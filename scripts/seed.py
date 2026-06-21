"""
Seed script: generates 200,000 products using a single bulk INSERT.

Why bulk and not a loop?
- A Python loop with individual INSERTs = ~200,000 round-trips → minutes
- A single VALUES batch or COPY FROM STDIN = one round-trip → seconds
We use execute_values (psycopg2) which batches rows into a small number of
multi-row INSERT statements, keeping memory bounded while staying fast.
"""

import os
import random
import sys
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL environment variable is required")

CATEGORIES = [
    "Electronics", "Clothing", "Books", "Home & Garden",
    "Sports", "Toys", "Beauty", "Automotive", "Food", "Music",
]

ADJECTIVES = ["Premium", "Vintage", "Smart", "Ultra", "Pro", "Classic", "Eco", "Lite", "Max", "Mini"]
NOUNS = ["Widget", "Gadget", "Device", "Tool", "Kit", "Set", "Pack", "Bundle", "Module", "Unit"]

TOTAL = 200_000
BATCH = 10_000  # rows per execute_values call

NOW = datetime.now(timezone.utc)


def random_product(i: int) -> tuple:
    name = f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {i:06d}"
    category = random.choice(CATEGORIES)
    price = round(random.uniform(1.99, 999.99), 2)
    # spread created_at over the past 2 years so newest-first ordering is meaningful
    offset_seconds = random.randint(0, 2 * 365 * 24 * 3600)
    created_at = NOW - timedelta(seconds=offset_seconds)
    updated_at = created_at + timedelta(seconds=random.randint(0, 3600))
    return (name, category, price, created_at, updated_at)


def main():
    print(f"Connecting to database…")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    with conn.cursor() as cur:
        print("Creating table + index if not exists…")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          BIGSERIAL PRIMARY KEY,
                name        TEXT        NOT NULL,
                category    TEXT        NOT NULL,
                price       NUMERIC(10, 2) NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        # Composite index covering the ORDER BY and the keyset WHERE clause.
        # category is included so category-filtered queries stay on the index.
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_cursor
            ON products (created_at DESC, id DESC);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_category_cursor
            ON products (category, created_at DESC, id DESC);
        """)
        conn.commit()

        print(f"Inserting {TOTAL:,} products in batches of {BATCH:,}…")
        inserted = 0
        while inserted < TOTAL:
            batch_size = min(BATCH, TOTAL - inserted)
            rows = [random_product(inserted + j) for j in range(batch_size)]
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO products (name, category, price, created_at, updated_at) VALUES %s",
                rows,
                page_size=BATCH,
            )
            conn.commit()
            inserted += batch_size
            print(f"  {inserted:,} / {TOTAL:,}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
