import math

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.db import execute_query


store_bp = Blueprint('store', __name__, url_prefix='/store')


@store_bp.route('/')
def store_catalog():
    """Public catalog that only shows sellable product information."""
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = 9
    category_ids = request.args.getlist('category_id', type=int)
    sort_by = request.args.get('sort_by', 'name_asc')

    conditions = []
    params = []
    if category_ids:
        placeholders = ', '.join(['%s'] * len(category_ids))
        category_rows = execute_query(
            f"SELECT id FROM categories WHERE id IN ({placeholders}) OR parent_id IN ({placeholders});",
            tuple(category_ids + category_ids),
            fetchall=True,
        ) or []
        matching_ids = [category['id'] for category in category_rows] or category_ids
        placeholders = ', '.join(['%s'] * len(matching_ids))
        conditions.append(f'p.category_id IN ({placeholders})')
        params.extend(matching_ids)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ''
    sort_mapping = {
        'price_asc': 'p.retail_price ASC',
        'price_desc': 'p.retail_price DESC',
        'name_asc': 'p.name ASC',
        'name_desc': 'p.name DESC',
        'newest': 'p.id DESC',
    }
    order_by = sort_mapping.get(sort_by, 'p.name ASC')

    total_result = execute_query(
        f'SELECT COUNT(*) AS total FROM products p {where_sql};',
        tuple(params),
        fetchone=True,
    )
    total_items = total_result['total'] if total_result else 0
    total_pages = max(math.ceil(total_items / per_page), 1)
    page = min(page, total_pages)

    products = execute_query(
        f"""
        SELECT p.id, p.sku, p.name, p.description, p.image_url, p.quantity,
               p.retail_price, b.name AS brand_name, c.name AS category_name
        FROM products p
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN categories c ON c.id = p.category_id
        {where_sql}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s;
        """,
        tuple(params + [per_page, (page - 1) * per_page]),
        fetchall=True,
    ) or []

    categories = execute_query(
        'SELECT id, name, parent_id FROM categories ORDER BY parent_id ASC NULLS FIRST, name ASC;',
        fetchall=True,
    ) or []
    parent_categories = [category for category in categories if category['parent_id'] is None]
    subcategories = [category for category in categories if category['parent_id'] is not None]

    return render_template(
        'store/index.html',
        products=products,
        parent_categories=parent_categories,
        subcategories=subcategories,
        selected_category_ids=category_ids,
        sort_by=sort_by,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
    )


@store_bp.route('/product/<int:product_id>')
def store_product_detail(product_id):
    """Public product page without internal cost-price information."""
    product = execute_query(
        """
        SELECT p.id, p.sku, p.name, p.description, p.image_url, p.quantity,
               p.retail_price, b.name AS brand_name, c.name AS category_name
        FROM products p
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.id = %s;
        """,
        (product_id,),
        fetchone=True,
    )
    if not product:
        abort(404)
    return render_template('store/product_detail.html', product=product)


@store_bp.route('/product/<int:product_id>/order', methods=['POST'])
def confirm_order(product_id):
    """Confirm one simple store order and deduct the purchased stock safely."""
    customer_name = request.form.get('customer_name', '').strip()
    quantity = request.form.get('quantity', type=int)

    if not customer_name or not quantity or quantity < 1:
        flash('Enter your name and a quantity of at least 1.', 'warning')
        return redirect(url_for('store.store_product_detail', product_id=product_id))

    order = execute_query(
        """
        WITH updated_product AS (
            UPDATE products
            SET quantity = quantity - %s
            WHERE id = %s AND quantity >= %s
            RETURNING id, retail_price
        )
        INSERT INTO orders (product_id, customer_name, quantity, unit_price, total_price, status)
        SELECT id, %s, %s, retail_price, retail_price * %s, 'CONFIRMED'
        FROM updated_product
        RETURNING id;
        """,
        (quantity, product_id, quantity, customer_name, quantity, quantity),
        fetchone=True,
        commit=True,
    )

    if not order:
        flash('This product does not have enough stock for that order.', 'warning')
        return redirect(url_for('store.store_product_detail', product_id=product_id))

    flash(f'Order #{order["id"]} confirmed. Inventory has been updated.', 'success')
    return redirect(url_for('store.store_product_detail', product_id=product_id))
