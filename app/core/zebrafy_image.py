########################################################################################
#
#    Author: Miika Nissi
#    Copyright 2023-2023 Miika Nissi (https://miikanissi.com)
#
#    This file is part of zebrafy
#    (see https://github.com/miikanissi/zebrafy).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
########################################################################################




########################################################################################
#
#    Author: Miika Nissi
#    Copyright 2023-2023 Miika Nissi (https://miikanissi.com)
#
#    This file is part of zebrafy
#    (see https://github.com/miikanissi/zebrafy).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
########################################################################################

# 1. Standard library imports:
import operator
from io import BytesIO
from typing import Union
import base64
import operator
import zlib

# 2. Known third party imports:
from PIL import Image

class GraphicField:
    """
    Converts a PIL image to Zebra Programming Language (ZPL) graphic field data.

    :param PIL.Image.Image image: An instance of a PIL Image.
    :param compression_type: ZPL compression type parameter that accepts the \
    following values, defaults to ``"A"``:

        - ``"A"``: ASCII hexadecimal - most compatible (default)
        - ``"B"``: Base64 binary
        - ``"C"``: LZ77 / Zlib compressed base64 binary - best compression
    """

    def __init__(self, pil_image: Image, compression_type: str = None):
        self.pil_image = pil_image
        if compression_type is None:
            compression_type = "a"
        self.compression_type = compression_type.upper()

    pil_image = property(operator.attrgetter("_pil_image"))

    @pil_image.setter
    def pil_image(self, i):
        if not i:
            raise ValueError("Image cannot be empty.")
        self._pil_image = i

    compression_type = property(operator.attrgetter("_compression_type"))

    @compression_type.setter
    def compression_type(self, c):
        if c is None:
            raise ValueError("Compression type cannot be empty.")
        if not isinstance(c, str):
            raise TypeError(
                "Compression type must be a valid string. {param_type} was given."
                .format(param_type=type(c))
            )
        if c not in ["A", "B", "C"]:
            raise ValueError(
                'Compression type must be "A","B", or "C". {param} was given.'.format(
                    param=c
                )
            )
        self._compression_type = c

    def _get_binary_byte_count(self) -> int:
        """
        Get binary byte count.

        This is the total number of bytes to be transmitted for the total image or
        the total number of bytes that follow parameter bytes_per_row. For ASCII \
        download, the parameter should match parameter graphic_field_count. \
        Out-of-range values are set to the nearest limit.

        :returns: Binary byte count
        """
        return len(self._get_data_string())

    def _get_bytes_per_row(self) -> int:
        """
        Get bytes per row.

        This is the number of bytes in the image data that comprise one row of the \
        image.

        :returns: Bytes per row
        """
        return int((self._pil_image.size[0] + 7) / 8)

    def _get_graphic_field_count(self) -> int:
        """
        Get graphic field count.

        This is the total number of bytes comprising the image data (width x height).

        :returns: Graphic field count."
        """
        return int(self._get_bytes_per_row() * self._pil_image.size[1])

    def _get_data_string(self) -> str:
        """
        Get graphic field data string depending on compression type.

        :returns: Graphic field data string depending on compression type.
        """
        image_bytes = self._pil_image.tobytes()
        data_string = ""

        # Compression type A: Convert bytes to ASCII hexadecimal
        if self._compression_type == "A":
            data_string = image_bytes.hex()

        # Compression type B: Convert bytes to base64 and add header + CRC
        elif self._compression_type == "B":
            b64_bytes = base64.b64encode(image_bytes)
            data_string = ":B64:{encoded_data}:{crc}".format(
                encoded_data=b64_bytes.decode("ascii"),
                crc=CRC(b64_bytes).get_crc_hex_string(),
            )

        # Compression type C: Convert LZ77/ Zlib compressed bytes to base64 and add
        # header + CRC
        elif self._compression_type == "C":
            z64_bytes = base64.b64encode(zlib.compress(image_bytes))
            data_string = ":Z64:{encoded_data}:{crc}".format(
                encoded_data=z64_bytes.decode("ascii"),
                crc=CRC(z64_bytes).get_crc_hex_string(),
            )

        return data_string

    def get_graphic_field(self) -> str:
        """
        Get a complete graphic field string for ZPL.

        :returns: Complete graphic field string for ZPL.
        """
        return "^GF{comp_type},{bb_count},{gf_count},{bpr},{data}^FS".format(
            comp_type=self._compression_type,
            bb_count=self._get_binary_byte_count(),
            gf_count=self._get_graphic_field_count(),
            bpr=self._get_bytes_per_row(),
            data=self._get_data_string(),
        )

class CRC:
    """
    Utility class to calculate CRC-16-CCITT algorithm across the received data bytes.

    CRC-16-CCITT polynomial representation: x^{16} + x^{12} + x^5 + 1

    :param data_bytes: Bytes object for which to calculate CRC
    :param poly: Reversed polynomial representation for CRC-16-CCITT calculation, \
    defaults to ``0x8408``
    """

    def __init__(self, data_bytes: bytes, poly: int = None):
        self.data_bytes = data_bytes
        if poly is None:
            poly = 0x8408
        self.poly = poly

    data_bytes = property(operator.attrgetter("_data_bytes"))

    @data_bytes.setter
    def data_bytes(self, d):
        if d is None:
            raise ValueError("Bytes data cannot be empty.")
        if not isinstance(d, bytes):
            raise TypeError(
                "Bytes data must be a valid bytes object. {param_type} was given."
                .format(param_type=type(d))
            )
        self._data_bytes = d

    poly = property(operator.attrgetter("_poly"))

    @poly.setter
    def poly(self, p):
        if p is None:
            raise ValueError("Polynomial cannot be empty.")
        if not isinstance(p, int):
            raise TypeError(
                "Polynomial must be a valid integer. {param_type} was given.".format(
                    param_type=type(p)
                )
            )
        self._poly = p

    def _get_crc16_ccitt(self) -> int:
        """
        Calculate CRC-16-CCITT Algorithm.

        :returns: CRC-16-CCITT
        """
        data = bytearray(self._data_bytes)
        crc = 0xFFFF
        for b in data:
            cur_byte = 0xFF & b
            for _ in range(0, 8):
                if (crc & 0x0001) ^ (cur_byte & 0x0001):
                    crc = (crc >> 1) ^ self._poly
                else:
                    crc >>= 1
                cur_byte >>= 1
        crc = ~crc & 0xFFFF
        crc = (crc << 8) | ((crc >> 8) & 0xFF)

        return crc & 0xFFFF

    def get_crc_hex_string(self) -> str:
        """
        Get CRC-16-CCITT as four digit zero padding hexadecimal string.

        :returns: CRC-16-CCITT as four digit zero padding hexadecimal string
        """
        return "%04X" % self._get_crc16_ccitt()


class ZebrafyImage:
    """
    Provides a method for converting PIL Image or image bytes to Zebra Programming \
    Language (ZPL).

    :param image: Image as a PIL Image or bytes object.
    :param compression_type: ZPL compression type parameter that accepts the \
    following values, defaults to ``"A"``:

        - ``"A"``: ASCII hexadecimal - most compatible (default)
        - ``"B"``: Base64 binary
        - ``"C"``: LZ77 / Zlib compressed base64 binary - best compression
    :param invert: Invert the black and white in resulting image, defaults to ``False``
    :param dither: Dither the pixels instead of hard limit on black and white, \
    defaults to ``False``
    :param threshold: Black pixel threshold for undithered image (``0-255``), defaults \
    to ``128``
    :param width: Width of the image in the resulting ZPL. If ``0``, use default image \
    width, defaults to ``0``
    :param height: Height of the image in the resulting ZPL. If ``0``, use default \
    image height, defaults to ``0``
    :param pos_x: X position of the image on the resulting ZPL, defaults to ``0``
    :param pos_y: Y position of the image on the resulting ZPL, defaults to ``0``
    :param complete_zpl: Return a complete ZPL with header and footer included. \
    Otherwise return only the graphic field, defaults to ``True``
    """

    def __init__(
        self,
        image: Union[bytes, Image.Image],
        compression_type: str = None,
        invert: bool = None,
        dither: bool = None,
        threshold: int = None,
        width: int = None,
        height: int = None,
        pos_x: int = None,
        pos_y: int = None,
        complete_zpl: bool = None,
    ):
        self.image = image
        if compression_type is None:
            compression_type = "a"
        self.compression_type = compression_type.upper()
        if invert is None:
            invert = False
        self.invert = invert
        if dither is None:
            dither = True
        self.dither = dither
        if threshold is None:
            threshold = 128
        self.threshold = threshold
        if width is None:
            width = 0
        self.width = width
        if height is None:
            height = 0
        self.height = height
        if pos_x is None:
            pos_x = 0
        self.pos_x = pos_x
        if pos_y is None:
            pos_y = 0
        self.pos_y = pos_y
        if complete_zpl is None:
            complete_zpl = True
        self.complete_zpl = complete_zpl

    image = property(operator.attrgetter("_image"))

    @image.setter
    def image(self, i):
        if not i:
            raise ValueError("Image cannot be empty.")
        if not isinstance(i, bytes) and not isinstance(i, Image.Image):
            raise TypeError(
                "Image must be a valid bytes object or PIL.Image.Image object."
                " {param_type} was given.".format(param_type=type(i))
            )
        self._image = i

    compression_type = property(operator.attrgetter("_compression_type"))

    @compression_type.setter
    def compression_type(self, c):
        if c is None:
            raise ValueError("Compression type cannot be empty.")
        if not isinstance(c, str):
            raise TypeError(
                "Compression type must be a valid string. {param_type} was given."
                .format(param_type=type(c))
            )
        if c not in ["A", "B", "C"]:
            raise ValueError(
                'Compression type must be "A","B", or "C". {param} was given.'.format(
                    param=c
                )
            )
        self._compression_type = c

    invert = property(operator.attrgetter("_invert"))

    @invert.setter
    def invert(self, i):
        if i is None:
            raise ValueError("Invert cannot be empty.")
        if not isinstance(i, bool):
            raise TypeError(
                "Invert must be a boolean. {param_type} was given.".format(
                    param_type=type(i)
                )
            )
        self._invert = i

    dither = property(operator.attrgetter("_dither"))

    @dither.setter
    def dither(self, d):
        if d is None:
            raise ValueError("Dither cannot be empty.")
        if not isinstance(d, bool):
            raise TypeError(
                "Dither must be a boolean. {param_type} was given.".format(
                    param_type=type(d)
                )
            )
        self._dither = d

    threshold = property(operator.attrgetter("_threshold"))

    @threshold.setter
    def threshold(self, t):
        if t is None:
            raise ValueError("Threshold cannot be empty.")
        if not isinstance(t, int):
            raise TypeError(
                "Threshold must be an integer. {param_type} was given.".format(
                    param_type=type(t)
                )
            )
        if t < 0 or t > 255:
            raise ValueError(
                "Threshold must be within 0 to 255. {param} was given.".format(param=t)
            )
        self._threshold = t

    width = property(operator.attrgetter("_width"))

    @width.setter
    def width(self, w):
        if w is None:
            raise ValueError("Width cannot be empty.")
        if not isinstance(w, int):
            raise TypeError(
                "Width must be an integer. {param_type} was given.".format(
                    param_type=type(w)
                )
            )
        self._width = w

    height = property(operator.attrgetter("_height"))

    @height.setter
    def height(self, h):
        if h is None:
            raise ValueError("Height cannot be empty.")
        if not isinstance(h, int):
            raise TypeError(
                "Height must be an integer. {param_type} was given.".format(
                    param_type=type(h)
                )
            )
        self._height = h

    pos_x = property(operator.attrgetter("_pos_x"))

    @pos_x.setter
    def pos_x(self, x):
        if x is None:
            raise ValueError("X position cannot be empty.")
        if not isinstance(x, int):
            raise TypeError(
                "X position must be an integer. {param_type} was given.".format(
                    param_type=type(x)
                )
            )
        self._pos_x = x

    pos_y = property(operator.attrgetter("_pos_y"))

    @pos_y.setter
    def pos_y(self, y):
        if y is None:
            raise ValueError("Y position cannot be empty.")
        if not isinstance(y, int):
            raise TypeError(
                "Y position must be an integer. {param_type} was given.".format(
                    param_type=type(y)
                )
            )
        self._pos_y = y

    complete_zpl = property(operator.attrgetter("_complete_zpl"))

    @complete_zpl.setter
    def complete_zpl(self, c):
        if c is None:
            raise ValueError("Complete ZPL cannot be empty.")
        if not isinstance(c, bool):
            raise TypeError(
                "Complete ZPL must be a boolean. {param_type} was given.".format(
                    param_type=type(c)
                )
            )
        self._complete_zpl = c

    def to_zpl(self) -> str:
        """
        Converts PIL Image or image bytes to Zebra Programming Language (ZPL).

        :returns: A complete ZPL file string which can be sent to a ZPL compatible \
        printer or a ZPL graphic field if complete_zpl is not set.
        """
        if isinstance(self._image, bytes):
            pil_image = Image.open(BytesIO(self._image))
        else:
            pil_image = self._image

        # Resize image if width or height defined in parameters
        if self._width or self._height:
            width, height = pil_image.size
            if self._width:
                width = self._width
            if self._height:
                height = self._height
            pil_image = pil_image.resize((width, height))

        # Convert image to black and white based on given parameters
        if self._dither:
            pil_image = pil_image.convert("1")
            if self._invert:
                pil_image = pil_image.point(lambda x: 255 - x)
        else:
            pil_image = pil_image.convert("L")
            pil_image = pil_image.point(
                lambda x: (
                    (0 if self._invert else 255)
                    if x > self._threshold
                    else (255 if self._invert else 0)
                ),
                mode="1",
            )

        graphic_field = GraphicField(pil_image, compression_type=self._compression_type)

        # Set graphic field position based on given parameters
        pos = "^FO0,0"
        if self._pos_x or self._pos_y:
            pos = "^FO{x},{y}".format(x=self._pos_x, y=self._pos_y)

        # Return complete ZPL with header and footer or only the graphic field based on
        # given parameters
        if self._complete_zpl:
            return "^XA\n" + pos + graphic_field.get_graphic_field() + "\n^XZ\n"

        return pos + graphic_field.get_graphic_field()
