-- QueryMind application database schema
-- Run this against the querymind database (not business_data)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS query_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
);

CREATE INDEX IF NOT EXISTS idx_query_history_session_id ON query_history(session_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC);

-- Business data database schema
-- Run this against the business_data database

-- (Separate connection required for the following tables)
-- These are created by seed.py against ANALYST_DB_URL

-- customers
-- CREATE TABLE customers (
--     id SERIAL PRIMARY KEY,
--     first_name VARCHAR(100) NOT NULL,
--     last_name VARCHAR(100) NOT NULL,
--     email VARCHAR(255) UNIQUE NOT NULL,
--     city VARCHAR(100),
--     country VARCHAR(100),
--     signup_date DATE NOT NULL,
--     customer_segment VARCHAR(20) NOT NULL CHECK (customer_segment IN ('new', 'returning', 'vip'))
-- );

-- products
-- CREATE TABLE products (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     category VARCHAR(100) NOT NULL,
--     subcategory VARCHAR(100),
--     price NUMERIC(10, 2) NOT NULL,
--     cost NUMERIC(10, 2) NOT NULL,
--     stock_quantity INTEGER NOT NULL DEFAULT 0,
--     supplier VARCHAR(255),
--     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- );

-- orders
-- CREATE TABLE orders (
--     id SERIAL PRIMARY KEY,
--     customer_id INTEGER NOT NULL REFERENCES customers(id),
--     order_date DATE NOT NULL,
--     status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'shipped', 'delivered', 'cancelled')),
--     total_amount NUMERIC(12, 2) NOT NULL,
--     shipping_city VARCHAR(100),
--     shipping_country VARCHAR(100),
--     payment_method VARCHAR(50)
-- );

-- order_items
-- CREATE TABLE order_items (
--     id SERIAL PRIMARY KEY,
--     order_id INTEGER NOT NULL REFERENCES orders(id),
--     product_id INTEGER NOT NULL REFERENCES products(id),
--     quantity INTEGER NOT NULL,
--     unit_price NUMERIC(10, 2) NOT NULL,
--     discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0
-- );

-- sales_reps
-- CREATE TABLE sales_reps (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     region VARCHAR(100),
--     email VARCHAR(255) UNIQUE NOT NULL,
--     hire_date DATE NOT NULL,
--     target_monthly NUMERIC(12, 2) NOT NULL
-- );

-- support_tickets
-- CREATE TABLE support_tickets (
--     id SERIAL PRIMARY KEY,
--     customer_id INTEGER NOT NULL REFERENCES customers(id),
--     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
--     resolved_at TIMESTAMPTZ,
--     category VARCHAR(100),
--     status VARCHAR(20) NOT NULL CHECK (status IN ('open', 'closed')),
--     satisfaction_score INTEGER CHECK (satisfaction_score BETWEEN 1 AND 5)
-- );
