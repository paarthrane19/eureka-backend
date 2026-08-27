# Supasift API (FastAPI + MongoDB)

REST backend for the Supasift mobile app. JWT auth (bcrypt-hashed passwords),
Pydantic models, and MongoDB collections for `users`, `posts`, `comments`,
`votes`, `bookmarks`, and `notifications`.

## Setup (macOS)

### 1. MongoDB

```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

This runs MongoDB at `mongodb://localhost:27017`. Confirm with `brew services list`.

### 2. Python environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` if needed — the defaults target local MongoDB. **Change `JWT_SECRET`
before deploying anywhere real.**

### 3. Seed the database

```bash
python seed.py
```

This drops and rebuilds the collections with 6 accounts and 25 genuinely
interesting science posts (plus a scattering of comments) so the feed feels
alive from first launch. All seed accounts share the password **`eureka123`**.

### 4. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` is important: it lets your phone reach the API over the LAN, not
just `localhost`. Interactive API docs are at `http://localhost:8000/docs`.

## Project layout

```
backend/
├── app/
│   ├── main.py            App factory, CORS, router registration, lifespan
│   ├── config.py          Settings (env-driven) + category list
│   ├── database.py        Motor client, connection lifecycle, indexes
│   ├── security.py        Password hashing, JWT, current-user dependency
│   ├── schemas.py         Pydantic request/response models
│   ├── serializers.py     Mongo document → API dict helpers
│   └── routers/
│       ├── auth.py            /auth  signup, login, me
│       ├── users.py           /users profile, onboarding, user posts
│       ├── posts.py           /posts feed, detail, upvote, bookmark, library
│       ├── comments.py        post comments
│       └── notifications.py   /notifications list, unread count, mark read
└── seed.py                Database seeding script
```

## Key endpoints

| Method | Path                       | Notes                                  |
|--------|----------------------------|----------------------------------------|
| POST   | `/auth/signup`             | Returns JWT + user                     |
| POST   | `/auth/login-json`         | JSON login for the mobile client       |
| GET    | `/auth/me`                 | Current user (Bearer token)            |
| POST   | `/auth/forgot-password`    | Email a reset link if the address has an account (always returns generic success) |
| POST   | `/auth/reset-password`     | Consume a reset token, set a new password |
| POST   | `/users/me/onboarding`     | Save 3+ interests                      |
| GET    | `/posts?feed=for-you`      | Feed; `feed=all\|for-you`, `category`, `before` cursor |
| POST   | `/posts`                   | Create a post                          |
| POST   | `/posts/{id}/upvote`       | Toggle upvote (returns updated post)   |
| PUT    | `/posts/{id}/bookmark`     | Toggle bookmark                        |
| GET    | `/posts/library`           | Bookmarked posts                       |
| GET    | `/posts/{id}/comments`     | Threaded comments                      |
| POST   | `/posts/{id}/comments`     | Add a comment                          |
| GET    | `/notifications`           | Your notifications                     |
| POST   | `/admin/agent/post`        | Publish an official @supasift post (admin token, not a user JWT) |

All routes except signup/login require an `Authorization: Bearer <token>` header.

`/admin/agent/post` is protected by a separate shared secret rather than a user
JWT: send `Authorization: Bearer <EUREKA_ADMIN_TOKEN>`. It publishes a post from
the official (verified) @supasift account, creating that account on first use, and
flags the post with `is_agent_post`. Categories use lowercase slugs (`physics`,
`astronomy`, `biology`, `chemistry`, `math`, `earth-science`, `technology`,
`medicine`).

## Renaming the official account

The official account is found by username (`AGENT_USERNAME`, default
`supasift`). A database seeded before the Supasift rebrand still holds it as
`@eureka`, and the lookup would miss it and create a duplicate — orphaning
every post already published under the old name. Rename it in place once per
deployed database (dry run by default):

```bash
MONGODB_URI='<connection string>' DRY_RUN=true  python rename_official_account.py
MONGODB_URI='<connection string>' DRY_RUN=false python rename_official_account.py
```

It's idempotent, and refuses to act if both usernames somehow exist.

## Notes

- Pagination on the feed uses a keyset cursor (`before` = the `created_at` of the
  last post you saw) for stable infinite scroll.
- `for-you` filters to the user's chosen interest categories; `all` shows
  everything.
- CORS allows `CORS_ORIGINS` (comma-separated, defaults to local web dev + the
  deployed Vercel frontend) plus any `*.vercel.app` preview deployment via
  regex. Native/mobile clients aren't subject to CORS at all.

## Deploying to Railway

1. **Create the service.** In Railway, "New Project" → "Deploy from GitHub repo"
   → select this backend's repo (set the **Root Directory** to `backend` if it
   lives alongside other apps in a monorepo).
2. **Add MongoDB.** "New" → "Database" → "Add MongoDB" in the same project.
   Railway provisions it and exposes a connection string.
3. **Set environment variables** on the backend service:

   | Variable        | Value                                                                                                                       |
   | ---------------- | ---------------------------------------------------------------------------------------------------------------------------- |
   | `MONGODB_URI`    | Reference the Mongo plugin's connection string (select it as a variable reference, e.g. `${{MongoDB.MONGO_URL}}`)            |
   | `MONGO_DB`       | `eureka`                                                                                                                     |
   | `JWT_SECRET`     | A long random string — **do not reuse the dev default**                                                                      |
   | `CORS_ORIGINS`   | `https://supasift.com,https://www.supasift.com` (comma-separate to add more)                                                 |
   | `EUREKA_ADMIN_TOKEN` | Shared secret for the protected admin routes (`POST /admin/agent/post`). Use a long random string; leave blank to disable |
   | `RESEND_API_KEY` | API key from [resend.com](https://resend.com) — see below. Leave blank to disable password reset emails (link is only logged) |
   | `EMAIL_FROM`     | `Supasift <onboarding@resend.dev>` until a domain is verified in Resend, then `Supasift <noreply@supasift.com>` |
   | `FRONTEND_URL`   | `https://supasift.com` — used to build the link inside reset emails |

   Railway also injects `PORT` automatically — no need to set it yourself.

   **Getting a Resend API key:** sign up free at [resend.com](https://resend.com)
   (no credit card, 3,000 emails/month / 100/day free tier) → **API Keys** in
   the sidebar → **Create API Key** → give it a name and "Sending access" →
   copy the key (shown once) into `RESEND_API_KEY`. Out of the box you can only
   send to the email address you signed up with; to email real users, add your
   domain under **Domains** → **Add Domain** and add the DNS records it gives
   you, then switch `EMAIL_FROM` to an address on that domain.
4. **Deploy.** Railway detects Python via Nixpacks, installs `requirements.txt`,
   and runs the start command from `railway.json` / `Procfile`:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. **Seed the database (optional, once).** With the Railway CLI linked to the
   project, run `railway run python seed.py` from the `backend` directory to
   seed the deployed MongoDB the same way local dev is seeded.
6. **Point the frontend at it.** Set `NEXT_PUBLIC_API_URL` on Vercel to the
   Railway-issued domain (e.g. `https://eureka-api-production.up.railway.app`).
