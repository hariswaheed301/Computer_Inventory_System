import os
import math
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.db import execute_query
from app.models.users import role_required

stock_bp = Blueprint('stock', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------- DASHBOARD WITH CHARTS -----------------
@stock_bp.route('/')
@stock_bp.route('/dashboard')
@login_required
def dashboard():

    # Dashboard Statistics
    stats = execute_query("""
        SELECT
            COUNT(*) AS total_products,

            COALESCE(SUM(
                CASE
                    WHEN quantity > 0 THEN 1
                    ELSE 0
                END
            ),0) AS in_stock,

            COALESCE(SUM(
                CASE
                    WHEN quantity = 0 THEN 1
                    ELSE 0
                END
            ),0) AS out_of_stock,

            COALESCE(SUM(
                CASE
                    WHEN quantity > 0
                    AND quantity < 5
                    THEN 1
                    ELSE 0
                END
            ),0) AS low_stock

        FROM products;
    """, fetchone=True)


    # Total Categories
    category_result = execute_query("""
        SELECT COUNT(*) AS total
        FROM categories;
    """, fetchone=True)


    # Total Brands
    brand_result = execute_query("""
        SELECT COUNT(*) AS total
        FROM brands;
    """, fetchone=True)


    # Top 5 Products
    chart_data = execute_query("""
        SELECT
            name,
            quantity
        FROM products
        ORDER BY quantity DESC
        LIMIT 5;
    """, fetchall=True) or []


    # Low Stock Table
    low_stock_items = execute_query("""
        SELECT
            p.id,
            p.name,
            p.sku,
            p.quantity,
            p.reorder_level,
            c.name AS category_name

        FROM products p

        LEFT JOIN categories c
            ON p.category_id=c.id

        WHERE p.quantity > 0 AND p.quantity < 5

        ORDER BY
            p.quantity ASC,
            p.name ASC

        LIMIT 5;
    """, fetchall=True) or []


    return render_template(

        "dashboard/dashboard.html",

        total_skus=stats["total_products"],

        in_stock=stats["in_stock"],

        low_stock=stats["low_stock"],

        out_of_stock=stats["out_of_stock"],

        total_categories=category_result["total"],

        total_brands=brand_result["total"],

        chart_data=chart_data,

        low_stock_items=low_stock_items

    )

# ----------------- INVENTORY CATALOG & LISTING -----------------
@stock_bp.route('/inventory')
@login_required
def inventory():

    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    # ---------------- SEARCH ----------------
    search = request.args.get('search', '').strip()

    # ---------------- SORT ----------------
    sort = request.args.get('sort', 'newest')

    sort_options = {
        "newest": "p.id DESC",
        "oldest": "p.id ASC",
        "name": "p.name ASC",
        "quantity": "p.quantity DESC",
        "price": "p.retail_price DESC"
    }

    order_by = sort_options.get(sort, "p.id DESC")

    # ---------------- STOCK FILTER ----------------
    stock_status = request.args.get('stock_status')

    # ---------------- CATEGORY FILTER ----------------
    raw_cat_ids = request.args.getlist('category_id')

    category_ids = []

    for cid in raw_cat_ids:
        try:
            category_ids.append(int(cid))
        except:
            pass

    # ---------------- BRAND FILTER ----------------
    raw_brand_ids = request.args.getlist('brand_id')

    brand_ids = []

    for bid in raw_brand_ids:
        try:
            brand_ids.append(int(bid))
        except:
            pass

    # ---------------- BUILD CATEGORY TREE ----------------

    target_categories = set(category_ids)

    if category_ids:

        placeholders = ",".join(["%s"] * len(category_ids))

        children = execute_query(
            f"""
            SELECT id
            FROM categories
            WHERE parent_id IN ({placeholders});
            """,
            tuple(category_ids),
            fetchall=True
        ) or []

        for child in children:
            target_categories.add(child["id"])

    target_categories = list(target_categories)

    # ---------------- WHERE CLAUSE ----------------

    where = []

    params = []

    # Search
    if search:
        where.append("(p.name ILIKE %s OR p.sku ILIKE %s)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    # Category
    if target_categories:

        placeholders = ",".join(["%s"] * len(target_categories))

        where.append(
            f"p.category_id IN ({placeholders})"
        )

        params.extend(target_categories)

    # Brand
    if brand_ids:

        placeholders = ",".join(["%s"] * len(brand_ids))

        where.append(
            f"p.brand_id IN ({placeholders})"
        )

        params.extend(brand_ids)

    # Stock
    if stock_status == "low_stock":

        where.append("p.quantity > 0 AND p.quantity < 5")

    elif stock_status == "out_of_stock":

        where.append(
            "p.quantity=0"
        )

    where_sql = ""

    if where:
        where_sql = "WHERE " + " AND ".join(where)

    # ---------------- TOTAL COUNT ----------------

    total_query = f"""
        SELECT
            COUNT(*) AS total
        FROM products p
        {where_sql};
    """

    total = execute_query(
        total_query,
        tuple(params) if params else None,
        fetchone=True
    )

    total_items = total["total"] if total else 0

    total_pages = math.ceil(total_items / per_page)

    if total_pages == 0:
        total_pages = 1

    # ---------------- PRODUCT QUERY ----------------

    product_query = f"""

        SELECT

            p.*,

            COALESCE(
                p.image_url,
                'default_product.png'
            ) AS image_url,

            b.name AS brand_name,

            c.name AS subcategory_name,

            COALESCE(parent.name,c.name)
            AS category_name

        FROM products p

        LEFT JOIN brands b
            ON p.brand_id=b.id

        LEFT JOIN categories c
            ON p.category_id=c.id

        LEFT JOIN categories parent
            ON c.parent_id=parent.id

        {where_sql}

        ORDER BY {order_by}

        LIMIT %s
        OFFSET %s;

    """

    product_params = list(params)

    product_params.extend([
        per_page,
        offset
    ])

    products = execute_query(
        product_query,
        tuple(product_params),
        fetchall=True
    ) or []

    # ---------------- CATEGORY TREE ----------------

    raw_categories = execute_query("""
        SELECT
            id,
            name,
            parent_id
        FROM categories
        ORDER BY
            parent_id ASC NULLS FIRST,
            name ASC;
    """, fetchall=True) or []

    parent_categories = []

    category_dict = {}

    for cat in raw_categories:

        obj = {
            "id": cat["id"],
            "name": cat["name"],
            "parent_id": cat["parent_id"],
            "subcategories": []
        }

        category_dict[cat["id"]] = obj

        if cat["parent_id"] is None:
            parent_categories.append(obj)

    for cat in raw_categories:

        if cat["parent_id"]:

            if cat["parent_id"] in category_dict:

                category_dict[
                    cat["parent_id"]
                ]["subcategories"].append(
                    category_dict[cat["id"]]
                )

    # ---------------- BRANDS ----------------

    brands = execute_query("""
        SELECT
            id,
            name
        FROM brands
        ORDER BY name;
    """, fetchall=True) or []

    return render_template(

        "inventory/inventory_list.html",

        products=products,

        parent_categories=parent_categories,

        brands=brands,

        selected_categories=category_ids,

        selected_brands=brand_ids,

        stock_status=stock_status,

        search=search,

        sort=sort,

        page=page,

        total_pages=total_pages,

        total_items=total_items

    )


# ----------------- ADD PRODUCT PAGE -----------------
@stock_bp.route('/product/add', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def add_product():
    if request.method == 'POST':
        sku = request.form.get('sku', '').strip()
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        brand_id = int(request.form.get('brand_id'))
        category_id = int(request.form.get('category_id'))
        quantity = int(request.form.get('quantity', 0))
        reorder_level = int(request.form.get('reorder_level', 5))
        cost_price = float(request.form.get('cost_price', 0.0))
        retail_price = float(request.form.get('retail_price', 0.0))

        filename = 'default_product.png'
        file = request.files.get('image')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"{sku}_{file.filename}")
            upload_path = os.path.join(current_app.root_path, 'static/uploads/products', filename)
            file.save(upload_path)

        query = """
            INSERT INTO products (sku, name, description, image_url, brand_id, category_id, quantity, reorder_level, cost_price, retail_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        execute_query(query, (sku, name, description, filename, brand_id, category_id, quantity, reorder_level, cost_price, retail_price), commit=True)
        flash('New Product added successfully!', 'success')
        return redirect(url_for('stock.inventory'))

    categories = execute_query("SELECT id, name, parent_id FROM categories ORDER BY parent_id ASC NULLS FIRST, name ASC;", fetchall=True) or []
    brands = execute_query("SELECT id, name FROM brands ORDER BY name ASC;", fetchall=True) or []
    return render_template('inventory/add_product.html', categories=categories, brands=brands)


# ----------------- EDIT PRODUCT PAGE -----------------
@stock_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def edit_product(product_id):
    product = execute_query("SELECT * FROM products WHERE id = %s;", (product_id,), fetchone=True)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('stock.inventory'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        brand_id = int(request.form.get('brand_id'))
        category_id = int(request.form.get('category_id'))
        quantity = int(request.form.get('quantity'))
        reorder_level = int(request.form.get('reorder_level'))
        cost_price = float(request.form.get('cost_price'))
        retail_price = float(request.form.get('retail_price'))

        filename = product['image_url']
        file = request.files.get('image')
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"{product['sku']}_{file.filename}")
            upload_path = os.path.join(current_app.root_path, 'static/uploads/products', filename)
            file.save(upload_path)

        update_query = """
            UPDATE products 
            SET name=%s, description=%s, image_url=%s, brand_id=%s, category_id=%s, quantity=%s, reorder_level=%s, cost_price=%s, retail_price=%s
            WHERE id=%s;
        """
        execute_query(update_query, (name, description, filename, brand_id, category_id, quantity, reorder_level, cost_price, retail_price, product_id), commit=True)
        flash('Product updated successfully!', 'success')
        return redirect(url_for('stock.product_detail', product_id=product_id))

    categories = execute_query("SELECT id, name, parent_id FROM categories ORDER BY parent_id ASC NULLS FIRST, name ASC;", fetchall=True) or []
    brands = execute_query("SELECT id, name FROM brands ORDER BY name ASC;", fetchall=True) or []
    return render_template('inventory/edit_product.html', product=product, categories=categories, brands=brands)


# ----------------- E-COMMERCE PRODUCT DETAIL PAGE -----------------
@stock_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    query = """
        SELECT p.*, b.name AS brand_name, c.name AS category_name
        FROM products p
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id = %s;
    """
    product = execute_query(query, (product_id,), fetchone=True)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('stock.inventory'))

    return render_template('inventory/product_detail.html', product=product)


# ----------------- AUTO-GENERATE SKU -----------------
def derive_category_code(name):
    """Derive a 2-letter category code from name (e.g., Keyboard -> KB, Monitor -> MN, Mouse -> MS)."""
    words = name.split()
    code = ''.join([w[0] for w in words if w])[:2].upper()
    if len(code) < 2:
        code = name[:2].upper()
    return code

def derive_subcategory_code(name):
    """Derive a subcategory code (up to 4 letters) from name."""
    words = name.split()
    code = ''.join([w[0] for w in words if w])[:4].upper()
    if len(code) < 2:
        code = name[:4].upper()
    return code

def get_next_sku_sequence(prefix):
    """Get the next sequence number for a given SKU prefix."""
    result = execute_query("""
        SELECT MAX(CAST(SUBSTRING(sku FROM LENGTH(%s) + 1) AS INTEGER)) AS max_seq
        FROM products
        WHERE sku LIKE %s;
    """, (prefix, f"{prefix}%"), fetchone=True)
    return (result['max_seq'] or 0) + 1

@stock_bp.route('/api/generate-sku')
@login_required
def generate_sku():
    """Generate an SKU based on selected subcategory or category."""
    subcategory_id = request.args.get('subcategory_id', type=int)
    category_id = request.args.get('category_id', type=int)

    if subcategory_id:
        # Has subcategory: use pattern {CATEGORY_CODE}-{SUBCATEGORY_CODE}-{SEQ}
        subcat = execute_query("""
            SELECT c.id, c.name, c.parent_id, p.name AS parent_name
            FROM categories c
            LEFT JOIN categories p ON c.parent_id = p.id
            WHERE c.id = %s;
        """, (subcategory_id,), fetchone=True)

        if not subcat or not subcat['parent_id']:
            return jsonify({'success': False, 'error': 'Invalid subcategory'}), 400

        parent_code = derive_category_code(subcat['parent_name'])
        sub_code = derive_subcategory_code(subcat['name'])
        prefix = f"{parent_code}-{sub_code}-"
        next_seq = get_next_sku_sequence(prefix)
        sku = f"{parent_code}-{sub_code}-{next_seq:03d}"

    elif category_id:
        # No subcategory: use pattern {CATEGORY_CODE}-XXX-{SEQ}
        cat = execute_query("""
            SELECT id, name FROM categories WHERE id = %s;
        """, (category_id,), fetchone=True)

        if not cat:
            return jsonify({'success': False, 'error': 'Invalid category'}), 400

        cat_code = derive_category_code(cat['name'])
        prefix = f"{cat_code}-XXX-"
        next_seq = get_next_sku_sequence(prefix)
        sku = f"{cat_code}-XXX-{next_seq:03d}"

    else:
        return jsonify({'success': False, 'error': 'Category or subcategory ID required'}), 400

    return jsonify({'success': True, 'sku': sku})


# ----------------- ADMIN STOCK / PRODUCT REMOVAL -----------------
@stock_bp.route('/product/<int:product_id>/remove-units', methods=['POST'])
@login_required
@role_required('ADMIN')
def remove_units(product_id):
    units = request.form.get('units', type=int)
    if not units or units < 1:
        flash('Enter at least one unit to remove.', 'warning')
        return redirect(url_for('stock.product_detail', product_id=product_id))

    updated = execute_query(
        """
        UPDATE products
        SET quantity = quantity - %s
        WHERE id = %s AND quantity >= %s
        RETURNING quantity;
        """,
        (units, product_id, units),
        fetchone=True,
        commit=True,
    )
    if not updated:
        flash('Unable to remove that many units. Check the available stock.', 'warning')
    else:
        flash(f'{units} unit(s) removed. Remaining stock: {updated["quantity"]}.', 'success')
    return redirect(url_for('stock.product_detail', product_id=product_id))


@stock_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
@role_required('ADMIN')
def delete_product(product_id):
    # Keep confirmed order history valid by preventing deletion of ordered items.
    deleted = execute_query(
        """
        DELETE FROM products
        WHERE id = %s
          AND NOT EXISTS (SELECT 1 FROM orders WHERE product_id = %s)
        RETURNING id;
        """,
        (product_id, product_id),
        fetchone=True,
        commit=True,
    )
    if deleted:
        flash('Product deleted permanently.', 'success')
        return redirect(url_for('stock.inventory'))

    flash('Product could not be deleted. Products with confirmed orders are kept for order history.', 'warning')
    return redirect(url_for('stock.product_detail', product_id=product_id))
