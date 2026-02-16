# Requirements: Count Collection Soft Delete

## Problem Statement

When a CountCollectionLink is deleted, it is permanently removed from the database. The associated count records (BlendCountRecord, etc.) are orphaned with no way to access them through the UI. Users lose visibility into historical count data, and there is no way to recover a mistakenly deleted collection. The system needs a soft-delete mechanism that hides collections instead of destroying them, with a staff-only archive view for managing hidden collections.

## User Stories

1. **As a blending manager (staff)**, I want to hide a count collection I no longer need, so that my active list stays clean without permanently losing data.

2. **As a blending manager (staff)**, I want to view all hidden count collections on a dedicated page, so that I can review historical count data and restore collections if needed.

3. **As a blending manager (staff)**, I want to restore a hidden collection back to the active list, so that I can recover from accidental hides or resume counting.

4. **As a user actively entering counts**, I want to be notified when my current list is archived without being kicked out, so that I can finish my work before navigating away.

5. **As a blending manager (staff)**, I want hidden collection records flagged in the count status report, so that I can distinguish active from archived counts when reviewing data.

## Acceptance Criteria

### AC-1: Hide Action Replaces Delete
- WHEN a user clicks the action button on a collection link, THEN the system SHALL set `is_hidden=True` on the CountCollectionLink instead of deleting it.
- WHEN a collection is hidden, THEN it SHALL no longer appear on the active collection links page for any user.
- WHEN a collection is hidden, THEN the action SHALL be broadcast via WebSocket to all connected clients.

### AC-2: Active User Soft Transition
- WHEN a user is actively on a count list page and that collection is hidden, THEN the system SHALL display a dismissible banner reading "This count list has been archived."
- WHEN the banner is displayed, THEN the user SHALL still be able to continue entering and saving counts on that page.
- WHEN the user navigates away from the archived list, THEN they SHALL NOT be able to navigate back to it (it will no longer appear in the active list).

### AC-3: Hidden Collections Page (Staff Only)
- WHEN a staff user navigates to the hidden collections page, THEN the system SHALL display all CountCollectionLinks where `is_hidden=True`.
- WHEN a non-staff user attempts to access the hidden collections page, THEN the system SHALL deny access.
- WHEN viewing the hidden collections list, THEN each collection name SHALL be a clickable link that navigates to a read-only view of its count records.
- WHEN viewing hidden collection records, THEN the count entry form SHALL be disabled (no edits allowed).

### AC-4: Restore Action (Staff Only)
- WHEN a staff user clicks restore on a hidden collection, THEN the system SHALL set `is_hidden=False` and return the collection to the active list.
- WHEN a collection is restored, THEN the system SHALL broadcast a WebSocket event so the active collection links page updates in real time.
- WHEN a non-staff user attempts to restore a collection, THEN the system SHALL deny the action.

### AC-5: Navigation
- WHEN a staff user views the active collection links page, THEN the system SHALL display a link/button to the hidden collections page.
- WHEN a non-staff user views the active collection links page, THEN the hidden collections link SHALL NOT be visible.

### AC-6: Count Status Report
- WHEN count records belong to a hidden collection, THEN the count status report SHALL include those records but display a visual indicator (e.g., badge, icon, or row styling) that the collection is archived.

## Scope Boundaries

### In Scope
- `is_hidden` field on CountCollectionLink model
- Replacing hard delete with soft delete (hide)
- Hidden collections archive page (staff only)
- Restore from hidden (staff only)
- Soft transition for active users (banner, continue editing)
- Visual flag on count status report for hidden collection records
- WebSocket events for hide/restore actions

### Out of Scope
- Permanent delete capability (no hard delete from UI at all)
- Bulk hide/restore operations
- Automatic hiding based on age or completion status
- Changes to the count record models themselves (BlendCountRecord, etc.)
- Migration of previously deleted collections (they're already gone)
- Changes to the ETL/data_sync layer
