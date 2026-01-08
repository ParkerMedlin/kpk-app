import datetime as dt
import json
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer

from app.websockets.base_consumer import (
    RedisBackedConsumer,
    json_default,
    sanitize_events,
    sanitize_payload,
)
from core.models import (
    BlendComponentCountRecord,
    BlendCountRecord,
    CiItem,
    CountCollectionLink,
    ImItemWarehouse,
    ItemLocation,
)
from prodverse.models import WarehouseCountRecord

logger = logging.getLogger(__name__)


class CountListConsumer(RedisBackedConsumer, AsyncWebsocketConsumer):
    async def connect(self):
        self.count_list_id = self.scope["url_route"]["kwargs"].get("count_list_id")

        if not self.count_list_id or self.count_list_id == "undefined":
            logger.error(
                "Invalid count_list_id received: %s", self.count_list_id
            )
            await self.close(code=4000)
            return

        self.group_name = f"count_list_unique_{self.count_list_id}"
        self.redis_key = f"count_list:{self.count_list_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code):
        await self.safe_group_discard()
        raise StopConsumer

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error(
                "Invalid JSON received on CountListConsumer: %s", text_data
            )
            return

        action = data.get("action")

        if action == "update_count":
            await self.update_count(data)
        elif action == "refresh_on_hand":
            await self.refresh_on_hand(data)
        elif action == "update_location":
            await self.update_location(data)
        elif action == "delete_count":
            await self.delete_count(data)
        elif action == "add_count":
            await self.add_count(data)

    async def update_count(self, data: Dict[str, Any]) -> None:
        record_id = data["record_id"]

        await self.save_count(data)

        await self.send_to_group(
            "count_updated",
            {
                "record_id": record_id,
                "data": data,
            },
            persist=True,
        )

    async def refresh_on_hand(self, data: Dict[str, Any]) -> None:
        record_id = data["record_id"]
        record_type = data["record_type"]

        new_on_hand = float(await self.update_on_hand(record_id, record_type))

        await self.send_to_group(
            "on_hand_refreshed",
            {
                "record_id": record_id,
                "new_on_hand": new_on_hand,
            },
            persist=True,
        )

    async def update_location(self, data: Dict[str, Any]) -> None:
        item_code = data["item_code"]
        location = data["location"]

        await self.update_location_in_db(item_code, location)

        await self.send_to_group(
            "location_updated",
            {
                "item_code": item_code,
                "location": location,
            },
            persist=True,
        )

    async def delete_count(self, data: Dict[str, Any]) -> None:
        record_id = data["record_id"]
        record_type = data["record_type"]
        list_id = data["list_id"]

        await self.delete_count_from_db(record_id, record_type, list_id)

        await self.send_to_group(
            "count_deleted",
            {
                "record_id": record_id,
                "list_id": list_id,
            },
            persist=True,
        )

    async def add_count(self, data: Dict[str, Any]) -> None:
        record_type = data["record_type"]
        list_id = data["list_id"]
        item_code = data["item_code"]

        count_info = await self.add_count_to_db(record_type, list_id, item_code)
        if not count_info:
            return

        payload = {
            "list_id": list_id,
            "record_id": count_info["id"],
            "item_code": count_info["item_code"],
            "item_description": count_info["item_description"],
            "expected_quantity": float(count_info["expected_quantity"]),
            "counted_quantity": float(count_info["counted_quantity"]),
            "counted_date": count_info["counted_date"].strftime("%Y-%m-%d"),
            "variance": float(count_info["variance"]),
            "count_type": count_info["count_type"],
            "collection_id": count_info["collection_id"],
            "location": count_info["location"],
        }

        await self.send_to_group(
            "count_added",
            payload,
            persist=True,
        )

    async def count_updated(self, event: Dict[str, Any]) -> None:
        await self._forward_event(event, "count_updated")

    async def container_updated(self, event: Dict[str, Any]) -> None:
        await self._forward_event(event, "container_updated")

    async def on_hand_refreshed(self, event: Dict[str, Any]) -> None:
        await self._forward_event(event, "on_hand_refreshed")

    async def location_updated(self, event: Dict[str, Any]) -> None:
        await self._forward_event(event, "location_updated")

    async def count_deleted(self, event: Dict[str, Any]) -> None:
        """
        Echo delete events back to the initiating client so their UI removes the
        row immediately, mirroring the behaviour we now allow for count_added.
        """
        payload = {
            key: value for key, value in event.items() if key != "sender_channel_name"
        }
        payload = sanitize_payload(payload)
        try:
            await self.send(text_data=json.dumps(payload, default=json_default))
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialize count_deleted event for count list %s: %s",
                getattr(self, "count_list_id", "unknown"),
                exc,
            )
        except Exception:
            logger.exception(
                "Unexpected error forwarding count_deleted event for count list %s",
                getattr(self, "count_list_id", "unknown"),
            )

    async def count_added(self, event: Dict[str, Any]) -> None:
        """
        When a user adds a count we need to echo the event back to the same
        connection so the UI can render the new row immediately. Other events
        still suppress sender echoes to avoid redundant updates.
        """
        payload = {
            key: value for key, value in event.items() if key != "sender_channel_name"
        }
        payload = sanitize_payload(payload)
        try:
            await self.send(text_data=json.dumps(payload, default=json_default))
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialize count_added event for count list %s: %s",
                getattr(self, "count_list_id", "unknown"),
                exc,
            )
        except Exception:
            logger.exception(
                "Unexpected error forwarding count_added event for count list %s",
                getattr(self, "count_list_id", "unknown"),
            )

    async def _forward_event(self, event: Dict[str, Any], event_name: str) -> None:
        if self.is_sender(event):
            return

        payload = {
            key: value for key, value in event.items() if key != "sender_channel_name"
        }
        payload = sanitize_payload(payload)
        try:
            await self.send(text_data=json.dumps(payload, default=json_default))
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialize %s event for count list %s: %s",
                event_name,
                getattr(self, "count_list_id", "unknown"),
                exc,
            )
        except Exception:
            logger.exception(
                "Unexpected error forwarding %s event for count list %s",
                event_name,
                getattr(self, "count_list_id", "unknown"),
            )

    @database_sync_to_async
    def save_count(self, data: Dict[str, Any]) -> None:
        record_id = data["record_id"]
        record_type = data["record_type"]
        expected_quantity = data["expected_quantity"]
        counted_quantity = (
            Decimal(data["counted_quantity"])
            if data["counted_quantity"] != ""
            else Decimal("0.0")
        )
        counted_date = dt.datetime.strptime(
            data["counted_date"], "%Y-%m-%d"
        ).date()
        variance = data["variance"]
        counted = data["counted"]
        comment = data["comment"]
        containers = data["containers"]
        sage_converted_quantity = data["sage_converted_quantity"]

        model = self.get_model_for_record_type(record_type)
        record = model.objects.get(id=record_id)

        record.counted_quantity = counted_quantity
        record.expected_quantity = expected_quantity
        record.counted_date = counted_date
        record.variance = variance
        record.counted = counted
        record.comment = comment
        record.containers = containers
        record.sage_converted_quantity = sage_converted_quantity
        record.save()

        location_qs = ItemLocation.objects.filter(
            item_code__iexact=record.item_code
        )
        if location_qs.exists():
            this_location = location_qs.first()
            this_location.zone = data["location"]
            this_location.save()

    @database_sync_to_async
    def update_on_hand(self, record_id: int, record_type: str):
        model = self.get_model_for_record_type(record_type)
        record = model.objects.get(id=record_id)
        quantityonhand = (
            ImItemWarehouse.objects.filter(
                itemcode__iexact=record.item_code, warehousecode__exact="MTG"
            )
            .first()
            .quantityonhand
        )
        record.expected_quantity = quantityonhand
        record.save()
        return record.expected_quantity

    @database_sync_to_async
    def update_location_in_db(self, item_code: str, location: str) -> None:
        record = ItemLocation.objects.get(item_code=item_code)
        record.zone = location
        record.save()

    @database_sync_to_async
    def delete_count_from_db(
        self, record_id: int, record_type: str, list_id: int
    ) -> None:
        count_record_model = self.get_model_for_record_type(record_type)
        record = count_record_model.objects.get(id=record_id)
        record.delete()
        count_collection = CountCollectionLink.objects.get(pk=list_id)
        count_collection.count_id_list = [
            id_ for id_ in count_collection.count_id_list if id_ != record_id
        ]
        count_collection.save()

    @database_sync_to_async
    def add_count_to_db(
        self, record_type: str, list_id: int, item_code: str
    ) -> Optional[Dict[str, Any]]:
        model = self.get_model_for_record_type(record_type)

        item_description = {
            item.itemcode: item.itemcodedesc
            for item in CiItem.objects.filter(itemcode__iexact=item_code)
        }
        item_quantity = {
            item.itemcode: item.quantityonhand
            for item in ImItemWarehouse.objects.filter(itemcode__iexact=item_code).filter(
                warehousecode__iexact="MTG"
            )
        }

        this_description = item_description.get(item_code)
        this_item_onhandquantity = item_quantity.get(item_code)
        count_collection = CountCollectionLink.objects.get(pk=list_id)

        if this_description is None or this_item_onhandquantity is None:
            logger.error(
                "Unable to resolve reference data for new count record: item_code=%s",
                item_code,
            )
            return None

        try:
            new_count_record = model(
                item_code=item_code,
                item_description=this_description,
                expected_quantity=this_item_onhandquantity,
                counted_quantity=0,
                counted_date=dt.date.today(),
                variance=0,
                count_type=record_type,
                collection_id=count_collection.collection_id,
            )
            new_count_record.save()

            count_collection.count_id_list.append(new_count_record.id)
            count_collection.save()

            location_obj = ItemLocation.objects.filter(
                item_code__iexact=new_count_record.item_code
            ).first()
            location = location_obj.zone if location_obj else ""

            return {
                "id": new_count_record.id,
                "item_code": new_count_record.item_code,
                "item_description": new_count_record.item_description,
                "expected_quantity": new_count_record.expected_quantity,
                "counted_quantity": new_count_record.counted_quantity,
                "counted_date": new_count_record.counted_date,
                "variance": new_count_record.variance,
                "count_type": new_count_record.count_type,
                "collection_id": new_count_record.collection_id,
                "location": location,
            }

        except Exception as exc:
            logger.error("Error adding count to database: %s", exc)
            return None

    def get_model_for_record_type(self, record_type: str):
        if record_type == "blend":
            return BlendCountRecord
        if record_type == "blendcomponent":
            return BlendComponentCountRecord
        if record_type == "warehouse":
            return WarehouseCountRecord
        raise ValueError(f"Invalid record type: {record_type}")

    async def _send_initial_state(self) -> None:
        events = await self.load_state()
        if not events:
            return

        try:
            sanitized_events = sanitize_events(events)
            if not sanitized_events:
                return
            payload = {
                "type": "initial_state",
                "events": sanitized_events,
            }
            await self.send(text_data=json.dumps(payload, default=json_default))
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialize count list initial state for %s: %s",
                self.count_list_id,
                exc,
            )
            await self.clear_state()
        except Exception:
            logger.exception(
                "Unexpected error sending initial state for %s", self.count_list_id
            )
            await self.clear_state()
