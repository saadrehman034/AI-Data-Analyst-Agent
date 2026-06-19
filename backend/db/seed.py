"""
Seed the business_data PostgreSQL database with realistic e-commerce data.
Run: python -m backend.db.seed
"""

import asyncio
import random
import logging
from datetime import date, timedelta
from decimal import Decimal

import asyncpg
from faker import Faker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()
Faker.seed(42)
random.seed(42)

PRODUCT_CATEGORIES = {
    "Electronics": {
        "subcategories": ["Smartphones", "Laptops", "Tablets", "Headphones", "Cameras", "Smart Home"],
        "price_range": (49.99, 1999.99),
        "margin": 0.25,
    },
    "Clothing": {
        "subcategories": ["Men's Tops", "Women's Tops", "Jeans", "Dresses", "Outerwear", "Sportswear"],
        "price_range": (9.99, 299.99),
        "margin": 0.55,
    },
    "Home & Kitchen": {
        "subcategories": ["Cookware", "Furniture", "Bedding", "Decor", "Storage", "Lighting"],
        "price_range": (14.99, 899.99),
        "margin": 0.45,
    },
    "Books": {
        "subcategories": ["Fiction", "Non-fiction", "Business", "Science", "Children's", "Textbooks"],
        "price_range": (5.99, 79.99),
        "margin": 0.60,
    },
    "Sports & Outdoors": {
        "subcategories": ["Fitness", "Camping", "Cycling", "Running", "Team Sports", "Water Sports"],
        "price_range": (19.99, 599.99),
        "margin": 0.40,
    },
    "Beauty": {
        "subcategories": ["Skincare", "Makeup", "Haircare", "Fragrance", "Men's Grooming", "Wellness"],
        "price_range": (7.99, 249.99),
        "margin": 0.65,
    },
    "Toys & Games": {
        "subcategories": ["Board Games", "Action Figures", "LEGO", "Puzzles", "Outdoor Toys", "Educational"],
        "price_range": (9.99, 199.99),
        "margin": 0.50,
    },
    "Food & Grocery": {
        "subcategories": ["Snacks", "Beverages", "Organic", "Condiments", "Baking", "Coffee & Tea"],
        "price_range": (2.99, 59.99),
        "margin": 0.30,
    },
}

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay", "bank_transfer"]
ORDER_STATUSES = ["pending", "shipped", "delivered", "cancelled"]
ORDER_STATUS_WEIGHTS = [0.08, 0.12, 0.72, 0.08]
SUPPORT_CATEGORIES = ["shipping", "returns", "payment", "product_quality", "account", "other"]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
COUNTRIES = [
    "United States", "United Kingdom", "Germany", "France", "Canada", "Australia",
    "Japan", "Brazil", "India", "Mexico", "Netherlands", "Spain", "Italy", "Sweden",
    "Singapore", "UAE", "South Korea", "Poland", "Argentina", "South Africa",
]
COUNTRY_CITIES = {
    "United States": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia"],
    "United Kingdom": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool"],
    "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart"],
    "France": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Edmonton"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast"],
    "Japan": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo", "Kobe"],
    "Brazil": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza", "Curitiba"],
    "India": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad"],
    "Mexico": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "León"],
}

SUPPLIERS = [
    "GlobalTech Imports", "PrimeCo Manufacturing", "EcoSource Ltd", "FastShip Wholesale",
    "QualityFirst Distributors", "NovaTech Supplies", "Heritage Goods Co", "BlueSky Trading",
    "PeakPerformance Inc", "SunRise Products", "EliteSupply Chain", "NatureWorks Corp",
]

SALES_REP_NAMES = [
    ("Jordan", "Mitchell"), ("Alex", "Thompson"), ("Casey", "Rivera"), ("Riley", "Johnson"),
    ("Morgan", "Chen"), ("Taylor", "Williams"), ("Avery", "Brown"), ("Cameron", "Davis"),
    ("Quinn", "Martinez"), ("Peyton", "Anderson"), ("Skylar", "Garcia"), ("Reese", "Wilson"),
    ("Emerson", "Lee"), ("Finley", "Taylor"), ("Harlow", "Moore"), ("Sage", "Jackson"),
    ("Rowan", "White"), ("Blake", "Harris"), ("Drew", "Clark"), ("Parker", "Lewis"),
]


def random_date(start: date, end: date) -> date:
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


async def create_business_schema(conn: asyncpg.Connection):
    logger.info("Creating business_data schema...")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            city VARCHAR(100),
            country VARCHAR(100),
            signup_date DATE NOT NULL,
            customer_segment VARCHAR(20) NOT NULL CHECK (customer_segment IN ('new', 'returning', 'vip'))
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            subcategory VARCHAR(100),
            price NUMERIC(10, 2) NOT NULL,
            cost NUMERIC(10, 2) NOT NULL,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            supplier VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            order_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'shipped', 'delivered', 'cancelled')),
            total_amount NUMERIC(12, 2) NOT NULL,
            shipping_city VARCHAR(100),
            shipping_country VARCHAR(100),
            payment_method VARCHAR(50)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER NOT NULL,
            unit_price NUMERIC(10, 2) NOT NULL,
            discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS sales_reps (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            region VARCHAR(100),
            email VARCHAR(255) UNIQUE NOT NULL,
            hire_date DATE NOT NULL,
            target_monthly NUMERIC(12, 2) NOT NULL
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMPTZ,
            category VARCHAR(100),
            status VARCHAR(20) NOT NULL CHECK (status IN ('open', 'closed')),
            satisfaction_score INTEGER CHECK (satisfaction_score BETWEEN 1 AND 5)
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_customer_id ON support_tickets(customer_id)")
    logger.info("Schema created successfully")


async def seed_customers(conn: asyncpg.Connection, count: int = 2000) -> list[int]:
    logger.info(f"Seeding {count} customers...")
    start_date = date(2021, 1, 1)
    end_date = date(2024, 12, 31)
    records = []
    emails_seen = set()

    for i in range(count):
        first = fake.first_name()
        last = fake.last_name()
        email = f"{first.lower()}.{last.lower()}{random.randint(1, 9999)}@{fake.free_email_domain()}"
        while email in emails_seen:
            email = f"{first.lower()}.{last.lower()}{random.randint(1, 99999)}@{fake.free_email_domain()}"
        emails_seen.add(email)

        country = random.choice(COUNTRIES)
        cities = COUNTRY_CITIES.get(country, [fake.city()])
        city = random.choice(cities)

        signup = random_date(start_date, end_date)
        days_since_signup = (end_date - signup).days
        if days_since_signup > 730 and random.random() < 0.15:
            segment = "vip"
        elif days_since_signup > 180 and random.random() < 0.45:
            segment = "returning"
        else:
            segment = "new"

        records.append((first, last, email, city, country, signup, segment))

    await conn.executemany(
        "INSERT INTO customers (first_name, last_name, email, city, country, signup_date, customer_segment) VALUES ($1,$2,$3,$4,$5,$6,$7)",
        records
    )
    rows = await conn.fetch("SELECT id FROM customers ORDER BY id")
    ids = [r["id"] for r in rows]
    logger.info(f"Seeded {len(ids)} customers")
    return ids


async def seed_products(conn: asyncpg.Connection, count: int = 500) -> list[int]:
    logger.info(f"Seeding {count} products...")
    records = []
    for _ in range(count):
        category = random.choice(list(PRODUCT_CATEGORIES.keys()))
        info = PRODUCT_CATEGORIES[category]
        subcategory = random.choice(info["subcategories"])
        price = round(random.uniform(*info["price_range"]), 2)
        cost = round(price * (1 - info["margin"]) * random.uniform(0.85, 1.15), 2)
        stock = random.randint(0, 1000)
        supplier = random.choice(SUPPLIERS)
        created_at = fake.date_time_between(start_date="-4y", end_date="now")

        adj = random.choice(["Premium", "Classic", "Pro", "Ultra", "Essential", "Deluxe", "Smart", "Eco"])
        name = f"{adj} {subcategory.rstrip('s')} {fake.lexify('???').upper()}"
        records.append((name, category, subcategory, price, cost, stock, supplier, created_at))

    await conn.executemany(
        "INSERT INTO products (name, category, subcategory, price, cost, stock_quantity, supplier, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
        records
    )
    rows = await conn.fetch("SELECT id, price FROM products ORDER BY id")
    logger.info(f"Seeded {len(rows)} products")
    return [(r["id"], float(r["price"])) for r in rows]


async def seed_sales_reps(conn: asyncpg.Connection) -> list[int]:
    logger.info("Seeding sales reps...")
    records = []
    start = date(2018, 1, 1)
    end = date(2024, 1, 1)
    for first, last in SALES_REP_NAMES:
        region = random.choice(REGIONS)
        email = f"{first.lower()}.{last.lower()}@querymind-sales.com"
        hire = random_date(start, end)
        target = round(random.uniform(50000, 250000), 2)
        records.append((f"{first} {last}", region, email, hire, target))

    await conn.executemany(
        "INSERT INTO sales_reps (name, region, email, hire_date, target_monthly) VALUES ($1,$2,$3,$4,$5)",
        records
    )
    rows = await conn.fetch("SELECT id FROM sales_reps ORDER BY id")
    return [r["id"] for r in rows]


async def seed_orders_and_items(
    conn: asyncpg.Connection,
    customer_ids: list[int],
    product_id_prices: list[tuple[int, float]],
    order_count: int = 10000,
):
    logger.info(f"Seeding {order_count} orders with line items...")
    start_date = date(2022, 1, 1)
    end_date = date(2024, 12, 31)

    order_batch = []
    for _ in range(order_count):
        cid = random.choice(customer_ids)
        order_date = random_date(start_date, end_date)
        status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0]
        country = random.choice(COUNTRIES)
        cities = COUNTRY_CITIES.get(country, [fake.city()])
        city = random.choice(cities)
        payment = random.choice(PAYMENT_METHODS)
        order_batch.append((cid, order_date, status, 0.0, city, country, payment))

    await conn.executemany(
        "INSERT INTO orders (customer_id, order_date, status, total_amount, shipping_city, shipping_country, payment_method) VALUES ($1,$2,$3,$4,$5,$6,$7)",
        order_batch
    )
    order_rows = await conn.fetch("SELECT id FROM orders ORDER BY id")
    order_ids = [r["id"] for r in order_rows]

    logger.info("Seeding order items...")
    item_batch = []
    order_totals: dict[int, float] = {}

    for oid in order_ids:
        n_items = random.choices([1, 2, 3, 4, 5], weights=[0.4, 0.3, 0.15, 0.1, 0.05])[0]
        selected = random.sample(product_id_prices, min(n_items, len(product_id_prices)))
        for pid, base_price in selected:
            qty = random.randint(1, 5)
            discount = random.choices([0, 5, 10, 15, 20, 25], weights=[0.5, 0.15, 0.15, 0.1, 0.07, 0.03])[0]
            unit_price = round(base_price * random.uniform(0.95, 1.05), 2)
            item_batch.append((oid, pid, qty, unit_price, discount))
            line_total = unit_price * qty * (1 - discount / 100)
            order_totals[oid] = order_totals.get(oid, 0.0) + line_total

    await conn.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent) VALUES ($1,$2,$3,$4,$5)",
        item_batch
    )

    logger.info("Updating order totals...")
    total_records = [(round(v, 2), k) for k, v in order_totals.items()]
    await conn.executemany("UPDATE orders SET total_amount = $1 WHERE id = $2", total_records)

    logger.info(f"Seeded {len(order_ids)} orders and {len(item_batch)} order items")


async def seed_support_tickets(conn: asyncpg.Connection, customer_ids: list[int], count: int = 3000):
    logger.info(f"Seeding {count} support tickets...")
    records = []
    for _ in range(count):
        cid = random.choice(customer_ids)
        created = fake.date_time_between(start_date="-3y", end_date="now")
        category = random.choice(SUPPORT_CATEGORIES)
        is_closed = random.random() < 0.78
        status = "closed" if is_closed else "open"
        resolved = None
        score = None
        if is_closed:
            resolve_days = random.randint(1, 14)
            from datetime import datetime, timezone
            resolved = created + timedelta(days=resolve_days)
            score = random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.10, 0.20, 0.35, 0.30])[0]
        records.append((cid, created, resolved, category, status, score))

    await conn.executemany(
        "INSERT INTO support_tickets (customer_id, created_at, resolved_at, category, status, satisfaction_score) VALUES ($1,$2,$3,$4,$5,$6)",
        records
    )
    logger.info(f"Seeded {count} support tickets")


async def create_querymind_schema(conn: asyncpg.Connection):
    logger.info("Creating QueryMind app schema...")
    await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS query_sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id UUID NOT NULL REFERENCES query_sessions(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            generated_sql TEXT,
            result_row_count INTEGER,
            chart_type VARCHAR(20),
            insight TEXT,
            execution_time_ms INTEGER,
            had_error BOOLEAN NOT NULL DEFAULT FALSE,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_history_session_id ON query_history(session_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC)")
    logger.info("QueryMind schema created")


async def main():
    import os
    from dotenv import load_dotenv
    load_dotenv()

    analyst_url = os.getenv("ANALYST_DB_URL", "postgresql://postgres:password@localhost:5432/business_data")
    app_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/querymind")

    logger.info("Connecting to analyst database...")
    analyst_conn = await asyncpg.connect(analyst_url)
    try:
        await create_business_schema(analyst_conn)
        customer_ids = await seed_customers(analyst_conn, count=2000)
        product_id_prices = await seed_products(analyst_conn, count=500)
        await seed_sales_reps(analyst_conn)
        await seed_orders_and_items(analyst_conn, customer_ids, product_id_prices, order_count=10000)
        await seed_support_tickets(analyst_conn, customer_ids, count=3000)
        logger.info("Business data seeding complete!")
    finally:
        await analyst_conn.close()

    logger.info("Connecting to QueryMind app database...")
    app_conn = await asyncpg.connect(app_url)
    try:
        await create_querymind_schema(app_conn)
        logger.info("QueryMind app schema ready!")
    finally:
        await app_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
