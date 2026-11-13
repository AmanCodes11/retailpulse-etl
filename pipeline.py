"""Load a complete retail CSV snapshot into SQLite and print SQL reports."""

import csv
from contextlib import closing
from datetime import date
import json
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATABASE = ROOT / "retailpulse.db"

PRODUCT_FIELDS = ("sku", "name", "stock_on_hand", "reorder_level")
SALE_FIELDS = ("sale_id", "sale_date", "sku", "quantity", "unit_price_inr")


def read_csv(path, fields):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != list(fields):
            raise ValueError(f"{path.name} needs these columns: {', '.join(fields)}")
        previous_line = reader.line_num
        for row in reader:
            yield previous_line + 1, row
            previous_line = reader.line_num


def clean_fields(row):
    if None in row or any(value is None for value in row.values()):
        raise ValueError("wrong number of columns")
    return {key: value.strip() for key, value in row.items()}


def required(value, field):
    if not value:
        raise ValueError(f"{field} is blank")
    return value


def whole_number(value, field, minimum):
    if not re.fullmatch(r"[0-9]{1,9}", value) or int(value) < minimum:
        raise ValueError(f"{field} must be a whole number from {minimum} to 999999999")
    return int(value)


def price_in_paise(value):
    if not re.fullmatch(r"[0-9]{1,5}(\.[0-9]{1,2})?", value):
        raise ValueError("unit price must have up to five rupee digits and two decimal places")
    rupees, _, paise = value.partition(".")
    amount = int(rupees) * 100 + int(paise.ljust(2, "0"))
    if amount == 0:
        raise ValueError("unit price must be positive")
    return amount


def extract_products():
    products = {}
    for line, raw in read_csv(DATA / "products.csv", PRODUCT_FIELDS):
        try:
            row = clean_fields(raw)
            sku = required(row["sku"], "sku").upper()
            if sku in products:
                raise ValueError("duplicate product SKU")
            products[sku] = (
                sku,
                required(row["name"], "name"),
                whole_number(row["stock_on_hand"], "stock_on_hand", 0),
                whole_number(row["reorder_level"], "reorder_level", 0),
            )
        except ValueError as error:
            raise ValueError(f"products.csv line {line}: {error}") from error
    if not products:
        raise ValueError("products.csv must contain at least one product")
    return products


def extract_sales(products):
    sales = {}
    rejected = []
    for line, raw in read_csv(DATA / "sales.csv", SALE_FIELDS):
        sale_id = (raw.get("sale_id") or "").strip().upper()
        try:
            row = clean_fields(raw)
            required(sale_id, "sale_id")
            if sale_id in sales:
                raise ValueError("duplicate sale ID")
            sold_on = date.fromisoformat(row["sale_date"]).isoformat()
            if sold_on != row["sale_date"]:
                raise ValueError("sale date must use YYYY-MM-DD")
            sku = required(row["sku"], "sku").upper()
            if sku not in products:
                raise ValueError(f"unknown SKU {sku}")
            sales[sale_id] = (
                sale_id, sold_on, sku,
                whole_number(row["quantity"], "quantity", 1),
                price_in_paise(row["unit_price_inr"]),
            )
        except ValueError as error:
            rejected.append((line, sale_id or None, str(error), json.dumps(raw)))
    return sales, rejected


def load_snapshot(connection, products, sales, rejected):
    connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    connection.executescript((ROOT / "reports.sql").read_text(encoding="utf-8"))
    # Replace all data in one transaction. A failed insert rolls back the refresh.
    with connection:
        connection.execute("DELETE FROM sales")
        connection.execute("DELETE FROM products")
        connection.execute("DELETE FROM rejected_sales")
        connection.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products.values())
        connection.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?)", sales.values())
        connection.executemany("INSERT INTO rejected_sales VALUES (?, ?, ?, ?)", rejected)


def format_rupees(paise):
    return f"INR {paise // 100:,}.{paise % 100:02d}"


def print_reports(connection):
    print("\nDaily revenue")
    for day, lines, revenue in connection.execute(
        "SELECT * FROM daily_revenue ORDER BY sale_date"
    ):
        print(f"  {day} | {lines} sale lines | {format_rupees(revenue)}")

    print("\nProducts by units sold")
    for sku, name, units, revenue in connection.execute(
        "SELECT * FROM product_sales ORDER BY units_sold DESC, sku"
    ):
        print(f"  {sku} | {name} | {units} units | {format_rupees(revenue)}")

    print("\nLow-stock products")
    for sku, name, stock, threshold in connection.execute(
        "SELECT * FROM low_stock ORDER BY stock_on_hand, sku"
    ):
        print(f"  {sku} | {name} | stock {stock} | threshold {threshold}")

    print("\nRejected sales")
    for line, sale_id, reason in connection.execute(
        "SELECT line_number, sale_id, reason FROM rejected_sales ORDER BY line_number"
    ):
        print(f"  CSV line {line} | {sale_id or '(blank)'} | {reason}")


def main():
    products = extract_products()
    sales, rejected = extract_sales(products)
    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        load_snapshot(connection, products, sales, rejected)
        print(f"Loaded {len(products)} products and {len(sales)} sales. Rejected {len(rejected)} rows.")
        print_reports(connection)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error, sqlite3.Error) as error:
        raise SystemExit(f"Pipeline failed: {error}") from None
