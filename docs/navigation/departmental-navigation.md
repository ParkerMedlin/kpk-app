# Departmental Navigation Contract

## Overview
- Navigation stays department-first. Each Django group has its own partial under `app/templates/navbars/`.
- Shared destinations (for example, the blend schedule links) now live in `app/templates/navbars/partials/blend-schedule-links.html` to avoid drift between departments.
- The global command palette (Ctrl/Cmd + K) reads only the links rendered for the current user, so permissions stay intact.

## Primary Assets
- `app/templates/base.html`: mounts the command palette button, modal markup, and still controls which group partials are included.
- `app/templates/navbars/*-navbar-items.html`: role-specific menus. Comments at the top of each file call out the intended audience.
- `app/templates/navbars/partials/blend-schedule-links.html`: single source of truth for the blend schedule destinations. Pass `include_staff_links` to control Drums/Totes visibility.
- `app/static/core/js/objects/pageObjects.js`: the `BaseTemplatePage` initializes the command palette and keeps it in sync with the nav.
- `app/static/core/css/base.css`: UI polish for the palette (modal shell, list items, shortcut hint).

## Adding or Editing Navigation
1. Decide which group needs the link and edit that group’s partial only. Keep text concise and user-facing; add a short comment if the intent is not obvious.
2. If the link fits an existing shared include (for example, a new blend schedule filter), update the partial instead of sprinkling copies in multiple files.
3. Confirm the generated `<a>` element has meaningful text. The command palette uses the anchor label (or `data-command-label`) when presenting search results.
4. Fire up the app, open the command palette (Ctrl/Cmd + K), and verify the new destination appears once, grouped under the correct dropdown label.
5. For staff-only entries, pass `include_staff_links=user.is_staff` or wrap the item in `{% if user.is_staff %}` to keep parity between navigation and permissions.

## Command Palette Notes
- Trigger: button in the top-right nav or Ctrl/Cmd + K globally.
- Results follow the links a user can see; nothing outside their permissions is surfaced.
- The list builds lazily the first time you search and then stays cached, so the palette appears instantly.
- Exact string matches jump to the top of the list—type the full menu label and hit Enter to launch immediately.
- Keyboard: arrow keys to move, Enter to open, Escape to close. Mouse users can click as expected.
- To hide a link from the palette while keeping it in the navbar, add `data-command-ignore="true"` to the anchor.
