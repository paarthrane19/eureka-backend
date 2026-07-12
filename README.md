# Eureka API (FastAPI + MongoDB)

REST backend for the Eureka mobile app. JWT auth (bcrypt-hashed passwords),
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
| POST   | `/users/me/onboarding`     | Save 3+ interests                      |
| GET    | `/posts?feed=for-you`      | Feed; `feed=all\|for-you`, `category`, `before` cursor |
| POST   | `/posts`                   | Create a post                          |
| POST   | `/posts/{id}/upvote`       | Toggle upvote (returns updated post)   |
| PUT    | `/posts/{id}/bookmark`     | Toggle bookmark                        |
| GET    | `/posts/library`           | Bookmarked posts                       |
| GET    | `/posts/{id}/comments`     | Threaded comments                      |
| POST   | `/posts/{id}/comments`     | Add a comment                          |
| GET    | `/notifications`           | Your notifications                     |

All routes except signup/login require an `Authorization: Bearer <token>` header.

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
   | `CORS_ORIGINS`   | `https://projecteureka.vercel.app` (comma-separate to add more)                                                              |

   Railway also injects `PORT` automatically — no need to set it yourself.
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
