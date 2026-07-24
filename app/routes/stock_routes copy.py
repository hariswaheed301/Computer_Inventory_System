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
    stats = execute_query("""
        SELECT 
            COUNT(*) AS total_skus,
            COALESCE(SUM(CASE WHEN quantity = 0 THEN 1 ELSE 0 END), 0) AS out_of_stock,
            COALESCE(SUM(CASE WHEN quantity > 0 AND quantity <= reorder_level THEN 1 ELSE 0 END), 0) AS low_stock
        FROM products;
    """, fetchone=True)

    # Fetch Top 5 Products by Quantity for Chart.js
    chart_data = execute_query("""
        SELECT name, quantity FROM products ORDER BY quantity DESC LIMIT 5;
    """, fetchall=True) or []

    # Fetch low stock items for dashboard quick view table
    low_stock_items = execute_query("""
        SELECT p.id, p.name, p.sku, p.quantity, p.reorder_level, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.quantity <= p.reorder_level
        ORDER BY p.quantity ASC
        LIMIT 5;
    """, fetchall=True) or []

    return render_template(
        'dashboard/dashboard.html', 
        total_skus=stats['total_skus'] if stats else 0,
        out_of_stock=stats['out_of_stock'] if stats else 0,
        low_stock=stats['low_stock'] if stats else 0,
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

    # Get multiple selected categories from query parameters
    raw_cat_ids = request.args.getlist('category_id')
    category_ids = []
    for cid in raw_cat_ids:
        try:
            category_ids.append(int(cid))
        except (ValueError, TypeError):
            continue

    stock_status = request.args.get('stock_status', type=str)

    # Resolve selected parent categories into parent + child category IDs
    all_target_category_ids = set(category_ids)
    if category_ids:
        placeholders = ', '.join(['%s'] * len(category_ids))
        child_cats = execute_query(
            f"SELECT id FROM categories WHERE parent_id IN ({placeholders});",
            tuple(category_ids),
            fetchall=True
        ) or []
        for child in child_cats:
            all_target_category_ids.add(child['id'])

    target_cat_list = list(all_target_category_ids)

    # Build WHERE conditions
    where_clauses = []
    params = []

    if stock_status == 'out_of_stock':
        where_clauses.append("p.quantity = 0")
    elif stock_status == 'low_stock':
        where_clauses.append("p.quantity > 0 AND p.quantity <= p.reorder_level")

    if target_cat_list:
        placeholders = ', '.join(['%s'] * len(target_cat_list))
        where_clauses.append(f"p.category_id IN ({placeholders})")
        params.extend(target_cat_list)

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Total Count for Pagination
    count_query = f"SELECT COUNT(*) AS total FROM products p {where_sql};"
    total_result = execute_query(count_query, tuple(params) if params else None, fetchone=True)
    total_items = total_result['total'] if total_result else 0
    total_pages = math.ceil(total_items / per_page) or 1

    # Fetch Paginated Products
    query = f"""
        SELECT 
            p.*, 
            COALESCE(p.image_url, 'default_product.png') AS image_url,
            b.name AS brand_name, 
            c.name AS subcategory_name,
            COALESCE(parent_c.name, c.name) AS category_name
        FROM products p
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN categories parent_c ON c.parent_id = parent_c.id
        {where_sql}
        ORDER BY p.id DESC
        LIMIT %s OFFSET %s;
    """
    query_params = list(params)
    query_params.extend([per_page, offset])

    products = execute_query(query, tuple(query_params), fetchall=True) or []

    # Fetch Categories Hierarchically
    raw_categories = execute_query("""
        SELECT id, name, parent_id 
        FROM categories 
        ORDER BY parent_id ASC NULLS FIRST, name ASC;
    """, fetchall=True) or []

    # Organize into Parent-Child Category structure
    parent_categories = []
    category_dict = {}

    for cat in raw_categories:
        cat_data = {'id': cat['id'], 'name': cat['name'], 'parent_id': cat['parent_id'], 'subcategories': []}
        category_dict[cat['id']] = cat_data
        if cat['parent_id'] is None:
            parent_categories.append(cat_data)
        elif cat['parent_id'] in category_dict:
            category_dict[cat['parent_id']]['subcategories'].append(cat_data)

    return render_template(
        'inventory/inventory_list.html',
        products=products,
        parent_categories=parent_categories,
        selected_categories=category_ids,
        stock_status=stock_status,
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

    categories = execute_query("SELECT id, name FROM categories ORDER BY name ASC;", fetchall=True) or []
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

    categories = execute_query("SELECT id, name FROM categories ORDER BY name ASC;", fetchall=True) or []
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