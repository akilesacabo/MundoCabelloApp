# Cloudflare Tunnel temporary setup

This file documents the temporary changes made so the app can be shared through a
public Cloudflare Tunnel and later reverted safely.

## Changed files

- `app/api.js`
  - API base now auto-detects the current origin.
  - On local dev ports `5173` and `5174`, it still uses `http://localhost:8000/api`.
  - When the app is served from the same origin as the backend, it uses `/api`.

- `backend/src/main.py`
  - Serves the frontend from `/app` using `StaticFiles`.
  - Redirects `/` to `/app/login.html`.

## How to run

1. Start the backend:

```bash
cd /Users/juanpablopereira/Documents/peluq-project/backend
./.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
```

2. Start the tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

3. Open the public URL printed by Cloudflare, then use:

- `/app/login.html`
- `/app/checkin.html`
- `/app/admin.html`
- `/app/admin-staff.html`
- `/app/admin-services.html`
- `/app/specialist.html`
- `/app/queue.html`

## Verify

- `GET /health` should return `{"status":"ok"}`
- Login should work from the public URL without changing the API URL manually.

## Revert later

If you want to undo this temporary tunnel setup, revert the two changes above:

- In `app/api.js`, restore the fixed local API base:

```js
const API='http://localhost:8000/api';
```

- In `backend/src/main.py`, remove:
  - `Path`, `RedirectResponse`, and `StaticFiles` imports
  - `app_dir = ...`
  - the `@app.get("/")` redirect
  - `app.mount("/app", StaticFiles(...))`

You can keep this file around until you are ready to remove the tunnel support.
