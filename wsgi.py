from app import create_app
from app.db import execute_query
from werkzeug.security import generate_password_hash

app = create_app()

def init_and_seed_db():
    with app.app_context():
        # 1. Create Tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'STORE_PERSON',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                failed_login_attempts INT DEFAULT 0,
                is_locked BOOLEAN DEFAULT FALSE,
                locked_until TIMESTAMP,
                last_login_attempt TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                parent_id INT REFERENCES categories(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS brands (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL
            );
            """,
          
"""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_url VARCHAR(255) DEFAULT 'default_product.png',
    brand_id INT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    category_id INT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 5,
    cost_price NUMERIC(10, 2) NOT NULL,
    retail_price NUMERIC(10, 2) NOT NULL
);
"""
        ]
        for t in tables:
            execute_query(t, commit=True)

        # 1.5 Add Missing Columns (Migrations)
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INT DEFAULT 0;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_attempt TIMESTAMP;"
        ]
        for migration in migrations:
            try:
                execute_query(migration, commit=True)
            except Exception as e:
                # Column might already exist or other error - continue
                print(f"Migration note: {e}")

        # 2. Seed Default Admin & Store User
        admin_exists = execute_query("SELECT id FROM users WHERE username = %s;", ('admin',), fetchone=True)
        if not admin_exists:
            execute_query(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s);",
                ('admin', 'admin@techstore.com', generate_password_hash('admin123'), 'ADMIN'),
                commit=True
            )
            execute_query(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s);",
                ('store', 'store@techstore.com', generate_password_hash('store123'), 'STORE_PERSON'),
                commit=True
            )

        # 3. Seed Keyboards/Monitors Catalog if empty
        cat_exists = execute_query("SELECT id FROM categories LIMIT 1;", fetchone=True)
        if not cat_exists:
            execute_query("INSERT INTO categories (name) VALUES (%s), (%s), (%s);", ('Keyboards', 'Mice', 'Monitors'), commit=True)
            kb_cat = execute_query("SELECT id FROM categories WHERE name = %s;", ('Keyboards',), fetchone=True)
            
            execute_query(
                "INSERT INTO categories (name, parent_id) VALUES (%s, %s), (%s, %s), (%s, %s);",
                ('Mechanical Keyboards', kb_cat['id'], 'Silent Keyboards', kb_cat['id'], 'Simple Membrane Keyboards', kb_cat['id']),
                commit=True
            )
            execute_query("INSERT INTO brands (name) VALUES (%s), (%s), (%s);", ('Logitech', 'Razer', 'Dell'), commit=True)

            b_razer = execute_query("SELECT id FROM brands WHERE name = %s;", ('Razer',), fetchone=True)
            b_logi = execute_query("SELECT id FROM brands WHERE name = %s;", ('Logitech',), fetchone=True)
            b_dell = execute_query("SELECT id FROM brands WHERE name = %s;", ('Dell',), fetchone=True)

            sub_mech = execute_query("SELECT id FROM categories WHERE name = %s;", ('Mechanical Keyboards',), fetchone=True)
            sub_silent = execute_query("SELECT id FROM categories WHERE name = %s;", ('Silent Keyboards',), fetchone=True)
            sub_simple = execute_query("SELECT id FROM categories WHERE name = %s;", ('Simple Membrane Keyboards',), fetchone=True)

            products = [
                ('KB-MECH-01', 'BlackWidow V4 Pro', b_razer['id'], sub_mech['id'], 12, 3, 150.00, 220.00),
                ('KB-SLNT-01', 'MX Keys S Silent', b_logi['id'], sub_silent['id'], 2, 5, 80.00, 110.00),
                ('KB-SMPL-01', 'Dell Wired K216', b_dell['id'], sub_simple['id'], 0, 5, 10.00, 18.00),
                ('KB-MECH-02', 'BlackWidow V4\5 Pro', b_razer['id'], sub_mech['id'], 12, 3, 240.00, 220.00),
                ('KB-SLNT-02', 'MX Keys S2 Silent', b_logi['id'], sub_silent['id'], 2, 5, 48.00, 110.00),
                ('KB-SMPL-03', 'Dell Wired K3216', b_dell['id'], sub_simple['id'], 0, 5, 29.00, 18.00)
                
            ]
            for p in products:
                execute_query(
                    """
                    INSERT INTO products (sku, name, brand_id, category_id, quantity, reorder_level, cost_price, retail_price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    p, commit=True
                )
init_and_seed_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)