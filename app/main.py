import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CodeVector Product API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def encode_cursor(created_at: datetime, id: int) -> str:
    payload = {"created_at": created_at.isoformat(), "id": id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["created_at"]), payload["id"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products")
def list_products(
    category: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    params = []
    conditions = []

    if category:
        conditions.append("category = %s")
        params.append(category)

    if cursor:
        cur_created_at, cur_id = decode_cursor(cursor)
        conditions.append("(created_at, id) < (%s, %s)")
        params.extend([cur_created_at, cur_id])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT id, name, category, price, created_at, updated_at
        FROM products
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT %s
    """
    params.append(limit + 1)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    has_next = len(rows) > limit
    items = rows[:limit]

    next_cursor = None
    if has_next and items:
        last = items[-1]
        next_cursor = encode_cursor(last["created_at"], last["id"])

    return {
        "items": [
            {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "price": float(r["price"]),
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in items
        ],
        "next_cursor": next_cursor,
        "has_next": has_next,
        "count": len(items),
    }


@app.get("/categories")
def list_categories():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT category FROM products ORDER BY category")
            rows = cur.fetchall()
    return {"categories": [r["category"] for r in rows]}


@app.get("/stats")
def stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total, MIN(created_at) as oldest, MAX(created_at) as newest FROM products")
            row = cur.fetchone()
    return {
        "total_products": row["total"],
        "oldest": row["oldest"].isoformat() if row["oldest"] else None,
        "newest": row["newest"].isoformat() if row["newest"] else None,
    }
