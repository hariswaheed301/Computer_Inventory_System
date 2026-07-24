"""Manually add products for testing inventory pagination.

Run this file only when you want pagination test data:
    .\\venv\\Scripts\\python.exe seed_test_products.py

It adds 25 products once. Re-running it does not duplicate rows because every
test product has a unique SKU and conflicts are ignored.
"""

from app.db import execute_query
from wsgi import app, init_and_seed_db


def seed_pagination_products():
    # Ensure the application tables and the original small catalog exist first.
    init_and_seed_db()

    with app.app_context():
        categories = execute_query(
            "SELECT id, name FROM categories WHERE name IN (%s, %s, %s);",
            ('Mechanical Keyboards', 'Silent Keyboards', 'Simple Membrane Keyboards'),
            fetchall=True,
        ) or []
        brands = execute_query(
            "SELECT id, name FROM brands WHERE name IN (%s, %s, %s);",
            ('Logitech', 'Razer', 'Dell'),
            fetchall=True,
        ) or []

        category_ids = {category['name']: category['id'] for category in categories}
        brand_ids = {brand['name']: brand['id'] for brand in brands}
        if len(category_ids) != 3 or len(brand_ids) != 3:
            raise RuntimeError('The default categories and brands were not created.')

        test_products = []
        product_types = [
            ('Razer', 'Mechanical Keyboards', 'Mechanical Keyboard'),
            ('Logitech', 'Silent Keyboards', 'Silent Keyboard'),
            ('Dell', 'Simple Membrane Keyboards', 'Membrane Keyboard'),
        ]

        for number in range(1, 26):
            brand, category, product_type = product_types[(number - 1) % len(product_types)]
            test_products.append((
                f'PAGE-TEST-{number:02d}',
                f'Test {product_type} {number:02d}',
                f'Pagination test product {number:02d}.',
                'default_product.png',
                brand_ids[brand],
                category_ids[category],
                number % 12,
                3,
                20.00 + number,
                35.00 + number,
            ))

        inserted = 0
        for product in test_products:
            result = execute_query(
                """
                INSERT INTO products (
                    sku, name, description, image_url, brand_id, category_id,
                    quantity, reorder_level, cost_price, retail_price
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sku) DO NOTHING
                RETURNING id;
                """,
                product,
                fetchone=True,
                commit=True,
            )
            inserted += int(result is not None)

        total = execute_query("SELECT COUNT(*) AS total FROM products;", fetchone=True)
        print(f'Added {inserted} pagination test products. Total products: {total["total"]}.')


if __name__ == '__main__':
    seed_pagination_products()
