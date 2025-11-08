import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, Response, redirect
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect, generate_csrf  # Add generate_csrf here
from datetime import datetime, timedelta
import mysql.connector
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Set a secret key for security (required for CSRF and session)
app.config['SECRET_KEY'] = os.urandom(24).hex()  # Generates a random secure key

# Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '#yourpassword' # Replace YOUR_PASSWORD_HERE with your actual password before running locally
app.config['MYSQL_DB'] = 'restaurant'
app.config['UPLOAD_FOLDER'] = 'static'  # Folder to save uploaded images
app.config['TAX_RATE'] = 0.1  # Configurable tax rate
app.config['OPERATIONAL_EXPENSES'] = {
    "rent": 5000,
    "utilities": 2000,
    "salaries": 15000,
    "marketing": 1000
}  # Configurable operational expenses
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Initialize CSRF protection
csrf = CSRFProtect(app)

mysql = MySQL(app)

# Simulated database of menu items (replace with actual database logic if needed)
MENU_ITEMS = [
    ('Coffee', 50, 'assets/coffee.jpg'),
    ('Tea', 30, 'assets/tea.jpg'),
    ('Sandwich', 80, 'assets/sandwich.jpg')
]

# Simulated orders storage (replace with a database in production)
ORDERS = {}

# Utility function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Utility function to sanitize JSON response (handles Infinity and NaN)
def sanitize_json(data):
    if isinstance(data, dict):
        return {k: sanitize_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json(item) for item in data]
    elif isinstance(data, float) and (data == float('inf') or data == float('-inf') or data != data):  # Check for Infinity or NaN
        return "N/A"
    return data

# Generate order number in format YYYYMMDD-NNN with transaction to prevent race condition
def generate_order_number():
    today = datetime.now()
    today_str = today.strftime('%Y%m%d')
    start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    cur = mysql.connection.cursor()
    try:
        cur.execute("LOCK TABLES orders WRITE")
        cur.execute("SELECT COUNT(*) FROM orders WHERE created_at >= %s AND created_at < %s",
                    (start_of_day, end_of_day))
        count = cur.fetchone()[0] + 1
        order_number = f"{today_str}-{count:03d}"
        cur.execute("INSERT INTO orders (order_number, created_at, status) VALUES (%s, %s, %s)",
                    (order_number, today, 'pending'))
        mysql.connection.commit()
        return order_number
    except Exception as e:
        logger.error(f"Error generating order number: {str(e)}")
        raise
    finally:
        cur.execute("UNLOCK TABLES")
        cur.close()

# Menu Board Page
@app.route('/')
def home():
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id, name FROM categories")
        categories = cur.fetchall()
        
        cur.execute("""
            SELECT mi.id, mi.name, mi.price, mi.quantity, c.name as category_name, mi.image,
                   (SELECT SUM(oi.quantity) FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE oi.item_name = mi.name AND o.status = 'completed') as total_sold
            FROM menu_items mi
            JOIN categories c ON mi.category_id = c.id
        """)
        menu_items = cur.fetchall()
        
        menu_data = [{
            'id': item[0],
            'name': item[1],
            'price': float(item[2]),
            'quantity': int(item[3]),
            'category_name': item[4],
            'image': item[5],
            'total_sold': int(item[6] or 0)
        } for item in menu_items]
        
        # Generate CSRF token
        csrf_token = generate_csrf()
        
        return render_template('MenuBoard.html', menu=menu_data, categories=categories, csrf_token=csrf_token)
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500
    finally:
        cur.close()

# Fetch items by category
@app.route('/items-by-category/<category_name>')
def items_by_category(category_name):
    if not category_name:
        return jsonify(sanitize_json({"error": "Category name is required"})), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT mi.id, mi.name, mi.price, mi.quantity, c.name as category_name, mi.image,
                   (SELECT SUM(oi.quantity) FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE oi.item_name = mi.name AND o.status = 'completed') as total_sold
            FROM menu_items mi
            JOIN categories c ON mi.category_id = c.id
            WHERE c.name = %s
        """, (category_name,))
        menu_items = cur.fetchall()
        return jsonify(sanitize_json([{
            "id": item[0],
            "name": item[1],
            "price": float(item[2]),
            "quantity": int(item[3]),
            "category_name": item[4],
            "image": item[5],
            "total_sold": int(item[6] or 0)
        } for item in menu_items]))
    except Exception as e:
        logger.error(f"Error in items_by_category route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500
    finally:
        cur.close()

# Add Category
@app.route('/add-category', methods=['POST'])
def add_category():
    try:
        data = request.json
        category_name = data.get('name')
        if not category_name:
            return jsonify(sanitize_json({"error": "Category name is required"})), 400

        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT name FROM categories WHERE name = %s", (category_name,))
            existing_category = cur.fetchone()
            if existing_category:
                return jsonify(sanitize_json({"error": "Category already exists"})), 400

            cur.execute("INSERT INTO categories (name) VALUES (%s)", (category_name,))
            mysql.connection.commit()
            return jsonify(sanitize_json({"message": f"Category '{category_name}' added successfully!"}))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in add_category route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

# Add Item
@app.route('/add-item', methods=['POST'])
def add_item():
    try:
        data = request.json
        name = data.get('name')
        price = data.get('price')
        quantity = data.get('quantity')
        category_id = data.get('category_id')
        image = data.get('image', 'default.png')

        if not name:
            return jsonify(sanitize_json({"error": "Item name is required"})), 400
        try:
            price = float(price)
            if price <= 0:
                return jsonify(sanitize_json({"error": "Price must be positive"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Price must be a valid number"})), 400
        try:
            quantity = int(quantity)
            if quantity < 0:
                return jsonify(sanitize_json({"error": "Quantity cannot be negative"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Quantity must be a valid integer"})), 400
        try:
            category_id = int(category_id)
            if category_id <= 0:
                return jsonify(sanitize_json({"error": "Invalid category ID"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Category ID must be a valid integer"})), 400

        with mysql.connection.cursor() as cur:
            # Check if category exists
            cur.execute("SELECT id FROM categories WHERE id = %s", (category_id,))
            if not cur.fetchone():
                return jsonify(sanitize_json({"error": "Category ID does not exist"})), 400

            cur.execute("SELECT name FROM menu_items WHERE name = %s", (name,))
            existing_item = cur.fetchone()

            if existing_item:
                cur.execute("UPDATE menu_items SET price = %s, category_id = %s, quantity = %s WHERE name = %s",
                            (price, category_id, quantity, name))
                message = f"Item '{name}' updated successfully!"
            else:
                cur.execute("INSERT INTO menu_items (name, price, quantity, category_id, image) VALUES (%s, %s, %s, %s, %s)",
                            (name, price, quantity, category_id, image))
                message = f"New item '{name}' added successfully!"

            mysql.connection.commit()
            return jsonify(sanitize_json({"message": message}))
    except Exception as e:
        logger.error(f"Error in add_item route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500
    
@app.route('/delete-item', methods=['POST'])
def delete_item():
    try:
        data = request.json
        item_id = data.get('id')
        try:
            item_id = int(item_id)
            if item_id <= 0:
                return jsonify(sanitize_json({"error": "Invalid item ID"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Item ID must be a valid integer"})), 400

        cur = mysql.connection.cursor()
        try:
            cur.execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
            if cur.rowcount == 0:
                return jsonify(sanitize_json({"error": "Item not found"})), 404
            
            cur.execute("SELECT MAX(id) FROM menu_items")
            max_id = cur.fetchone()[0]
            if max_id is None:
                cur.execute("ALTER TABLE menu_items AUTO_INCREMENT = 1")
            else:
                cur.execute("ALTER TABLE menu_items AUTO_INCREMENT = %s", (max_id + 1,))
            
            mysql.connection.commit()
            return jsonify(sanitize_json({"message": "Item deleted successfully!"}))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in delete_item route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/inventory')
def inventory():
    cur = mysql.connection.cursor()
    try:
        # Fetch all inventory items with additional transaction details
        cur.execute("""
            SELECT name, quantity, cost_per_unit, image,
                   (SELECT SUM(quantity) FROM inventory_transactions WHERE item_name = inventory_items.name AND transaction_type = 'stock_in') as total_stock_in,
                   (SELECT SUM(quantity) FROM inventory_transactions WHERE item_name = inventory_items.name AND transaction_type = 'stock_out') as total_stock_out
            FROM inventory_items
        """)
        inventory_items = cur.fetchall()
        
        # Fetch low stock items
        cur.execute("SELECT name, quantity, image FROM inventory_items WHERE quantity <= 5")
        low_stock_items = cur.fetchall()
        
        # Process inventory data
        inventory_data = [{
            'name': item[0],
            'quantity': float(item[1]),
            'cost_per_unit': float(item[2]),
            'image': item[3],
            'total_stock_in': float(item[4] or 0),
            'total_stock_out': float(item[5] or 0),
            'stock_status': 'Low' if float(item[1]) <= 5 else 'Sufficient'
        } for item in inventory_items]
        
        # Generate CSRF token
        csrf_token = generate_csrf()
        
        return render_template('Inventory.html', 
                             inventory=inventory_data, 
                             low_stock_items=low_stock_items, 
                             active_tab='stock-in',
                             csrf_token=csrf_token)  # Pass CSRF token to template
    except Exception as e:
        logger.error(f"Error in inventory route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500
    finally:
        cur.close()

@app.route('/add-inventory', methods=['POST'])
def add_inventory():
    try:
        data = request.json
        name = data.get('name')
        quantity = data.get('quantity')
        cost = data.get('cost')
        seller = data.get('seller', 'N/A')
        image = data.get('image', 'default.png')

        if not name:
            return jsonify(sanitize_json({"error": "Item name is required"})), 400
        try:
            quantity = float(quantity)
            if quantity <= 0:
                return jsonify(sanitize_json({"error": "Quantity must be positive"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Quantity must be a valid number"})), 400
        try:
            cost = float(cost)
            if cost <= 0:
                return jsonify(sanitize_json({"error": "Cost must be positive"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Cost must be a valid number"})), 400

        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT quantity, image FROM inventory_items WHERE name = %s", (name,))
            existing = cur.fetchone()
            if existing:
                new_quantity = float(existing[0]) + quantity
                current_image = existing[1] if existing[1] else 'default.png'
                cur.execute("UPDATE inventory_items SET quantity = %s, cost_per_unit = %s, image = %s WHERE name = %s",
                            (new_quantity, cost, current_image, name))
            else:
                cur.execute("INSERT INTO inventory_items (name, quantity, cost_per_unit, image) VALUES (%s, %s, %s, %s)",
                            (name, quantity, cost, image))
            cur.execute("INSERT INTO inventory_transactions (item_name, transaction_type, quantity, cost_per_unit, transaction_date, seller) VALUES (%s, %s, %s, %s, %s, %s)",
                        (name, 'stock_in', quantity, cost, datetime.now(), seller))
            mysql.connection.commit()
            return jsonify(sanitize_json({"message": "Inventory updated successfully!"}))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in add_inventory route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/stockout')
def stockout():
    cur = mysql.connection.cursor()
    try:
        # Fetch all inventory items with transaction details
        cur.execute("""
            SELECT name, quantity, cost_per_unit, image,
                   (SELECT SUM(quantity) FROM inventory_transactions WHERE item_name = inventory_items.name AND transaction_type = 'stock_in') as total_stock_in,
                   (SELECT SUM(quantity) FROM inventory_transactions WHERE item_name = inventory_items.name AND transaction_type = 'stock_out') as total_stock_out
            FROM inventory_items
        """)
        inventory_items = cur.fetchall()
        
        # Fetch low stock items
        cur.execute("SELECT name, quantity, image FROM inventory_items WHERE quantity <= 5")
        low_stock_items = cur.fetchall()
        
        # Process inventory data
        inventory_data = [{
            'name': item[0],
            'quantity': float(item[1]),
            'cost_per_unit': float(item[2]),
            'image': item[3],
            'total_stock_in': float(item[4] or 0),
            'total_stock_out': float(item[5] or 0),
            'stock_status': 'Low' if float(item[1]) <= 5 else 'Sufficient'
        } for item in inventory_items]
        
        # Generate CSRF token
        csrf_token = generate_csrf()
        
        return render_template('Inventory.html', 
                             inventory=inventory_data, 
                             low_stock_items=low_stock_items, 
                             active_tab='stock-out',
                             csrf_token=csrf_token)  # Pass CSRF token to template
    except Exception as e:
        logger.error(f"Error in stockout route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500
    finally:
        cur.close()

@app.route('/remove-inventory', methods=['POST'])
def remove_inventory():
    try:
        data = request.json
        name = data.get('name')
        quantity_left = data.get('quantity')

        if not name:
            return jsonify(sanitize_json({"error": "Item name is required"})), 400
        try:
            quantity_left = float(quantity_left)
            if quantity_left < 0:
                return jsonify(sanitize_json({"error": "Quantity left cannot be negative"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Quantity must be a valid number"})), 400

        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT quantity, cost_per_unit FROM inventory_items WHERE name = %s", (name,))
            existing = cur.fetchone()
            if not existing:
                return jsonify(sanitize_json({"error": "Item not found in inventory"})), 404
            current_quantity = float(existing[0])
            cost_per_unit = float(existing[1])
            if quantity_left > current_quantity:
                return jsonify(sanitize_json({"error": "Quantity left cannot be more than current stock"})), 400
            quantity_used = current_quantity - quantity_left
            cur.execute("UPDATE inventory_items SET quantity = %s WHERE name = %s", (quantity_left, name))
            cur.execute("INSERT INTO inventory_transactions (item_name, transaction_type, quantity, cost_per_unit, transaction_date, seller) VALUES (%s, %s, %s, %s, %s, %s)",
                        (name, 'stock_out', quantity_used, cost_per_unit, datetime.now(), 'N/A'))
            mysql.connection.commit()
            return jsonify(sanitize_json({"message": "Stock updated successfully!"}))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in remove_inventory route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/lowstock')
def lowstock():
    cur = mysql.connection.cursor()
    try:
        # Fetch all inventory items with transaction details
        cur.execute("""
            SELECT name, quantity, cost_per_unit, image,
                   (SELECT SUM(quantity) FROM inventory_transactions WHERE item_name = inventory_items.name AND transaction_type = 'stock_in') as total_stock_in,
                   (SELECT SUM(quantity) FROM inventory_transactions WHERE item_name = inventory_items.name AND transaction_type = 'stock_out') as total_stock_out
            FROM inventory_items
        """)
        inventory_items = cur.fetchall()
        
        # Fetch and process low stock items
        cur.execute("SELECT name, quantity, image FROM inventory_items WHERE quantity <= 5")
        low_stock_items_raw = cur.fetchall()
        low_stock_items = [{
            'name': item[0],
            'quantity': float(item[1]),
            'image': item[2] if item[2] else 'default.png'  # Fallback to default.png if image is None
        } for item in low_stock_items_raw]
        
        # Process inventory data
        inventory_data = [{
            'name': item[0],
            'quantity': float(item[1]),
            'cost_per_unit': float(item[2]),
            'image': item[3] if item[3] else 'default.png',  # Fallback to default.png if image is None
            'total_stock_in': float(item[4] or 0),
            'total_stock_out': float(item[5] or 0),
            'stock_status': 'Low' if float(item[1]) <= 5 else 'Sufficient'
        } for item in inventory_items]
        
        return render_template('Inventory.html', 
                             inventory=inventory_data, 
                             low_stock_items=low_stock_items, 
                             active_tab='low-stock')
    except Exception as e:
        logger.error(f"Error in lowstock route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500
    finally:
        cur.close()

@app.route('/get-images', methods=['POST'])
@csrf.exempt  # Skip CSRF check for this route
def get_images():
    try:
        data = request.get_json()  # Better JSON handling
        if not data:
            logger.error("No JSON data received in /get-images")
            return jsonify({"error": "No data provided"}), 400
        
        item_name = data.get('item_name')
        context = data.get('context')
        logger.debug(f"Received request: item_name={item_name}, context={context}")

        if not item_name:
            logger.error("Item name is missing")
            return jsonify({"error": "Item name is required"}), 400
        if context not in ['menu', 'inventory']:
            logger.error(f"Invalid context: {context}")
            return jsonify({"error": "Invalid context"}), 400

        cur = mysql.connection.cursor()
        try:
            if context == 'inventory':
                cur.execute("SELECT name, image FROM inventory_items WHERE name = %s", (item_name,))
                existing = cur.fetchone()
                if existing:
                    return jsonify({"exists": True, "image": f"/static/{existing[1]}"})
                cur.execute("SELECT DISTINCT image FROM inventory_items")
                db_images = [f"/static/{item[0]}" for item in cur.fetchall() if item[0]]
            elif context == 'menu':
                cur.execute("SELECT name, image FROM menu_items WHERE name = %s", (item_name,))
                existing = cur.fetchone()
                if existing:
                    return jsonify({"exists": True, "image": f"/static/{existing[1]}"})
                cur.execute("SELECT DISTINCT image FROM menu_items")
                db_images = [f"/static/{item[0]}" for item in cur.fetchall() if item[0]]

            static_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
            filesystem_images = [f"/static/{f}" for f in os.listdir(static_folder) if allowed_file(f)]
            all_images = list(set(db_images + filesystem_images))

            return jsonify({"exists": False, "images": all_images})
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in get_images route: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/billing', methods=['GET'])
def billing():
    with mysql.connection.cursor() as cur:
        try:
            cur.execute("""
                SELECT mi.name, mi.price, mi.image
                FROM menu_items mi
            """)
            menu_items = cur.fetchall()
            csrf_token = generate_csrf()
            return render_template('Billing.html', menu_items=menu_items, order=None, order_items=None, csrf_token=csrf_token)
        except Exception as e:
            logger.error(f"Error in billing route: {str(e)}")
            return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/billing/proceed', methods=['POST'])
def proceed_to_payment():
    try:
        data = request.json
        items = data.get('items')
        subtotal = data.get('subtotal')

        if not items or not isinstance(items, list):
            return jsonify(sanitize_json({"error": "Items list is required"})), 400
        try:
            subtotal = float(subtotal)
            if subtotal <= 0:
                return jsonify(sanitize_json({"error": "Subtotal must be positive"})), 400
        except (ValueError, TypeError):
            return jsonify(sanitize_json({"error": "Subtotal must be a valid number"})), 400

        for item in items:
            if not item.get('name'):
                return jsonify(sanitize_json({"error": "Item name is required"})), 400
            try:
                quantity = int(item.get('quantity'))
                if quantity <= 0:
                    return jsonify(sanitize_json({"error": f"Quantity for item '{item.get('name')}' must be positive"})), 400
            except (ValueError, TypeError):
                return jsonify(sanitize_json({"error": f"Quantity for item '{item.get('name')}' must be a valid integer"})), 400
            try:
                price = float(item.get('price'))
                if price <= 0:
                    return jsonify(sanitize_json({"error": f"Price for item '{item.get('name')}' must be positive"})), 400
            except (ValueError, TypeError):
                return jsonify(sanitize_json({"error": f"Price for item '{item.get('name')}' must be a valid number"})), 400

        taxes = subtotal * app.config['TAX_RATE']
        total = subtotal + taxes

        cur = mysql.connection.cursor()
        try:
            # Check stock availability
            for item in items:
                item_name = item['name']
                ordered_quantity = int(item['quantity'])
                cur.execute("""
                    SELECT mi.quantity, c.name as category_name
                    FROM menu_items mi
                    JOIN categories c ON mi.category_id = c.id
                    WHERE mi.name = %s
                """, (item_name,))
                result = cur.fetchone()
                if not result:
                    return jsonify(sanitize_json({"error": f"Item '{item_name}' not found"})), 404
                current_quantity = int(result[0])
                category_name = result[1]
                if category_name == "Quick Bites" and ordered_quantity > current_quantity:
                    return jsonify(sanitize_json({"error": f"Insufficient stock for '{item_name}'. Available: {current_quantity}, Requested: {ordered_quantity}"})), 400

            # Generate order
            order_number = generate_order_number()
            cur.execute("SELECT id FROM orders WHERE order_number = %s", (order_number,))
            order = cur.fetchone()
            if not order:
                return jsonify(sanitize_json({"error": "Failed to retrieve order ID"})), 500
            order_id = order[0]

            cur.execute("UPDATE orders SET subtotal = %s, taxes = %s, total = %s, payment_method = %s, status = %s WHERE order_number = %s",
                        (subtotal, taxes, total, 'cash', 'pending', order_number))

            for item in items:
                cur.execute("INSERT INTO order_items (order_id, item_name, price, quantity) VALUES (%s, %s, %s, %s)",
                            (order_id, item['name'], item['price'], item['quantity']))

            mysql.connection.commit()
            return jsonify(sanitize_json({"success": True, "order_number": order_number}))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in proceed_to_payment route: {str(e)}")
        return jsonify(sanitize_json({"success": False, "error": str(e)})), 500

@app.route('/billing/confirm', methods=['GET'])
def billing_confirm():
    order_number = request.args.get('order_number')
    if not order_number:
        return redirect('/billing')

    with mysql.connection.cursor() as cur:
        try:
            cur.execute("""
                SELECT order_number, subtotal, taxes, total, payment_method, status
                FROM orders WHERE order_number = %s
            """, (order_number,))
            order = cur.fetchone()
            if not order or order[5] != 'pending':
                return redirect('/billing')

            cur.execute("""
                SELECT item_name, price, quantity
                FROM order_items WHERE order_id = (SELECT id FROM orders WHERE order_number = %s)
            """, (order_number,))
            order_items = cur.fetchall()

            order_dict = {
                'order_number': order[0],
                'subtotal': float(order[1]),
                'taxes': float(order[2]),
                'total': float(order[3]),
                'payment_method': order[4]
            }
            order_items_list = [{'item_name': item[0], 'price': float(item[1]), 'quantity': int(item[2])} for item in order_items]

            cur.execute("SELECT name, price, image FROM menu_items")
            menu_items = cur.fetchall()

            csrf_token = generate_csrf()
            return render_template('Billing.html', order=order_dict, order_items=order_items_list, menu_items=menu_items, csrf_token=csrf_token)
        except Exception as e:
            logger.error(f"Error in billing_confirm route: {str(e)}")
            return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/billing/complete', methods=['POST'])
def complete_payment():
    try:
        data = request.json
        order_number = data.get('order_number')
        if not order_number:
            return jsonify(sanitize_json({"error": "Order number is required"})), 400

        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT id FROM orders WHERE order_number = %s AND status = 'pending'", (order_number,))
            order = cur.fetchone()
            if not order:
                return jsonify(sanitize_json({"error": "Order not found or already processed"})), 404
            order_id = order[0]

            cur.execute("SELECT item_name, quantity FROM order_items WHERE order_id = %s", (order_id,))
            order_items = cur.fetchall()

            for item in order_items:
                item_name = item[0]
                ordered_quantity = int(item[1])
                cur.execute("""
                    SELECT mi.quantity, c.name as category_name
                    FROM menu_items mi
                    JOIN categories c ON mi.category_id = c.id
                    WHERE mi.name = %s
                """, (item_name,))
                result = cur.fetchone()
                if not result:
                    return jsonify(sanitize_json({"error": f"Item '{item_name}' not found"})), 404
                current_quantity = int(result[0])
                category_name = result[1]
                if category_name == "Quick Bites":
                    new_quantity = current_quantity - ordered_quantity
                    if new_quantity < 0:
                        return jsonify(sanitize_json({"error": f"Insufficient stock for '{item_name}'. Available: {current_quantity}, Requested: {ordered_quantity}"})), 400
                    cur.execute("UPDATE menu_items SET quantity = %s WHERE name = %s", (new_quantity, item_name))

            cur.execute("UPDATE orders SET status = 'completed', payment_method = 'cash' WHERE order_number = %s AND status = 'pending'", (order_number,))
            if cur.rowcount == 0:
                return jsonify(sanitize_json({"error": "Order not found or already processed"})), 404

            mysql.connection.commit()
            return jsonify(sanitize_json({"success": True}))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in complete_payment route: {str(e)}")
        return jsonify(sanitize_json({"success": False, "error": str(e)})), 500

@app.route('/billing/cancel', methods=['POST'])
def cancel_order():
    try:
        data = request.json
        order_number = data.get('order_number')
        if not order_number:
            return jsonify(sanitize_json({"error": "Order number is required"})), 400

        cur = mysql.connection.cursor()
        try:
            cur.execute("UPDATE orders SET status = 'cancelled' WHERE order_number = %s AND status = 'pending'", (order_number,))
            if cur.rowcount == 0:
                return jsonify(sanitize_json({"error": "Order not found or already processed"})), 404
            mysql.connection.commit()
            return jsonify(sanitize_json({"success": True}))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in cancel_order route: {str(e)}")
        return jsonify(sanitize_json({"success": False, "error": str(e)})), 500

# Consolidated Reports and Analysis Route
@app.route('/reports-and-analysis', methods=['GET'])
def reports_and_analysis():
    cur = mysql.connection.cursor()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = today + timedelta(days=1)

        # Today's Sales
        cur.execute("""
            SELECT SUM(total) 
            FROM orders 
            WHERE status = 'completed' 
            AND created_at >= %s AND created_at < %s
        """, (today, end_of_day))
        today_sales = float(cur.fetchone()[0] or 0.00)

        # Today's Orders
        cur.execute("""
            SELECT COUNT(*) 
            FROM orders 
            WHERE status = 'completed' 
            AND created_at >= %s AND created_at < %s
        """, (today, end_of_day))
        today_orders = cur.fetchone()[0] or 0

        # Most sold item overall for today
        cur.execute("""
            SELECT oi.item_name, SUM(oi.quantity) as total_qty, c.name as category_name
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN menu_items mi ON oi.item_name = mi.name
            JOIN categories c ON mi.category_id = c.id
            WHERE o.status = 'completed' 
            AND o.created_at >= %s AND o.created_at < %s
            GROUP BY oi.item_name, c.name
            ORDER BY total_qty DESC
            LIMIT 1
        """, (today, end_of_day))
        most_sold = cur.fetchone()
        most_sold_item = most_sold[0] if most_sold else "None"
        most_sold_category = most_sold[2] if most_sold else "None"

        # Most sold item by category for today
        cur.execute("""
            SELECT c.name, oi.item_name, SUM(oi.quantity) as total_qty
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN menu_items mi ON oi.item_name = mi.name
            JOIN categories c ON mi.category_id = c.id
            WHERE o.status = 'completed'
            AND o.created_at >= %s AND o.created_at < %s
            GROUP BY c.name, oi.item_name
            ORDER BY c.name, total_qty DESC
        """, (today, end_of_day))
        category_items = cur.fetchall()

        most_sold_by_category = {}
        for category, item_name, total_qty in category_items:
            if category not in most_sold_by_category:
                most_sold_by_category[category] = {"item_name": item_name, "quantity": int(total_qty)}

        # Initial orders and sales data
        orders = []
        sales_data = None
        report_type = None

        # Use Flask-WTF's CSRF token generation within app context
        from flask_wtf.csrf import generate_csrf  # Import here if needed
        csrf_token = generate_csrf()

        return render_template('ReportsAndAnalysis.html', 
                             today_sales=today_sales, 
                             today_orders=today_orders, 
                             most_sold_item=most_sold_item,
                             most_sold_category=most_sold_category,
                             most_sold_by_category=most_sold_by_category,
                             orders=orders,
                             sales_data=sales_data,
                             report_type=report_type,
                             csrf_token=csrf_token)  # Pass CSRF token to template
    except Exception as e:
        logger.error(f"Error in reports_and_analysis route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500
    finally:
        cur.close()

# Add new route to fetch CSRF token if needed dynamically
@app.route('/get-csrf-token', methods=['GET'])
def get_csrf_token():
    token = generate_csrf()
    return jsonify({"csrf_token": token})

@app.route('/reports-and-analysis/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.json
        from_date = data.get('from_date')
        if not from_date:
            return jsonify(sanitize_json({"error": "Please provide a start date for the weekly report"})), 400

        try:
            start_date = datetime.strptime(from_date, '%Y-%m-%d')
        except ValueError:
            return jsonify(sanitize_json({"error": "Invalid date format. Use YYYY-MM-DD"})), 400
        end_date = start_date + timedelta(days=7)

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                SELECT SUM(o.total) as total_sales, SUM(o.subtotal) as costs
                FROM orders o
                WHERE o.status = 'completed' 
                AND o.created_at >= %s AND o.created_at < %s
            """, (start_date, end_date))
            sales_result = cur.fetchone()
            total_sales = float(sales_result[0]) if sales_result[0] else 0.0
            total_costs = float(sales_result[1]) if sales_result[1] else 0.0
            total_profits = total_sales - total_costs

            cur.execute("""
                SELECT SUM(oi.quantity) as total_goods
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.status = 'completed'
                AND o.created_at >= %s AND o.created_at < %s
            """, (start_date, end_date))
            total_goods = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT it.item_name, SUM(it.quantity) as total_used
                FROM inventory_transactions it
                WHERE it.transaction_date >= %s AND it.transaction_date < %s
                AND it.transaction_type = 'stock_out'
                GROUP BY it.item_name
                ORDER BY total_used DESC
                LIMIT 1
            """, (start_date, end_date))
            most_used_result = cur.fetchone()
            most_used_grocery = most_used_result[0] if most_used_result else "None"

            cur.execute("""
                SELECT oi.item_name, SUM(oi.quantity) as total_qty, c.name as category_name
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN menu_items mi ON oi.item_name = mi.name
                JOIN categories c ON mi.category_id = c.id
                WHERE o.status = 'completed' 
                AND o.created_at >= %s AND o.created_at < %s
                GROUP BY oi.item_name, c.name
                ORDER BY total_qty DESC
                LIMIT 1
            """, (start_date, end_date))
            most_sold_result = cur.fetchone()
            most_sold_item = most_sold_result[0] if most_sold_result else "None"
            most_sold_category = most_sold_result[2] if most_sold_result else "None"

            cur.execute("""
                SELECT c.name, SUM(oi.quantity) as total_goods, SUM(o.total) as net_sales, SUM(o.subtotal) as costs
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN menu_items mi ON oi.item_name = mi.name
                JOIN categories c ON mi.category_id = c.id
                WHERE o.status = 'completed'
                AND o.created_at >= %s AND o.created_at < %s
                GROUP BY c.name
            """, (start_date, end_date))
            category_sales = cur.fetchall()
            custom_sales_by_category = {}
            for category, total_goods, net_sales, costs in category_sales:
                custom_sales_by_category[category] = {
                    "total_goods_sold": int(total_goods) if total_goods else 0,
                    "net_sales": float(net_sales) if net_sales else 0.0,
                    "profits": (float(net_sales) - float(costs)) if net_sales and costs else 0.0
                }

            daily_data = []
            for i in range(7):
                day_start = start_date + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                day_name = day_start.strftime('%A').upper()

                cur.execute("""
                    SELECT SUM(o.total) as daily_sales, SUM(o.subtotal) as daily_costs
                    FROM orders o
                    WHERE o.status = 'completed' 
                    AND o.created_at >= %s AND o.created_at < %s
                """, (day_start, day_end))
                daily_result = cur.fetchone()
                daily_sales = float(daily_result[0]) if daily_result[0] else 0.0
                daily_costs = float(daily_result[1]) if daily_result[1] else 0.0
                daily_profits = daily_sales - daily_costs

                cur.execute("""
                    SELECT c.name, oi.item_name, SUM(oi.quantity) as total_qty
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at < %s
                    GROUP BY c.name, oi.item_name
                    ORDER BY c.name, total_qty DESC
                """, (day_start, day_end))
                daily_category_items = cur.fetchall()

                most_sold_by_category = {}
                for category, item_name, total_qty in daily_category_items:
                    if category not in most_sold_by_category:
                        most_sold_by_category[category] = {"item_name": item_name, "quantity": int(total_qty)}

                daily_data.append({
                    "date": day_start.strftime('%d-%m-%y'),
                    "day": day_name,
                    "sales": daily_sales,
                    "profits": daily_profits,
                    "most_sold_by_category": most_sold_by_category
                })

            cac = 0.0
            response = {
                "report_type": "weekly",
                "total_sales": total_sales,
                "most_used_grocery": most_used_grocery,
                "most_sold_item": most_sold_item,
                "most_sold_category": most_sold_category,
                "profits": total_profits,
                "new_menu": "None",
                "custom_sales": {
                    "total_goods_sold": int(total_goods),
                    "net_revenue_retention": total_sales,
                    "net_sales": total_sales,
                    "profits": total_profits,
                    "customer_acquisition_costs": cac,
                    "by_category": custom_sales_by_category
                },
                "daily_data": daily_data,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
            }

            return jsonify(sanitize_json(response))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in generate_report route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/reports-and-analysis/export_pdf', methods=['POST'])
def export_pdf():
    try:
        report_type = request.form.get('report_type')
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')

        if report_type != 'weekly':
            return jsonify(sanitize_json({"error": "Unsupported report type"})), 400

        if not all([from_date, to_date]):
            return jsonify(sanitize_json({"error": "Please provide both start and end dates for the weekly report"})), 400

        try:
            start_date = datetime.strptime(from_date, '%Y-%m-%d')
            end_date = datetime.strptime(to_date, '%Y-%m-%d')
        except ValueError:
            return jsonify(sanitize_json({"error": "Invalid date format. Use YYYY-MM-DD"})), 400

        cur = mysql.connection.cursor()
        try:
            # Total sales and profits for the week
            cur.execute("""
                SELECT SUM(o.total) as total_sales, SUM(o.subtotal) as costs
                FROM orders o
                WHERE o.status = 'completed' 
                AND o.created_at >= %s AND o.created_at < %s
            """, (start_date, end_date))
            sales_result = cur.fetchone()
            total_sales = float(sales_result[0] or 0.0)
            total_costs = float(sales_result[1] or 0.0)
            total_profits = total_sales - total_costs

            # Total goods sold
            cur.execute("""
                SELECT SUM(oi.quantity) as total_goods
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.status = 'completed'
                AND o.created_at >= %s AND o.created_at < %s
            """, (start_date, end_date))
            total_goods = cur.fetchone()[0] or 0

            # Most used grocery
            cur.execute("""
                SELECT it.item_name, SUM(it.quantity) as total_used
                FROM inventory_transactions it
                WHERE it.transaction_date >= %s AND it.transaction_date < %s
                AND it.transaction_type = 'stock_out'
                GROUP BY it.item_name
                ORDER BY total_used DESC
                LIMIT 1
            """, (start_date, end_date))
            most_used_result = cur.fetchone()
            most_used_grocery = most_used_result[0] if most_used_result else "None"

            # Most sold item
            cur.execute("""
                SELECT oi.item_name, SUM(oi.quantity) as total_qty, c.name as category_name
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN menu_items mi ON oi.item_name = mi.name
                JOIN categories c ON mi.category_id = c.id
                WHERE o.status = 'completed' 
                AND o.created_at >= %s AND o.created_at < %s
                GROUP BY oi.item_name, c.name
                ORDER BY total_qty DESC
                LIMIT 1
            """, (start_date, end_date))
            most_sold_result = cur.fetchone()
            most_sold_item = most_sold_result[0] if most_sold_result else "None"
            most_sold_category = most_sold_result[2] if most_sold_result else "None"

            # Daily breakdown
            daily_data = []
            for i in range((end_date - start_date).days):
                day_start = start_date + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                day_name = day_start.strftime('%A').upper()

                # Daily sales and profits
                cur.execute("""
                    SELECT SUM(o.total) as daily_sales, SUM(o.subtotal) as daily_costs
                    FROM orders o
                    WHERE o.status = 'completed' 
                    AND o.created_at >= %s AND o.created_at < %s
                """, (day_start, day_end))
                daily_result = cur.fetchone()
                daily_sales = float(daily_result[0] or 0.0)
                daily_costs = float(daily_result[1] or 0.0)
                daily_profits = daily_sales - daily_costs

                # Most sold by category for the day
                cur.execute("""
                    SELECT c.name, oi.item_name, SUM(oi.quantity) as total_qty
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at < %s
                    GROUP BY c.name, oi.item_name
                    ORDER BY c.name, total_qty DESC
                """, (day_start, day_end))
                category_items = cur.fetchall()

                most_sold_by_category = {}
                for category, item_name, total_qty in category_items:
                    if category not in most_sold_by_category:
                        most_sold_by_category[category] = {"item_name": item_name, "quantity": int(total_qty)}

                daily_data.append({
                    "date": day_start.strftime('%d-%m-%y'),
                    "day": day_name,
                    "sales": daily_sales,
                    "profits": daily_profits,
                    "most_sold_by_category": most_sold_by_category
                })

            # Create a chart using matplotlib (e.g., daily sales trend)
            dates = [entry["date"] for entry in daily_data]
            sales = [entry["sales"] for entry in daily_data]
            plt.figure(figsize=(8, 4))
            plt.plot(dates, sales, marker='o', color='b', label='Daily Sales (₹)')
            plt.title('Daily Sales Trend')
            plt.xlabel('Date')
            plt.ylabel('Sales (₹)')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()

            # Save the chart to a BytesIO buffer
            chart_buffer = io.BytesIO()
            plt.savefig(chart_buffer, format='png', bbox_inches='tight')
            chart_buffer.seek(0)
            plt.close()

            # Create the PDF using reportlab
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            elements = []

            # Define styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            subtitle_style = styles['Heading2']
            normal_style = styles['Normal']
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])

            # Add title
            elements.append(Paragraph(f"Weekly Report ({from_date} to {to_date})", title_style))
            elements.append(Spacer(1, 12))

            # Add summary
            elements.append(Paragraph("Summary", subtitle_style))
            summary_data = [
                ["Total Sales", f"₹{total_sales:.2f}"],
                ["Total Profits", f"₹{total_profits:.2f}"],
                ["Total Goods Sold", str(total_goods)],
                ["Most Used Grocery", most_used_grocery],
                ["Most Sold Item", f"{most_sold_item} ({most_sold_category})"]
            ]
            summary_table = Table(summary_data)
            summary_table.setStyle(table_style)
            elements.append(summary_table)
            elements.append(Spacer(1, 12))

            # Add the chart
            elements.append(Paragraph("Daily Sales Trend", subtitle_style))
            chart_image = Image(chart_buffer, width=400, height=200)
            elements.append(chart_image)
            elements.append(Spacer(1, 12))

            # Add daily breakdown
            elements.append(Paragraph("Daily Breakdown", subtitle_style))
            daily_table_data = [["Date", "Day", "Sales (₹)", "Profits (₹)", "Most Sold by Category"]]
            for day in daily_data:
                most_sold_str = "\n".join([f"{cat}: {item['item_name']} ({item['quantity']})" for cat, item in day['most_sold_by_category'].items()])
                daily_table_data.append([
                    day['date'],
                    day['day'],
                    f"₹{day['sales']:.2f}",
                    f"₹{day['profits']:.2f}",
                    most_sold_str
                ])
            daily_table = Table(daily_table_data)
            daily_table.setStyle(table_style)
            elements.append(daily_table)

            # Build the PDF
            doc.build(elements)

            # Prepare the response
            pdf_buffer.seek(0)
            return Response(
                pdf_buffer.getvalue(),
                mimetype='application/pdf',
                headers={"Content-Disposition": f"attachment;filename=weekly_report_{from_date}_to_{to_date}.pdf"}
            )
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in export_pdf route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/reports-and-analysis/export_chart', methods=['POST'])
def export_chart():
    try:
        report_type = request.form.get('report_type')
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')

        # Check if all fields are there
        if not report_type or not from_date or not to_date:
            return jsonify({"error": "Missing report_type, from_date, or to_date"}), 400

        # Convert dates to the right format
        try:
            start_date = datetime.strptime(from_date, '%Y-%m-%d').strftime('%Y-%m-%d 00:00:00')
            end_date = datetime.strptime(to_date, '%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
        except ValueError:
            return jsonify({"error": "Dates must be in YYYY-MM-DD format"}), 400

        # Get data from the database
        cur = mysql.connection.cursor()
        try:
            query = """
                SELECT mi.name, SUM(oi.quantity) as qty_sold
                FROM order_items oi
                JOIN menu_items mi ON oi.item_name = mi.name
                JOIN orders o ON oi.order_id = o.id
                WHERE o.status = 'completed' AND o.created_at BETWEEN %s AND %s
                GROUP BY mi.name
            """
            cur.execute(query, (start_date, end_date))
            sales_data = cur.fetchall()

            # Make a chart (even if there’s no data)
            plt.figure(figsize=(6, 3))  # Smaller size to use less memory
            if not sales_data:
                plt.text(0.5, 0.5, "No Data Available", ha='center', va='center', fontsize=12)
                plt.axis('off')
            else:
                names = [item[0] for item in sales_data]
                quantities = [item[1] for item in sales_data]
                plt.bar(names, quantities, color='skyblue')
                plt.title(f"Sales by Item ({from_date} to {to_date})")
                plt.xlabel("Items")
                plt.ylabel("Quantity Sold")
                plt.xticks(rotation=45)
                plt.grid(True, axis='y', linestyle='--', alpha=0.7)
                plt.tight_layout()

            # Save the chart to a file in memory
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            plt.close()  # Clear the chart from memory

            # Send the chart to the browser
            return Response(
                buffer.getvalue(),
                mimetype='image/png',
                headers={"Content-Disposition": f"attachment;filename={report_type}_chart.png"}
            )
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in export_chart: {str(e)}")  # Log the problem
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500

@app.route('/reports-and-analysis/orders', methods=['POST'])
def orders_history():
    try:
        data = request.json
        from_date = data.get('from_date')
        to_date = data.get('to_date')

        if not all([from_date, to_date]):
            missing = [k for k, v in {"from_date": from_date, "to_date": to_date}.items() if not v]
            return jsonify(sanitize_json({"error": f"Missing required fields: {missing}"})), 400

        try:
            start_datetime = datetime.strptime(from_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(to_date, '%Y-%m-%d')
            from_date = start_datetime.strftime('%Y-%m-%d 00:00:00')
            to_date = end_datetime.strftime('%Y-%m-%d 23:59:59')
        except ValueError:
            return jsonify(sanitize_json({"error": "Invalid date format. Use YYYY-MM-DD"})), 400

        logger.debug(f"Fetching orders from {from_date} to {to_date}")
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                SELECT o.order_number, o.total, o.status, GROUP_CONCAT(oi.item_name SEPARATOR ', ') as items
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.created_at >= %s AND o.created_at <= %s
                GROUP BY o.id, o.order_number, o.total, o.status
            """, (from_date, to_date))
            orders = cur.fetchall()
            logger.debug(f"Orders fetched: {orders}")
            
            return jsonify(sanitize_json({
                "orders": [
                    {
                        "order_number": order[0],
                        "total": float(order[1]),
                        "status": order[2],
                        "items": order[3]
                    } for order in orders
                ]
            }))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in orders_history route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

@app.route('/reports-and-analysis/sales/report', methods=['POST'])
def sales_report():
    try:
        data = request.json
        report_type = data.get('report_type')
        from_date = data.get('from_date')
        to_date = data.get('to_date')

        if not report_type:
            return jsonify(sanitize_json({"error": "Report type is required"})), 400

        # For 6-months and 12-months, calculate dates if not provided
        if report_type in ['6-months', '12-months']:
            end_datetime = datetime.now()
            if report_type == '6-months':
                start_datetime = end_datetime - timedelta(days=180)
            else:  # 12-months
                start_datetime = end_datetime - timedelta(days=365)
            # If dates are not provided, use calculated dates
            if not from_date:
                from_date = start_datetime.strftime('%Y-%m-%d')
            if not to_date:
                to_date = end_datetime.strftime('%Y-%m-%d')
        else:
            # For other report types, dates are required
            if not all([from_date, to_date]):
                missing = [k for k, v in {"from_date": from_date, "to_date": to_date}.items() if not v]
                return jsonify(sanitize_json({"error": f"Missing required fields: {missing}"})), 400

        try:
            start_datetime = datetime.strptime(from_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(to_date, '%Y-%m-%d')
            from_date = start_datetime.strftime('%Y-%m-%d 00:00:00')
            to_date = end_datetime.strftime('%Y-%m-%d 23:59:59')
        except ValueError:
            return jsonify(sanitize_json({"error": "Invalid date format. Use YYYY-MM-DD"})), 400

        logger.debug(f"Report type: {report_type}, From: {from_date}, To: {to_date}")

        cur = mysql.connection.cursor()
        try:
            if report_type == 'most-sold':
                cur.execute("""
                    SELECT oi.item_name, SUM(oi.quantity) as total_qty, c.name as category_name
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed' 
                    AND o.created_at >= %s AND o.created_at <= %s
                    GROUP BY oi.item_name, c.name
                    ORDER BY total_qty DESC
                    LIMIT 5
                """, (from_date, to_date))
                result = cur.fetchall()
                logger.debug(f"Most sold result: {result}")

                most_sold_by_category = {}
                for item_name, total_qty, category in result:
                    if category not in most_sold_by_category:
                        most_sold_by_category[category] = []
                    most_sold_by_category[category].append({
                        "item_name": item_name,
                        "quantity": int(total_qty)
                    })

                response = {
                    "most_sold_by_category": most_sold_by_category
                }

            elif report_type == 'most-used':
                cur.execute("""
                    SELECT it.item_name, SUM(it.quantity) as total_used
                    FROM inventory_transactions it
                    WHERE it.transaction_date >= %s AND it.transaction_date <= %s
                    AND it.transaction_type = 'stock_out'
                    GROUP BY it.item_name
                    ORDER BY total_used DESC
                """, (from_date, to_date))
                usage_result = cur.fetchall()
                logger.debug(f"Most used result: {usage_result}")

                cur.execute("""
                    SELECT it.item_name, it.transaction_type, it.quantity, it.cost_per_unit, it.transaction_date, it.seller
                    FROM inventory_transactions it
                    WHERE it.transaction_date >= %s AND it.transaction_date <= %s
                    ORDER BY it.item_name, it.transaction_date
                """, (from_date, to_date))
                all_transactions = cur.fetchall()
                logger.debug(f"All transactions: {all_transactions}")

                all_items = []
                for item in usage_result:
                    item_name = item[0]
                    total_used = float(item[1])
                    stock_in_transactions = [t for t in all_transactions if t[0] == item_name and t[1] == 'stock_in']
                    total_spent = sum(float(t[2]) * float(t[3]) for t in stock_in_transactions)
                    min_cost = min((float(t[3]) for t in stock_in_transactions), default=0.0)
                    max_cost = max((float(t[3]) for t in stock_in_transactions), default=0.0)
                    price_raise = max_cost - min_cost if stock_in_transactions else 0.0

                    item_transactions = [
                        {
                            "type": t[1],
                            "quantity": float(t[2]),
                            "cost_per_unit": float(t[3]),
                            "date": t[4].strftime('%Y-%m-%d'),
                            "seller": t[5] or "N/A"
                        }
                        for t in all_transactions if t[0] == item_name
                    ]

                    all_items.append({
                        "item_name": item_name,
                        "quantity_used": total_used,
                        "total_spent": total_spent,
                        "price_raise": price_raise,
                        "transactions": item_transactions
                    })

                top_3 = all_items[:3]
                response = {
                    "all_groceries": all_items,
                    "top_3_groceries": top_3
                }

            elif report_type == 'custom':
                cur.execute("""
                    SELECT SUM(oi.quantity) as total_goods
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at <= %s
                """, (from_date, to_date))
                total_goods = cur.fetchone()[0] or 0
                logger.debug(f"Total goods: {total_goods}")

                cur.execute("""
                    SELECT SUM(o.total) as net_sales, SUM(o.subtotal) as costs
                    FROM orders o
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at <= %s
                """, (from_date, to_date))
                sales_result = cur.fetchone()
                logger.debug(f"Sales result: {sales_result}")
                net_sales = float(sales_result[0]) if sales_result[0] else 0.0
                costs = float(sales_result[1]) if sales_result[1] else 0.0
                profits = net_sales - costs

                cur.execute("""
                    SELECT c.name, SUM(oi.quantity) as total_goods, SUM(o.total) as net_sales, SUM(o.subtotal) as costs
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at <= %s
                    GROUP BY c.name
                """, (from_date, to_date))
                category_sales = cur.fetchall()
                custom_sales_by_category = {}
                for category, total_goods, net_sales, costs in category_sales:
                    custom_sales_by_category[category] = {
                        "total_goods_sold": int(total_goods) if total_goods else 0,
                        "net_sales": float(net_sales) if net_sales else 0.0,
                        "profits": (float(net_sales) - float(costs)) if net_sales and costs else 0.0
                    }

                cac = 0.0
                response = {
                    "custom_report": {
                        "total_goods_sold": int(total_goods),
                        "net_revenue_retention": net_sales,
                        "net_sales": net_sales,
                        "profits": profits,
                        "customer_acquisition_costs": cac,
                        "by_category": custom_sales_by_category
                    }
                }

            elif report_type == '6-months':
                start_date = start_datetime
                end_date = end_datetime
                num_months = 6

                monthly_revenue = []
                total_revenue = 0.0
                for i in range(num_months):
                    month_start = start_date + timedelta(days=i * 30)
                    month_end = month_start + timedelta(days=30)
                    cur.execute("""
                        SELECT SUM(o.total) as monthly_sales
                        FROM orders o
                        WHERE o.status = 'completed'
                        AND o.created_at >= %s AND o.created_at < %s
                    """, (month_start, month_end))
                    monthly_sales = float(cur.fetchone()[0] or 0.0)
                    total_revenue += monthly_sales
                    monthly_revenue.append({
                        "month": month_start.strftime('%B %Y'),
                        "sales": monthly_sales
                    })

                sales_trends = {
                    "peak_month": max(monthly_revenue, key=lambda x: x['sales'], default={"month": "N/A", "sales": 0}),
                    "slow_month": min(monthly_revenue, key=lambda x: x['sales'], default={"month": "N/A", "sales": 0})
                }

                cur.execute("""
                    SELECT c.name, SUM(o.total) as category_sales, SUM(oi.quantity) as total_qty
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at <= %s
                    GROUP BY c.name
                """, (start_date, end_date))
                category_sales = cur.fetchall()
                category_wise_sales = {}
                for category, sales, qty in category_sales:
                    category_wise_sales[category] = {
                        "sales": float(sales) if sales else 0.0,
                        "quantity": int(qty) if qty else 0
                    }

                cur.execute("""
                    SELECT oi.item_name, SUM(oi.quantity) as total_qty, c.name as category_name
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at <= %s
                    GROUP BY oi.item_name, c.name
                    ORDER BY total_qty DESC
                    LIMIT 5
                """, (start_date, end_date))
                best_selling_items = [
                    {"item_name": item[0], "quantity": int(item[1]), "category": item[2]}
                    for item in cur.fetchall()
                ]

                monthly_expenses = []
                total_expenses = 0.0
                operational_expenses = app.config['OPERATIONAL_EXPENSES']
                for i in range(num_months):
                    month_start = start_date + timedelta(days=i * 30)
                    month_end = month_start + timedelta(days=30)
                    cur.execute("""
                        SELECT SUM(it.quantity * it.cost_per_unit) as cogs
                        FROM inventory_transactions it
                        WHERE it.transaction_type = 'stock_out'
                        AND it.transaction_date >= %s AND it.transaction_date < %s
                    """, (month_start, month_end))
                    cogs_result = cur.fetchone()
                    cogs = float(cogs_result[0] or 0.0)
                    month_expenses = cogs + sum(operational_expenses.values())
                    total_expenses += month_expenses
                    monthly_expenses.append({
                        "month": month_start.strftime('%B %Y'),
                        "cogs": cogs,
                        "operational": operational_expenses,
                        "total": month_expenses
                    })

                gross_profit = total_revenue - sum(exp['cogs'] for exp in monthly_expenses)
                net_profit = total_revenue - total_expenses
                gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0
                net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

                cur.execute("""
                    SELECT it.item_name, SUM(it.quantity) as total_used
                    FROM inventory_transactions it
                    WHERE it.transaction_type = 'stock_out'
                    AND it.transaction_date >= %s AND it.transaction_date <= %s
                    GROUP BY it.item_name
                    ORDER BY total_used DESC
                """, (start_date, end_date))
                stock_usage = [
                    {"item_name": item[0], "quantity_used": float(item[1])}
                    for item in cur.fetchall()
                ]

                wastage = sum(item['quantity_used'] * 0.05 for item in stock_usage)

                cur.execute("""
                    SELECT it.item_name, it.transaction_type, it.quantity, it.transaction_date
                    FROM inventory_transactions it
                    WHERE it.transaction_date >= %s AND it.transaction_date <= %s
                    ORDER BY it.transaction_date
                """, (start_date, end_date))
                inventory_transactions = cur.fetchall()
                low_stock_alerts = [
                    {"item_name": t[0], "date": t[3].strftime('%Y-%m-%d'), "quantity": float(t[2])}
                    for t in inventory_transactions if t[1] == 'stock_out' and float(t[2]) <= 5
                ]
                restocking_history = [
                    {"item_name": t[0], "date": t[3].strftime('%Y-%m-%d'), "quantity": float(t[2])}
                    for t in inventory_transactions if t[1] == 'stock_in'
                ]

                cur.execute("""
                    SELECT it.seller, COUNT(*) as transactions, SUM(it.quantity * it.cost_per_unit) as total_spent
                    FROM inventory_transactions it
                    WHERE it.transaction_type = 'stock_in'
                    AND it.transaction_date >= %s AND it.transaction_date <= %s
                    GROUP BY it.seller
                """, (start_date, end_date))
                supplier_performance = [
                    {"seller": s[0], "transactions": int(s[1]), "total_spent": float(s[2])}
                    for s in cur.fetchall() if s[0] != 'N/A'
                ]

                response = {
                    "six_months_report": {
                        "total_revenue": total_revenue,
                        "total_expenses": total_expenses,
                        "monthly_revenue": monthly_revenue,
                        "sales_trends": sales_trends,
                        "category_wise_sales": category_wise_sales,
                        "best_selling_items": best_selling_items,
                        "profitability": {
                            "gross_profit": gross_profit,
                            "net_profit": net_profit,
                            "gross_margin": gross_margin,
                            "net_margin": net_margin
                        }
                    }
                }

            elif report_type == '12-months':
                start_date = start_datetime
                end_date = end_datetime
                num_months = 12

                monthly_revenue = []
                total_revenue = 0.0
                for i in range(num_months):
                    month_start = start_date + timedelta(days=i * 30)
                    month_end = month_start + timedelta(days=30)
                    cur.execute("""
                        SELECT SUM(o.total) as monthly_sales
                        FROM orders o
                        WHERE o.status = 'completed'
                        AND o.created_at >= %s AND o.created_at < %s
                    """, (month_start, month_end))
                    monthly_sales = float(cur.fetchone()[0] or 0.0)
                    total_revenue += monthly_sales
                    monthly_revenue.append({
                        "month": month_start.strftime('%B %Y'),
                        "sales": monthly_sales
                    })

                sales_trends = {
                    "peak_month": max(monthly_revenue, key=lambda x: x['sales'], default={"month": "N/A", "sales": 0}),
                    "slow_month": min(monthly_revenue, key=lambda x: x['sales'], default={"month": "N/A", "sales": 0})
                }

                cur.execute("""
                    SELECT c.name, SUM(o.total) as category_sales, SUM(oi.quantity) as total_qty
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at <= %s
                    GROUP BY c.name
                """, (start_date, end_date))
                category_sales = cur.fetchall()
                category_wise_sales = {}
                for category, sales, qty in category_sales:
                    category_wise_sales[category] = {
                        "sales": float(sales) if sales else 0.0,
                        "quantity": int(qty) if qty else 0
                    }

                prev_year_start = start_date - timedelta(days=365)
                prev_year_end = start_date
                cur.execute("""
                    SELECT SUM(o.total) as prev_year_sales
                    FROM orders o
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at < %s
                """, (prev_year_start, prev_year_end))
                prev_year_result = cur.fetchone()
                prev_year_sales = float(prev_year_result[0] or 0.0)
                yoy_growth = ((total_revenue - prev_year_sales) / prev_year_sales * 100) if prev_year_sales > 0 else 0.0

                cur.execute("""
                    SELECT oi.item_name, SUM(oi.quantity) as total_qty, c.name as category_name
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN menu_items mi ON oi.item_name = mi.name
                    JOIN categories c ON mi.category_id = c.id
                    WHERE o.status = 'completed'
                    AND o.created_at >= %s AND o.created_at <= %s
                    GROUP BY oi.item_name, c.name
                    ORDER BY total_qty DESC
                    LIMIT 5
                """, (start_date, end_date))
                best_selling_items = [
                    {"item_name": item[0], "quantity": int(item[1]), "category": item[2]}
                    for item in cur.fetchall()
                ]

                monthly_expenses = []
                total_expenses = 0.0
                operational_expenses = app.config['OPERATIONAL_EXPENSES']
                for i in range(num_months):
                    month_start = start_date + timedelta(days=i * 30)
                    month_end = month_start + timedelta(days=30)
                    cur.execute("""
                        SELECT SUM(it.quantity * it.cost_per_unit) as cogs
                        FROM inventory_transactions it
                        WHERE it.transaction_type = 'stock_out'
                        AND it.transaction_date >= %s AND it.transaction_date < %s
                    """, (month_start, month_end))
                    cogs_result = cur.fetchone()
                    cogs = float(cogs_result[0] or 0.0)
                    month_expenses = cogs + sum(operational_expenses.values())
                    total_expenses += month_expenses
                    monthly_expenses.append({
                        "month": month_start.strftime('%B %Y'),
                        "cogs": cogs,
                        "operational": operational_expenses,
                        "total": month_expenses
                    })

                gross_profit = total_revenue - sum(exp['cogs'] for exp in monthly_expenses)
                net_profit = total_revenue - total_expenses
                gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0
                net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

                cur.execute("""
                    SELECT it.item_name, SUM(it.quantity) as total_used
                    FROM inventory_transactions it
                    WHERE it.transaction_type = 'stock_out'
                    AND it.transaction_date >= %s AND it.transaction_date <= %s
                    GROUP BY it.item_name
                    ORDER BY total_used DESC
                """, (start_date, end_date))
                stock_usage = [
                    {"item_name": item[0], "quantity_used": float(item[1])}
                    for item in cur.fetchall()
                ]

                wastage = sum(item['quantity_used'] * 0.05 for item in stock_usage)  # Assuming 5% wastage

                cur.execute("""
                    SELECT it.item_name, it.transaction_type, it.quantity, it.transaction_date
                    FROM inventory_transactions it
                    WHERE it.transaction_date >= %s AND it.transaction_date <= %s
                    ORDER BY it.transaction_date
                """, (start_date, end_date))
                inventory_transactions = cur.fetchall()
                low_stock_alerts = [
                    {"item_name": t[0], "date": t[3].strftime('%Y-%m-%d'), "quantity": float(t[2])}
                    for t in inventory_transactions if t[1] == 'stock_out' and float(t[2]) <= 5
                ]
                restocking_history = [
                    {"item_name": t[0], "date": t[3].strftime('%Y-%m-%d'), "quantity": float(t[2])}
                    for t in inventory_transactions if t[1] == 'stock_in'
                ]

                cur.execute("""
                    SELECT it.seller, COUNT(*) as transactions, SUM(it.quantity * it.cost_per_unit) as total_spent
                    FROM inventory_transactions it
                    WHERE it.transaction_type = 'stock_in'
                    AND it.transaction_date >= %s AND it.transaction_date <= %s
                    GROUP BY it.seller
                """, (start_date, end_date))
                supplier_performance = [
                    {"seller": s[0], "transactions": int(s[1]), "total_spent": float(s[2])}
                    for s in cur.fetchall() if s[0] != 'N/A'
                ]

                response = {
                    "twelve_months_report": {
                        "total_revenue": total_revenue,
                        "total_expenses": total_expenses,
                        "monthly_revenue": monthly_revenue,
                        "sales_trends": sales_trends,
                        "category_wise_sales": category_wise_sales,
                        "year_over_year_growth": yoy_growth,
                        "best_selling_items": best_selling_items,
                        "profitability": {
                            "gross_profit": gross_profit,
                            "net_profit": net_profit,
                            "gross_margin": gross_margin,
                            "net_margin": net_margin
                        },
                        "stock_usage": stock_usage,
                        "wastage": wastage,
                        "low_stock_alerts": low_stock_alerts,
                        "restocking_history": restocking_history,
                        "supplier_performance": supplier_performance
                    }
                }

            else:
                return jsonify(sanitize_json({"error": "Invalid report type"})), 400

            return jsonify(sanitize_json(response))
        finally:
            cur.close()
    except Exception as e:
        logger.error(f"Error in sales_report route: {str(e)}")
        return jsonify(sanitize_json({"error": str(e)})), 500

# Main entry point
if __name__ == '__main__':
    app.run(debug=True)