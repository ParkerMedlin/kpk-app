## Development Environment

- ALWAYS assume work is being done on the local development instance.
- NEVER run `kpk` commands (git pull, collectstatic, or any production commands) unless the user explicitly says they are ready to deploy to production.
- Do not suggest deploying, testing on prod, or running production commands as part of any workflow.
- When discussing testing, assume local Django runserver / local Docker compose unless told otherwise.
- NEVER attempt to test changes yourself (no curl, no browser automation, no running the app). Instead, provide the user with a detailed checklist of manual testing steps, including full URLs with query parameters or request payloads for any API endpoints (e.g., `http://localhost:8000/api/endpoint/?param=value`).
