CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    stock_on_hand INTEGER NOT NULL CHECK (stock_on_hand >= 0),
    reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0)
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id TEXT PRIMARY KEY NOT NULL,
    sale_date TEXT NOT NULL,
    sku TEXT NOT NULL REFERENCES products(sku),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_paise INTEGER NOT NULL CHECK (unit_price_paise > 0)
);

CREATE TABLE IF NOT EXISTS rejected_sales (
    line_number INTEGER PRIMARY KEY,
    sale_id TEXT,
    reason TEXT NOT NULL,
    raw_row TEXT NOT NULL
);
