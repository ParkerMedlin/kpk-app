# [Feature Name] — Troubleshooting

## Problem Summary

**Reported symptom:** [What the user described]

**Expected behavior:** [What should happen instead]

**Conditions:** [When/how it reproduces — always, specific data, specific role, etc.]

---

## Investigation

### Code Path Traced

```
[Entry point] → [Next layer] → [Next layer] → [Where it breaks]
```

### Findings

[Narrative explanation of what was found during investigation. Reference specific files and line numbers. Explain the root cause clearly enough that someone unfamiliar with this code path can understand it.]

### Code Locations

| File | Lines | Role |
|------|-------|------|
| `[file path]` | [N-M] | [What this code does in the context of the bug] |
| `[file path]` | [N-M] | [What this code does] |

---

## Fix Tasks

### Task 1: [Short imperative title]

- **File**: `[exact file path]`
- **Function/Section**: `[function name or template section]`
- **Do**: [Precise description of the change. Include current behavior and target behavior.]
- **Why**: [Why this change fixes the problem]
- **Watch out**: [Side effects to verify, if any]

### Task 2: [Short imperative title]

- **File**: `[exact file path]`
- **Function/Section**: `[function name or template section]`
- **Do**: [Precise description of the change]
- **Why**: [Why this change fixes the problem]
- **Watch out**: [Side effects to verify, if any]

---

## Verification

After all tasks are complete, verify:

- [ ] [Original symptom no longer occurs]
- [ ] [Expected behavior now works]
- [ ] [No regressions in related functionality — specify what to check]

---

**Status**: Draft | Approved | Fixed
