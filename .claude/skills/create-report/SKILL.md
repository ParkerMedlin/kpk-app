---
name: create-report
description: Creates new report pages in the KPK Django app. Use when user asks to create a report, add reporting features, build report pages, or add data visualizations.
---

# Create Report

## 1. Gather Requirements

Confirm with user if not already provided:
- Target app and whether to create a new branch
- Reference reports to emulate (if any)
- Required model/table changes
- Backend logic for data fetching/modification
- Frontend format and any forms needed

## 2. Implementation Checklist

```
- [ ] Backend: selectors/, services/, consumers.py
- [ ] Models: any model.py additions
- [ ] Template: templates/
- [ ] View: views/web.py
- [ ] API: views/api.py (if needed)
- [ ] URLs: urls.py
- [ ] JS: core/static/core/js/
- [ ] CSS: core/static/core/css/
- [ ] Forms: forms.py (if needed)
- [ ] Navigation: Add to quick lookup and Misc Reports dropdown
```
