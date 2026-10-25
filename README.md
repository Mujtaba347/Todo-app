# Taskly: To-Do app with AI assistants

**Stack:** FastAPI (Python) · React (Vite) · PostgreSQL · OpenRouter (AI chatbots)

- **Users** register, sign in and manage their own todos.
- **Admins** manage every user and every todo from an admin console.
- A **floating chatbot (bottom-right, the ✦ button)** performs CRUD operations from plain-language messages.
  Users and admins each get their **own separate assistant** (own endpoint, tools, prompt and chat history).

```
todo-app/
├── .env.example           copy to .env and fill in
├── backend/               FastAPI app
│   └── app/
│       ├── main.py        app, CORS, table creation, default admin seeding
│       ├── models.py      User, Todo (SQLAlchemy)
│       ├── services.py    shared business logic (REST + chatbot)
│       ├── chatbot.py     both assistants: prompts, tools, OpenRouter loop
│       └── routers/       auth, todos, admin, chat
└── frontend/              React app (login, user dashboard, admin console, chat widget)
```

## Requirements

| Tool | Version | Check with |
|---|---|---|
| Python | 3.10+ (tick "Add to PATH" when installing) | `python --version` |
| Node.js | 18+ (LTS) from https://nodejs.org | `node --version` |
| PostgreSQL | 14+ (includes pgAdmin 4) | https://www.postgresql.org/download/ |

## 1. Set up PostgreSQL

1. Install PostgreSQL with default options (port `5432`). Choose a password for the `postgres` user and remember it (letters and numbers only keeps things simple).
2. Open **pgAdmin 4**, expand `Servers`, connect to your PostgreSQL server (enter the password).
3. Click the **`postgres`** database, then `Tools → Query Tool` (Alt+Shift+Q), paste this and press ▶ / F5:
   ```sql
   CREATE DATABASE todo_app;
   ```
4. Verify with `SELECT datname FROM pg_database;`. `todo_app` should be listed.

You do **not** create tables. The backend creates `users` and `todos` automatically on first start.

## 2. Create the `.env` file

In the `todo-app` folder (same level as `backend` and `frontend`):

```powershell
copy .env.example .env        # Mac/Linux: cp .env.example .env
```

Edit `.env`:

| Variable | What to put |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/todo_app` |
| `SECRET_KEY` | long random string. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `OPENROUTER_API_KEY` | key from https://openrouter.ai/keys (Create Key, copy it once; starts with `sk-or-v1-`) |
| `OPENROUTER_MODEL` | a model that supports **tool calling**, e.g. `openai/gpt-4o-mini` (default) |
| `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` | the admin account, created on first start |
| `ADMIN_BOT_ALLOW_SQL_WRITE` | `false` (default) or `true`, see "Chatbots" below |
| `APP_ENV` | `development` locally, `production` on Render (enables strict startup checks) |

Notes:
- No spaces or quotes around values (`KEY=value`).
- If your DB password has special characters (`@ # /`), they must be URL-encoded (`@` → `%40`). Easier: use a simple password.
- The admin account is created **only once**, the first time the backend starts. Changing `ADMIN_PASSWORD` afterwards does not change an existing admin. Change it in the admin console instead, or ask the admin chatbot.
- Never commit or share `.env` (it is already in `.gitignore`). If a key leaks, revoke it on OpenRouter and create a new one.
- Restart the backend after any `.env` change.

## 3. Run the backend (Terminal 1)

```powershell
cd todo-app\backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- If activation says "running scripts is disabled": run `Set-ExecutionPolicy -Scope Process Bypass`, then activate again.
- Always run `uvicorn` from inside the `backend` folder.
- Success looks like: `Created default admin 'admin' ...` and `Application startup complete`.
- Health check: http://localhost:8000/api/health → `{"status":"ok","ai_configured":true}`
- API docs: http://localhost:8000/docs

## 4. Run the frontend (Terminal 2, a new terminal tab)

```powershell
cd todo-app\frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

## 5. Use the app

- **Admin:** sign in with `ADMIN_USERNAME` (or email) and `ADMIN_PASSWORD`. You get the admin console (Overview, Users, Todos) and the admin chatbot.
- **User:** click **Create account**. You get your own todo dashboard and your own chatbot.
- Click ✦ (bottom-right) to open the chatbot. Examples:
  - User: `Add a high priority todo to call the dentist tomorrow`, `What's still pending?`, `Mark the groceries todo as done`
  - Admin: `Give me a platform overview`, `List all users and how many todos each has`, `Which todos are overdue?`, `Create a user ali with email ali@example.com`

### Starting again later
Both terminals must be running. You do not repeat `pip install` / `npm install`.
```powershell
# Terminal 1
cd todo-app\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Terminal 2
cd todo-app\frontend
npm run dev
```
Stop with Ctrl+C in each terminal.

## Chatbots

Each message goes to `POST /api/chat/user` or `POST /api/chat/admin`. The backend sends it to OpenRouter with a list of tools; the model chooses tools, the backend runs them against PostgreSQL, and the answer returns with action chips (green = success, red = failed). The page refreshes after any action.

| | User assistant | Admin assistant |
|---|---|---|
| Endpoint | `/api/chat/user` | `/api/chat/admin` (admin role required) |
| Todos | create / list / update / complete / delete, **own only** | create / list / update / reassign / delete, **everyone's** |
| Users | none | list / create / update (role, active, password) / delete |
| Database | none | `describe_schema`, `run_sql`, platform stats |

**Database access**
- The admin assistant has access to the whole database. By default `run_sql` is **read-only** (reports and analysis); changes go through the validated CRUD tools. Set `ADMIN_BOT_ALLOW_SQL_WRITE=true` to also allow `INSERT/UPDATE/DELETE/DDL` through SQL.
- The user assistant is deliberately limited to the signed-in user's own todos. The server injects the owner id, so prompting cannot reach other people's data.
- Password hashes are never exposed to the model.
- Data the bot reads is sent to OpenRouter and the model provider you chose. Using the API costs credits on your OpenRouter account.

## Guardrails

**Chatbot**
- **Confirmation for destructive actions:** deleting a user, deleting all completed todos, and any SQL that changes data only run after the person confirmed in a *separate* message. This is enforced in server code, not only in the prompt.
- **Scope:** the user assistant can only ever touch the signed-in user's own todos (the owner id is injected by the server).
- **SQL safety (admin assistant):** one statement per call; read-only by default; no comments; `DROP / TRUNCATE / ALTER / GRANT / COPY / pg_sleep ...` blocked; `UPDATE`/`DELETE` need a `WHERE`; 5-second statement timeout; the audit log and password hashes are protected.
- **Prompt-injection defense:** todo text and database rows are treated as data, never as instructions.
- **Cost protection:** per-minute limit, daily message limit per user (50) and admin (200), maximum actions per message (10), message length cap.
- **Audit log:** every chatbot message and action is recorded and visible in the admin console's **Activity** tab (passwords are masked).

**API**
- Login lockout after 5 failed attempts (15 minutes), sign-up rate limit per IP, optional `ALLOW_REGISTRATION=false`.
- Passwords: at least 8 characters with a letter and a number.
- Limit of 500 todos per user, security headers on every response.
- With `APP_ENV=production` the backend **refuses to start** with a weak `SECRET_KEY` (< 32 chars) or the default admin password.

All limits are configurable in `.env` (see `.env.example`). Rate limits are kept in memory, which is right for one server; with several servers move them to Redis.

## Troubleshooting

| Problem | Fix |
|---|---|
| `connection refused` / `could not connect to server` | PostgreSQL is not running. Start the "postgresql" service (Windows `Services`) or reopen pgAdmin and connect. |
| `password authentication failed` | Wrong password in `DATABASE_URL`. |
| `database "todo_app" does not exist` | Do step 1 (create the database). |
| `pip` / `python` / `npm` not recognized | Install Python / Node.js, tick "Add to PATH", restart VS Code. |
| Backend won't start with settings errors | Check `.env` is in `todo-app\` (not inside `backend`) and has no stray quotes/spaces. |
| Chatbot: "OPENROUTER_API_KEY is not set" | Add the key to `.env`, restart the backend. |
| Chatbot: OpenRouter error 401 | Key is wrong or revoked. Create a new one. |
| Chatbot: OpenRouter error 402 | No credits on your OpenRouter account. Add credit. |
| Chatbot: OpenRouter error 400/404 | Model name wrong or no tool-calling support. Change `OPENROUTER_MODEL`. |
| "Cannot reach the server" in the browser | Backend isn't running on port 8000. |
| Port 8000 busy | `uvicorn app.main:app --reload --port 8001` and change `8000` to `8001` in `frontend/vite.config.js`. |
| Forgot the admin password | In pgAdmin run `DELETE FROM users WHERE role='admin';` (on `todo_app`), set a new `ADMIN_PASSWORD` in `.env` and restart the backend. A new admin is created. |


## Before going live

- Change `SECRET_KEY` and `ADMIN_PASSWORD`, serve over HTTPS, and set `CORS_ORIGINS` to your real frontend URL.
- Tables are created with `create_all`; add Alembic migrations before changing the schema later.
- Production frontend: `npm run build`, serve `frontend/dist` from any static host, and set `VITE_API_URL` to your API URL at build time.
