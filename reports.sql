CREATE VIEW IF NOT EXISTS daily_revenue AS
SELECT sale_date, COUNT(*) AS sale_lines,
       SUM(quantity * unit_price_paise) AS revenue_paise
FROM sales
GROUP BY sale_date;

CREATE VIEW IF NOT EXISTS product_sales AS
SELECT p.sku, p.name, COALESCE(SUM(s.quantity), 0) AS units_sold,
       COALESCE(SUM(s.quantity * s.unit_price_paise), 0) AS revenue_paise
FROM products AS p
LEFT JOIN sales AS s ON s.sku = p.sku
GROUP BY p.sku, p.name;

CREATE VIEW IF NOT EXISTS low_stock AS
SELECT sku, name, stock_on_hand, reorder_level
FROM products
WHERE stock_on_hand <= reorder_level;
