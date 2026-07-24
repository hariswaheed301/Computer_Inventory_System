from app.db import execute_query

class Category:
    """
    Model for managing Categories and Subcategories using Raw SQL.
    """
    def __init__(self, id=None, name=None, parent_id=None):
        self.id = id
        self.name = name
        self.parent_id = parent_id

    @classmethod
    def create(cls, name, parent_id=None):
        sql = "INSERT INTO categories (name, parent_id) VALUES (%s, %s) RETURNING id;"
        res = execute_query(sql, (name, parent_id), fetchone=True, commit=True)
        return res['id'] if res else None

    @classmethod
    def get_all(cls):
        sql = "SELECT id, name, parent_id FROM categories ORDER BY name ASC;"
        return execute_query(sql, fetchall=True) or []

    @classmethod
    def get_by_id(cls, category_id):
        sql = "SELECT id, name, parent_id FROM categories WHERE id = %s;"
        return execute_query(sql, (category_id,), fetchone=True)

    @classmethod
    def get_tree(cls):
        """
        Builds a nested category/subcategory tree structure for navigation sidebars.
        """
        all_categories = cls.get_all()
        parents = [c for c in all_categories if c['parent_id'] is None]
        
        for parent in parents:
            parent['subcategories'] = [
                c for c in all_categories if c['parent_id'] == parent['id']
            ]
        return parents


class Brand:
    """
    Model for managing Brands using Raw SQL.
    """
    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name

    @classmethod
    def create(cls, name):
        sql = "INSERT INTO brands (name) VALUES (%s) RETURNING id;"
        res = execute_query(sql, (name,), fetchone=True, commit=True)
        return res['id'] if res else None

    @classmethod
    def get_all(cls):
        sql = "SELECT id, name FROM brands ORDER BY name ASC;"
        return execute_query(sql, fetchall=True) or []

    @classmethod
    def get_by_id(cls, brand_id):
        sql = "SELECT id, name FROM brands WHERE id = %s;"
        return execute_query(sql, (brand_id,), fetchone=True)


class Product:
    """
    Model for managing Inventory Products using Raw SQL.
    """
    def __init__(self, id=None, sku=None, name=None, brand_id=None, category_id=None,
                 quantity=0, reorder_level=5, cost_price=0.0, retail_price=0.0,
                 description="", image_url="default_product.png"):
        self.id = id
        self.sku = sku
        self.name = name
        self.brand_id = brand_id
        self.category_id = category_id
        self.quantity = quantity
        self.reorder_level = reorder_level
        self.cost_price = cost_price
        self.retail_price = retail_price
        self.description = description
        self.image_url = image_url

    @classmethod
    def create(cls, sku, name, brand_id, category_id, quantity, cost_price, retail_price, reorder_level=5, description="", image_url="default_product.png"):
        sql = """
            INSERT INTO products (sku, name, brand_id, category_id, quantity, reorder_level, cost_price, retail_price, description, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        res = execute_query(
            sql, 
            (sku, name, brand_id, category_id, quantity, reorder_level, cost_price, retail_price, description, image_url),
            fetchone=True,
            commit=True
        )
        return res['id'] if res else None

    @classmethod
    def get_all(cls, category_ids=None, brand_ids=None, out_of_stock_only=False, search=None, limit=20, offset=0):
        """
        Fetches products with join details, search filters, and database pagination.
        """
        conditions = []
        params = []

        if category_ids:
            conditions.append("p.category_id = ANY(%s)")
            params.append(category_ids)

        if brand_ids:
            conditions.append("p.brand_id = ANY(%s)")
            params.append(brand_ids)

        if out_of_stock_only:
            conditions.append("p.quantity = 0")

        if search:
            conditions.append("(p.name ILIKE %s OR p.sku ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT p.id, p.sku, p.name, p.quantity, p.reorder_level, 
                   p.cost_price, p.retail_price, p.description, p.image_url,
                   b.name as brand_name, c.name as category_name
            FROM products p
            JOIN brands b ON p.brand_id = b.id
            JOIN categories c ON p.category_id = c.id
            {where_clause}
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])
        return execute_query(sql, tuple(params), fetchall=True) or []

    @classmethod
    def get_by_id(cls, product_id):
        sql = """
            SELECT p.*, b.name as brand_name, c.name as category_name
            FROM products p
            JOIN brands b ON p.brand_id = b.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = %s;
        """
        return execute_query(sql, (product_id,), fetchone=True)

    @classmethod
    def update_quantity(cls, product_id, new_quantity):
        sql = "UPDATE products SET quantity = %s WHERE id = %s;"
        return execute_query(sql, (new_quantity, product_id), commit=True)

    @classmethod
    def delete(cls, product_id):
        sql = "DELETE FROM products WHERE id = %s;"
        return execute_query(sql, (product_id,), commit=True)