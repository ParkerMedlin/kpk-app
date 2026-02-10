---
name: troubleshoot-feature
description: Troubleshoots a broken or misbehaving feature through guided investigation. Collects the problem description, asks clarifying questions, investigates relevant code, then produces a write-up with actionable fix tasks. Planning only — another LLM will execute the fixes.
---

# Troubleshoot Feature

A structured approach to diagnosing and documenting fixes for broken or misbehaving features. This skill produces a write-up only — it does NOT modify code.

## Workflow

```
1. COLLECT      →  2. INVESTIGATE  →  3. WRITE UP
   (symptoms)       (code dive)        (diagnosis + tasks)
```

## Phase 1: Collect Symptoms

Ask the user targeted questions to understand the problem. Get answers to as many of these as possible before investigating code:

- **What's broken?** Observable symptom in the user's own words.
- **What should happen instead?** Expected behavior.
- **When did it start?** Recent deploy, code change, data change?
- **Reproducibility** — Always? Sometimes? Specific conditions?
- **Scope** — One page/endpoint, or multiple? Specific users/roles?
- **Error messages** — Console errors, Django tracebacks, network failures?
- **Recent changes** — Any commits or deploys that might correlate?

Don't ask all of these as a wall of text. Ask the most important 2-3 first, then follow up based on answers.

## Phase 2: Investigate

Based on the symptoms, trace the code path:

1. **Identify entry point** — URL route, view function, template, JS module
2. **Follow the data** — View → service → selector → model/query
3. **Check the frontend** — Template rendering, JS event handlers, AJAX calls
4. **Look for the break** — Logic errors, missing data, wrong assumptions, race conditions
5. **Check recent changes** — `git log` on suspect files if timing is relevant

Use Read, Grep, and Glob tools to investigate. Summarize findings to the user as you go so they can steer the investigation.

## Phase 3: Write Up

Create `troubleshooting.md` in the relevant feature spec folder (or a new one if none exists):

```
project-handbook/feature-specs/{feature-name}/troubleshooting.md
```

Use template: [troubleshooting-template.md](troubleshooting-template.md)

The write-up must contain enough detail for another LLM to execute every fix task without needing to re-investigate the codebase.

## Key Principles

- **Don't guess.** Read the actual code before drawing conclusions.
- **Show your work.** Reference specific files, functions, and line numbers.
- **Tasks must be self-contained.** Each task should specify the exact file, function, and what to change. The executing LLM should not need to search the codebase.
- **Verify scope.** Check whether the same pattern/bug exists elsewhere before writing tasks.
- **No code changes.** This skill produces documentation only.
