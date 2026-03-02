# Sanitize Review Notes

Last updated: 2026-02-18
Branch: `sanitize/work-migration`

This is a running review log only. No files are removed from this checklist alone.

## How I decide what to flag
I flag candidates using objective signals:
- Security: hardcoded passwords, private keys, seeded accounts, sensitive config in tracked files.
- Identity leakage: personal emails/usernames, personal machine paths, personal account references.
- Environment coupling: scripts tied to specific local users/machines.
- Non-product artifacts: joke/demo/easter-egg assets, local backups/imports, old scripts.
- Repository hygiene: very large binaries or generated artifacts that are not required source.

## Initial Findings

### Priority 0 (security/compliance)
- ~~`app/core/management/commands/setup_users.py`~~ **DELETED**
  - Hardcoded user records with plaintext passwords and personal emails.
  - Resolved: deleted entirely — unnecessary given hashed pw data already lives in the DB.
- ~~`app/core/management/commands/change_admin_pw.py`~~ **DELETED**
  - Resolved: deleted entirely — same reasoning as setup_users.py.
- ~~`nginx/ssl/old/exceladdin.key:1`~~
  - Private key is tracked (`BEGIN PRIVATE KEY`).
  - Candidate action: purge from history and rotate/reissue key material.
	- User note: we don't use this key any more, can be safe deleted
- ~~`local_machine_scripts/python_db_scripts/old_scripts/CSVgres.py:8`~~
  - Hardcoded DB password string in legacy script.
  - Candidate action: remove legacy script or scrub credential literals.
	- User Note: I think can be safedeleted
- ~~`local_machine_scripts/python_db_scripts/old_scripts/reference/CSVtoPostgres.py:8`~~
  - Hardcoded DB password string in legacy reference script.
  - Candidate action: remove or scrub.
	- User Note: Scrub secret, keep old script for ref

### Priority 1 (tracked sensitive/ops data)
- ~~`db_backups/core_storagetank_202401090835.csv`~~
  - Tracked backup data file. Untrack and remove from history
- ~~`db_imports/`~~ (directory content present in working tree)
  - Import snapshots appear to be operational data and may not belong in source history.
	- Correct, clear from source history

### Priority 2 (likely non-product artifacts)
- ~~`local_machine_scripts/batch_scripts/old_scripts/`~~ (many files)
	- Keep for reference
- ~~`local_machine_scripts/python_db_scripts/old_scripts/`~~ (many files)
	- Keep for reference
- ~~`Users/pmedlin/Desktop/TimecardReportProcessor.py`~~
	- safe to delete
- `project-handbook/claude_skill_enhancements/` and `.claude/`
  - Determine if these are intentionally product-facing; otherwise move to internal docs repo.
	- keep here

### Priority 2 (large binary assets to review)
Tracked large files likely worth explicit keep/remove decision:
- ~~`ws4kp/server/images/gimp/Radar Basemap.xcf`~~ (~19 MB)
- ~~`ws4kp/server/images/gimp/Radar Basemap2.xcf`~~ (~19 MB)
- ~~`ws4kp/server/images/gimp/Radar Basemap5.xcf`~~ (~12 MB)
- ~~`ws4kp/server/music/default/Norman Connors - Kellies Theme.mp3`~~ (~7.2 MB)
- ~~`ws4kp/server/music/default/Kenny G - End Of The Night.mp3`~~ (~7.1 MB)
- ~~`ws4kp/server/music/default/Strong Breeze.mp3`~~ (~5.3 MB)
- ~~`app/core/static/core/media/important/kevin-gates-rbs-intro.gif`~~ (~1.8 MB)
- ~~`app/core/static/core/media/important/RippedEnzoBright.jpg`~~ (~1.6 MB)

- We want to keep these files, (and we will both local and on prod), but prob not stored in GitHub! Can remove from repo and scrub history

## Already addressed in history rewrite
These were already purged from all commits on this branch:
- ~~`app/nav3d/**`~~
- ~~`app/core/static/core/media/important/guy.jpg`~~
- ~~`app/core/static/core/media/guy.jpg`~~
	- ok delete these AND all references where they're used
	- Need to remove 

## Decision Log (fill together)
- [ ] Keep
- [ ] Remove from current tree only
- [ ] Purge from all history

| Item/Path | Decision | Notes |
|---|---|---|
| `app/core/management/commands/setup_users.py` | **Deleted** | Unnecessary — hashed pw data already in DB. |
| `app/core/management/commands/change_admin_pw.py` | **Deleted** | Same reasoning as setup_users.py. |
| `nginx/ssl/old/exceladdin.key` | Purge from all history | Unused key; remove from tree and rewrite history. |
| `db_backups/core_storagetank_202401090835.csv` | Purge from all history | Operational backup data should not live in git history. |
| `local_machine_scripts/python_db_scripts/old_scripts/` | Keep code, scrub secrets + purge secret-bearing history | Preserve reference code but remove credential literals everywhere. |
| `ws4kp/server/music/default/` | Remove from repo + purge from history | Keep files locally/prod, not in GitHub history. |
| `ws4kp/server/images/gimp/*.xcf` | Remove from repo + purge from history | Keep files locally/prod, not in GitHub history. |

## Agreed Plan (2026-02-18)
1. Pass 1 (now): security + artifact hygiene.
2. ~~Pass 2: `setup_users.py` redesign and rollout.~~ **Done — both `setup_users.py` and `change_admin_pw.py` deleted.**
3. Pass 2: full nav3d extraction cleanup (code + settings + urls + migrations/static references) and verification.

## Pass 1 Execution Checklist
- [ ] Remove `nginx/ssl/old/exceladdin.key` from tree.
- [ ] Remove `db_backups/core_storagetank_202401090835.csv` from tree.
- [ ] Scrub hardcoded credentials from `local_machine_scripts/python_db_scripts/old_scripts/**` while preserving scripts.
- [ ] Remove selected heavy media/assets from tracked source (`ws4kp/server/music/default/**`, `ws4kp/server/images/gimp/*.xcf`, and any approved extras).
- [ ] Run verification scans for:
  - [ ] `BEGIN PRIVATE KEY`
  - [ ] known legacy secrets (e.g. `REDACTED_DB_PASSWORD`, `REDACTED_PASSWORD`)
  - [ ] unexpected credential literals (`password =`, connection strings)
- [ ] Rewrite history once for all Pass 1 removals/scrubs.
- [ ] Re-verify rewritten history has no banned paths/secrets.
