# [Feature Name] – Test Suite

**URLs**:
- [Page]: `/core/[route]/`
- [API List/Create]: `/core/api/[route]/`
- [API Detail]: `/core/api/[route]/<id>/`

---

## 1. Access Control

### [Page Name] (`/core/[route]/`)

- [ ] Page loads for [authorized role]
- [ ] Page loads for staff user
- [ ] Page returns 403 for [unauthorized role]
- [ ] Page redirects to login for anonymous user

### Navigation

- [ ] "[Feature]" link appears in [dropdown] for [authorized users]

---

## 2. [Feature Area] – Field Display

### Core Fields (Always Visible)

- [ ] [Field] shows expected options/values
- [ ] [Field] displays correctly

### Conditional Fields – [Condition]

- [ ] Selecting "[value]" shows [field]
- [ ] Selecting "[value]" hides [field]
- [ ] Changing from [value] to [value] clears and hides [field]

---

## 3. [Feature Area] – User Interactions

- [ ] [Action] produces [expected result]
- [ ] [Action] produces [expected result]

---

## 4. [Feature Area] – Validation

### Client-Side

- [ ] Entering valid value shows success indicator
- [ ] Entering invalid value shows error: "[message]"
- [ ] Leaving required field empty shows error

### Server-Side

- [ ] Server validation error displays on correct field
- [ ] Error toast shows summary message

---

## 5. Form Submission – Happy Paths

- [ ] Submit with valid data → record created
- [ ] Success feedback appears
- [ ] Form resets after successful submission

---

## 6. Form Submission – Validation Errors

### Missing Required Fields

- [ ] Submit without [field] → error on field
- [ ] First error field receives focus

---

## 7. Data Integrity

- [ ] [Auto-populated field] set correctly on create
- [ ] [Computed field] calculated correctly

---

## 8. Edge Cases

### Boundary Values

- [ ] [Boundary value] handled correctly

### Null/Empty Handling

- [ ] Empty [field] for [condition]
- [ ] Null [field] for [condition]

---

## Test Summary

| Section | Tests |
|---------|-------|
| 1. Access Control | 0 |
| 2. Field Display | 0 |
| 3. User Interactions | 0 |
| 4. Validation | 0 |
| 5. Happy Paths | 0 |
| 6. Validation Errors | 0 |
| 7. Data Integrity | 0 |
| 8. Edge Cases | 0 |

**Total**: 0 tests
