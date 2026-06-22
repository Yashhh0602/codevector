# Product Browser — CodeVector 

Browse 200,000 products newest-first, filter by category, paginate without missing or repeating anything even when new data arrives.

**Live URL:** https://codevector-2.onrender.com  
**Stack:** FastAPI · PostgreSQL (Neon) · Deployed on Render

---

## The core engineering decision: why cursor pagination

The obvious approach is `OFFSET / LIMIT`:

```sql
SELECT * FROM products ORDER BY created_at DESC LIMIT 50 OFFSET 100;
```

This breaks as soon as the dataset changes. If 50 new products are inserted while someone is on page 2, every subsequent page shifts by 50 rows — the user sees duplicates on the next page and misses the rows that fell off the edge. OFFSET also gets slower the deeper you go: the database must scan and discard all preceding rows on every request.

**Cursor pagination** solves both problems. Instead of "skip N rows", you ask:

```sql
SELECT * FROM products
WHERE (created_at, id) < ($last_seen_created_at, $last_seen_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

Your position is anchored to the last item you saw, not to a row number. New insertions at the top of the table are completely invisible to your current traversal — you never drift. And the composite index `(created_at DESC, id DESC)` makes every page O(log n) regardless of depth.

The `id` tiebreaker handles the edge case where multiple products share the exact same `created_at` timestamp, making the cursor always unique and deterministic.

Cursors are serialised as base64 JSON tokens so the client treats them as opaque blobs — the encoding can change server-side without breaking API consumers.

---

## Project structure

```
.
├── app/
│   ├── main.py          # FastAPI app — products, categories, stats endpoints
│   └── static/
│       └── index.html   # Optional UI (bonus)
├── scripts/
│   └── seed.py          # Generates 200,000 products in bulk
├── requirements.txt
├── Procfile             # Render start command
└── render.yaml
```

---

## Run locally

```bash
# 1. Set your database URL
export DATABASE_URL="postgresql://user:pass@host/db"

# 2. Seed the database (one-time)
python scripts/seed.py

# 3. Start the server
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API is at `http://localhost:8000`, UI at `http://localhost:8000/`.

---

## API

| Endpoint | Description |
|---|---|
| `GET /products` | List products. Params: `category`, `cursor`, `limit` (default 50) |
| `GET /categories` | All distinct categories |
| `GET /stats` | Total count + date range |
| `GET /health` | Healthcheck |

**Pagination flow:**
```
GET /products → { items: [...], next_cursor: "abc123", has_next: true }
GET /products?cursor=abc123 → next page, anchored to your position
```

---

## Seed script

Uses psycopg v3's `execute_values` for bulk inserts — no Python loop, one round-trip per 10,000 rows. Generates 200k products in ~10–15 seconds depending on network latency to the database.

---

## What I'd improve with more time

- **Connection pooling** (PgBouncer or asyncpg + a pool) — right now each request opens a new connection, which is fine for low traffic but won't scale
- **Category count in sidebar** — a single aggregation query at load time
- **Search** — full-text index on `name` with a `?q=` param
- **Rate limiting** on the API

---

## How I used AI

Used Claude to scaffold the FastAPI boilerplate, write the HTML/CSS/JS for the bonus UI, and check psycopg v3 syntax.

The core pagination design (cursor vs offset, the composite index choice, the tiebreaker reasoning) I worked out myself — that's the part that matters and the part I'd need to explain and extend live.

Nothing Claude produced was wrong in a way I had to catch — the main value was speed on the boilerplate so I could focus on the interesting parts.
