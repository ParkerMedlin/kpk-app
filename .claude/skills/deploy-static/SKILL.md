---
name: deploy-static
description: Deploys static file changes (JS/CSS) to the production container by running collectstatic.
---

# Deploy Static Files

Run this after updating any `.js` or `.css` files to deploy changes to production.

## Command

```bash
docker exec kpk-app_app_blue_1 sh -c "python manage.py collectstatic --noinput"
```

## When to Use

After modifying files in:
- `app/core/static/core/js/`
- `app/core/static/core/css/`
- Any other static asset directories

## Instructions

Run the collectstatic command above. Report success or any errors to the user.
