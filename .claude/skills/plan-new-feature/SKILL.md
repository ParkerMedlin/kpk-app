---
name: plan-new-feature
description: Plans new features using a structured three-phase workflow (Requirements, Design, Tasks). Use when user wants to plan a feature, asks to spec out functionality, or says "let's plan" before implementing something significant.
---

# Plan New Feature

A structured approach to feature planning before implementation. Follows the spec-driven development pattern: define what, then how, then step-by-step execution.

## Workflow Overview

```
1. REQUIREMENTS  →  2. DESIGN  →  3. TASKS  →  4. IMPLEMENT
   (what)             (how)        (steps)      (code)
```

Each phase requires user approval before proceeding to the next.

## Phase 1: Requirements

Create `requirements.md` covering:
- **Problem statement**: What problem does this solve?
- **User stories**: As a [role], I want [action], so that [benefit]
- **Acceptance criteria**: WHEN [condition], THEN the system SHALL [behavior]
- **Scope boundaries**: What's explicitly NOT included

Use template: [requirements-template.md](requirements-template.md)

**Ask for approval before proceeding to Design.**

## Phase 2: Design

Create `design.md` covering:
- **Affected components**: Which existing files/modules change
- **New components**: What new files/classes/functions are needed
- **Data model changes**: New tables, fields, or relationships
- **Integration points**: How this connects to existing features
- **Error handling**: Key failure modes and how to handle them

Use template: [design-template.md](design-template.md)

**Ask for approval before proceeding to Tasks.**

## Phase 3: Tasks

Create `tasks.md` with:
- Numbered, actionable coding tasks
- Each task references its requirement
- Tasks build incrementally (each task produces testable output)
- Focus on what Claude Code can execute

Use template: [tasks-template.md](tasks-template.md)

**Ask for approval before implementation.**

## Phase 4: Tests

After implementation, create `tests.md` with:
- Grouped test cases organized by feature area
- Checkbox items for manual verification
- Coverage of access control, field display, validation, happy paths, error paths, data integrity, and edge cases
- Summary table with test counts per section

Use template: [tests-template.md](tests-template.md)

## Ongoing: Issues

When bugs or unexpected behavior are discovered during testing, document them in `issues.md`:
- Each issue gets a numbered heading with a short title
- Include: Problem description, Expected Behavior, Root Cause Analysis (when non-obvious), Code Locations, Fix Approach, and Tasks
- Tasks are numbered as `[issue].[task]` (e.g., 3.2) with checkboxes

Use template: [issues-template.md](issues-template.md)

## Ongoing: Change Orders

When requirements change or new functionality is added after initial implementation, document in `changeorders.md`:
- Each change is a numbered Phase continuing from tasks.md
- Include analysis of affected code and explicit side-effect verification
- Tasks follow the same Do/Deliverable format as tasks.md
- Progress table tracks completion across all phases

Use template: [changeorders-template.md](changeorders-template.md)

## Where to Store Specs

Create a feature folder at `project-handbook/feature-specs/{feature-name}/` containing:
```
project-handbook/feature-specs/{feature-name}/
├── requirements.md
├── design.md
├── tasks.md
├── tests.md          (after implementation)
├── issues.md         (as bugs are found)
└── changeorders.md   (as requirements evolve)
```

## KPK Context (Pre-Answered Decisions)

These decisions are already made for this codebase:

| Decision | Answer |
|----------|--------|
| Backend | Django 3.2 LTS |
| Database | PostgreSQL |
| Frontend | Bootstrap 5 + jQuery + vanilla JS |
| Real-time | Django Channels + Redis + WebSockets |
| API style | JSON endpoints in `views/api.py` |
| Layer pattern | Views → Services → Selectors |
| URL style | lowercase-with-dashes |
| Python style | snake_case functions, CamelCase classes |
| JS organization | `js/pageModules/` for page init, `js/objects/` for classes |

Reference `README.md` and `CLAUDE.md` for architecture details.

## Starting a New Feature

When user describes a feature:

1. **Clarify scope** - Ask questions if the feature boundaries are unclear
2. **Create spec folder** - `mkdir -p project-handbook/feature-specs/{feature-name}`
3. **Write requirements.md** - Use template, focus on WHAT not HOW
4. **Get approval** - Explicitly ask: "Does this requirements doc capture what you want?"
5. **Continue through phases** - Design, then Tasks, getting approval each time

## Implementation Phase

After tasks are approved:
- Work through tasks sequentially
- Mark each task complete as you finish
- Stop for review at natural breakpoints (end of phase, complex decisions)
- Reference task numbers in commit messages

**User Actions**: Some tasks require the user to perform actions directly (e.g., running migrations, deploying). Mark these clearly as "(USER ACTION)" in the task title. LLM should not attempt to run database migrations.
