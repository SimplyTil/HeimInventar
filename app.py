from flask import Flask, render_template, request, jsonify, abort, send_from_directory
import sqlite3
import requests
import os
from datetime import datetime
from functools import lru_cache
import re
import base64
import uuid

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max request size
DB_NAME = "inventory.db"
UPLOADS_DIR = 'static/uploads'

# Ensure uploads directory exists
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# --- Database Helper Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def sanitize_input(text, max_length=500):
    """Sanitize user input to prevent injection attacks."""
    if not text:
        return text
    # Remove null bytes and limit length
    sanitized = str(text).replace('\x00', '')[:max_length]
    return sanitized.strip()

def save_base64_image(base64_string):
    """Save base64 image to uploads folder and return filename."""
    try:
        # Extract image data from base64 string
        if ',' in base64_string:
            header, data = base64_string.split(',', 1)
        else:
            return None
        
        # Decode base64
        image_data = base64.b64decode(data)
        
        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOADS_DIR, filename)
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        return filename
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

def delete_image(image_url):
    """Delete image file from uploads folder."""
    try:
        if image_url.startswith('/static/uploads/'):
            filename = image_url.split('/')[-1]
            filepath = os.path.join(UPLOADS_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
    except Exception as e:
        print(f"Error deleting image: {e}")

def update_barcode_history(conn, ean, name, category=None, weight_volume=None, tags=None, is_vegetarian=False, is_vegan=False):
    """Update or create barcode history entry with full product metadata."""
    try:
        existing = conn.execute(
            'SELECT id, scan_count FROM barcode_history WHERE ean = ?', 
            (ean,)
        ).fetchone()
        
        if existing:
            conn.execute('''
                UPDATE barcode_history 
                SET scan_count = ?, last_scanned = ?, name = ?, category = ?, weight_volume = ?, tags = ?, is_vegetarian = ?, is_vegan = ?
                WHERE id = ?
            ''', (existing['scan_count'] + 1, datetime.now().isoformat(), name, category, weight_volume, tags, 
                  1 if is_vegetarian else 0, 1 if is_vegan else 0, existing['id']))
        else:
            conn.execute('''
                INSERT INTO barcode_history (ean, name, category, weight_volume, tags, is_vegetarian, is_vegan, scan_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ean, name, category, weight_volume, tags, 1 if is_vegetarian else 0, 1 if is_vegan else 0, 1))
    except Exception as e:
        print(f"Error updating barcode history: {e}")

def init_db():
    """Initializes the database with the products table and handles migrations."""
    conn = get_db_connection()
    if not conn:
        return

    c = conn.cursor()
    
    # Create products table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ean TEXT,
            name TEXT NOT NULL,
            expiry_date TEXT,
            purchase_date TEXT,
            location TEXT,
            quantity INTEGER DEFAULT 1,
            weight_volume TEXT,
            notes TEXT,
            is_vegetarian INTEGER DEFAULT 0,
            is_vegan INTEGER DEFAULT 0,
            price REAL DEFAULT 0.0,
            image_url TEXT,
            category TEXT,
            tags TEXT,
            scan_count INTEGER DEFAULT 0,
            last_scanned TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create shopping list table
    c.execute('''
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            category TEXT,
            checked INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create barcode history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS barcode_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ean TEXT NOT NULL,
            name TEXT,
            category TEXT,
            weight_volume TEXT,
            tags TEXT,
            is_vegetarian INTEGER DEFAULT 0,
            is_vegan INTEGER DEFAULT 0,
            scan_count INTEGER DEFAULT 1,
            last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for better performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_expiry_date ON products(expiry_date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_location ON products(location)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_name ON products(name)')
    
    # Migration: Check if weight_volume exists, if not add it
    try:
        c.execute('SELECT weight_volume FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding weight_volume column...")
        c.execute('ALTER TABLE products ADD COLUMN weight_volume TEXT')
    
    # Migration: Add created_at if missing
    try:
        c.execute('SELECT created_at FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding created_at column...")
        c.execute('ALTER TABLE products ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    
    # Migration: Add price if missing
    try:
        c.execute('SELECT price FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding price column...")
        c.execute('ALTER TABLE products ADD COLUMN price REAL DEFAULT 0.0')
    
    # Migration: Add image_url if missing
    try:
        c.execute('SELECT image_url FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding image_url column...")
        c.execute('ALTER TABLE products ADD COLUMN image_url TEXT')
    
    # Migration: Add category if missing
    try:
        c.execute('SELECT category FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding category column...")
        c.execute('ALTER TABLE products ADD COLUMN category TEXT')
    
    # Migration: Add tags if missing
    try:
        c.execute('SELECT tags FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding tags column...")
        c.execute('ALTER TABLE products ADD COLUMN tags TEXT')
    
    # Migration: Add scan_count if missing
    try:
        c.execute('SELECT scan_count FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding scan_count column...")
        c.execute('ALTER TABLE products ADD COLUMN scan_count INTEGER DEFAULT 0')
    
    # Migration: Add last_scanned if missing
    try:
        c.execute('SELECT last_scanned FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating database: Adding last_scanned column...")
        c.execute('ALTER TABLE products ADD COLUMN last_scanned TEXT')
    
    # Migrations for barcode_history
    try:
        c.execute('SELECT category FROM barcode_history LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating barcode_history: Adding category column...")
        c.execute('ALTER TABLE barcode_history ADD COLUMN category TEXT')
    
    try:
        c.execute('SELECT weight_volume FROM barcode_history LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating barcode_history: Adding weight_volume column...")
        c.execute('ALTER TABLE barcode_history ADD COLUMN weight_volume TEXT')
    
    try:
        c.execute('SELECT tags FROM barcode_history LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating barcode_history: Adding tags column...")
        c.execute('ALTER TABLE barcode_history ADD COLUMN tags TEXT')
    
    try:
        c.execute('SELECT is_vegetarian FROM barcode_history LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating barcode_history: Adding is_vegetarian column...")
        c.execute('ALTER TABLE barcode_history ADD COLUMN is_vegetarian INTEGER DEFAULT 0')
    
    try:
        c.execute('SELECT is_vegan FROM barcode_history LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating barcode_history: Adding is_vegan column...")
        c.execute('ALTER TABLE barcode_history ADD COLUMN is_vegan INTEGER DEFAULT 0')
        
    conn.commit()
    conn.close()

# --- Error Handling ---

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad Request', 'message': str(error.description)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found', 'message': str(error.description)}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred.'}), 500

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    """Retrieve all products."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        products = conn.execute('SELECT * FROM products').fetchall()
        return jsonify([dict(ix) for ix in products]), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/products', methods=['POST'])
def add_product():
    """Create a new product."""
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    data = request.json
    
    # Validation
    name = sanitize_input(data.get('name'), 200)
    if not name:
        abort(400, description="Product name is required")
    
    # Validate quantity
    try:
        quantity = int(data.get('quantity', 1))
        if quantity < 1 or quantity > 9999:
            abort(400, description="Quantity must be between 1 and 9999")
    except (ValueError, TypeError):
        abort(400, description="Invalid quantity")

    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")

    try:
        c = conn.cursor()
        
        # Handle image storage
        image_url = data.get('image_url', '')
        image_filename = ''
        if image_url and image_url.startswith('data:image'):
            # Save base64 image to file
            image_filename = save_base64_image(image_url)
            image_url = f'/static/uploads/{image_filename}' if image_filename else ''
        
        c.execute('''
            INSERT INTO products (ean, name, expiry_date, purchase_date, location, quantity, weight_volume, notes, is_vegetarian, is_vegan, price, image_url, category, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sanitize_input(data.get('ean'), 50),
            name,
            sanitize_input(data.get('expiry_date'), 20),
            sanitize_input(data.get('purchase_date', datetime.now().strftime('%Y-%m-%d')), 20),
            sanitize_input(data.get('location'), 100),
            quantity,
            sanitize_input(data.get('weight_volume'), 50),
            sanitize_input(data.get('notes'), 1000),
            1 if data.get('is_vegetarian') else 0,
            1 if data.get('is_vegan') else 0,
            float(data.get('price', 0.0)),
            image_url,
            sanitize_input(data.get('category'), 50),
            sanitize_input(data.get('tags'), 200)
        ))
        
        # Update barcode history with full product metadata
        ean = data.get('ean')
        if ean:
            update_barcode_history(conn, ean, name, data.get('category'), data.get('weight_volume'), 
                                 data.get('tags'), data.get('is_vegetarian'), data.get('is_vegan'))
        conn.commit()
        new_id = c.lastrowid
        return jsonify({'id': new_id, 'message': 'Produkt erfolgreich erstellt'}), 201
    except sqlite3.Error as e:
        conn.rollback()
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    """Update an existing product."""
    if not request.json:
        abort(400, description="Request body must be JSON")

    data = request.json
    
    # Validation
    name = sanitize_input(data.get('name'), 200)
    if not name:
        abort(400, description="Product name is required")
    
    try:
        quantity = int(data.get('quantity', 1))
        if quantity < 1 or quantity > 9999:
            abort(400, description="Quantity must be between 1 and 9999")
    except (ValueError, TypeError):
        abort(400, description="Invalid quantity")
    
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")

    try:
        # Check if product exists and get current image
        product = conn.execute('SELECT id, image_url FROM products WHERE id = ?', (id,)).fetchone()
        if not product:
            abort(404, description=f"Product with ID {id} not found")

        # Handle image storage
        image_url = data.get('image_url', '')
        old_image = product['image_url']
        
        if image_url and image_url.startswith('data:image'):
            # New base64 image - save it
            image_filename = save_base64_image(image_url)
            image_url = f'/static/uploads/{image_filename}' if image_filename else old_image
            # Delete old image if exists
            if old_image and old_image.startswith('/static/uploads/'):
                delete_image(old_image)
        elif not image_url and old_image:
            # Image was removed
            if old_image.startswith('/static/uploads/'):
                delete_image(old_image)
            image_url = ''
        elif not image_url:
            # Keep old image
            image_url = old_image or ''

        conn.execute('''
            UPDATE products SET 
                name = ?, expiry_date = ?, purchase_date = ?, location = ?, 
                quantity = ?, weight_volume = ?, notes = ?, is_vegetarian = ?, is_vegan = ?, price = ?, image_url = ?, category = ?, tags = ?
            WHERE id = ?
        ''', (
            name,
            sanitize_input(data.get('expiry_date'), 20),
            sanitize_input(data.get('purchase_date'), 20),
            sanitize_input(data.get('location'), 100),
            quantity,
            sanitize_input(data.get('weight_volume'), 50),
            sanitize_input(data.get('notes'), 1000),
            1 if data.get('is_vegetarian') else 0,
            1 if data.get('is_vegan') else 0,
            float(data.get('price', 0.0)),
            image_url,
            sanitize_input(data.get('category'), 50),
            sanitize_input(data.get('tags'), 200),
            id
        ))
        conn.commit()
        return jsonify({'message': 'Produkt erfolgreich aktualisiert'}), 200
    except sqlite3.Error as e:
        conn.rollback()
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    """Delete a product but preserve barcode history."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")

    try:
        # Check if product exists and get image
        product = conn.execute('SELECT image_url, ean, name, category, weight_volume, tags, is_vegetarian, is_vegan FROM products WHERE id = ?', (id,)).fetchone()
        if not product:
            abort(404, description=f"Product with ID {id} not found")

        # Update barcode history before deleting (preserve metadata)
        if product['ean']:
            update_barcode_history(conn, product['ean'], product['name'], product['category'], 
                                 product['weight_volume'], product['tags'], 
                                 product['is_vegetarian'], product['is_vegan'])
        
        # Delete image file if exists
        if product['image_url'] and product['image_url'].startswith('/static/uploads/'):
            delete_image(product['image_url'])
        
        conn.execute('DELETE FROM products WHERE id = ?', (id,))
        conn.commit()
        return jsonify({'message': 'Produkt erfolgreich gelöscht'}), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/products/batch', methods=['POST'])
def batch_operations():
    """Perform batch operations on multiple products."""
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    data = request.json
    operation = data.get('operation')
    product_ids = data.get('product_ids', [])
    
    if not operation or not product_ids:
        abort(400, description="Operation and product_ids are required")
    
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        if operation == 'delete':
            placeholders = ','.join('?' * len(product_ids))
            conn.execute(f'DELETE FROM products WHERE id IN ({placeholders})', product_ids)
        elif operation == 'update_location':
            location = sanitize_input(data.get('location'), 100)
            placeholders = ','.join('?' * len(product_ids))
            conn.execute(f'UPDATE products SET location = ? WHERE id IN ({placeholders})', [location] + product_ids)
        else:
            abort(400, description="Invalid operation")
        
        conn.commit()
        return jsonify({'message': f'{len(product_ids)} Produkte aktualisiert'}), 200
    except sqlite3.Error as e:
        conn.rollback()
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get inventory statistics."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        # Total products and value
        total = conn.execute('SELECT COUNT(*), SUM(quantity), SUM(price * quantity) FROM products').fetchone()
        
        # Expiring soon (within 7 days)
        from datetime import datetime, timedelta
        week_from_now = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        expiring = conn.execute('SELECT COUNT(*) FROM products WHERE expiry_date <= ? AND expiry_date >= date("now")', (week_from_now,)).fetchone()
        
        # Expired
        expired = conn.execute('SELECT COUNT(*) FROM products WHERE expiry_date < date("now")').fetchone()
        
        # By location
        by_location = conn.execute('SELECT location, COUNT(*), SUM(quantity) FROM products GROUP BY location').fetchall()
        
        # Price trends (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        recent_additions = conn.execute(
            'SELECT COUNT(*), SUM(price * quantity) FROM products WHERE created_at >= ?', 
            (thirty_days_ago,)
        ).fetchone()
        
        return jsonify({
            'total_products': total[0] or 0,
            'total_items': total[1] or 0,
            'total_value': round(total[2] or 0, 2),
            'expiring_soon': expiring[0] or 0,
            'expired': expired[0] or 0,
            'by_location': [{'location': row[0], 'products': row[1], 'items': row[2]} for row in by_location],
            'recent_additions_count': recent_additions[0] or 0,
            'recent_additions_value': round(recent_additions[1] or 0, 2)
        }), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/products/check-duplicate', methods=['POST'])
def check_duplicate():
    """Check if a product with same EAN or name exists."""
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    data = request.json
    ean = data.get('ean')
    name = data.get('name')
    
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        duplicates = []
        
        if ean:
            ean_matches = conn.execute('SELECT * FROM products WHERE ean = ? AND ean != ""', (ean,)).fetchall()
            duplicates.extend([dict(row) for row in ean_matches])
        
        if name and not duplicates:
            name_matches = conn.execute(
                'SELECT * FROM products WHERE LOWER(name) = LOWER(?) LIMIT 5', 
                (name,)
            ).fetchall()
            duplicates.extend([dict(row) for row in name_matches])
        
        return jsonify({
            'found': len(duplicates) > 0,
            'duplicates': duplicates[:5]
        }), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/scan/<ean>', methods=['GET'])
def scan_product(ean):
    """Proxy to Open Food Facts API and track scan history."""
    # Validate EAN format (digits only, typical length 8, 12, or 13)
    if not ean or not re.match(r'^\d{8,13}$', ean):
        abort(400, description="Invalid EAN format")

    url = f"https://world.openfoodfacts.org/api/v0/product/{ean}.json"
    try:
        response = requests.get(url, timeout=5, headers={'User-Agent': 'SmartKitchenInventory/1.0'})
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 1:
            product = data['product']
            product_name = product.get('product_name', 'Unbekanntes Produkt')[:200]
            
            # Extract category from API
            categories = product.get('categories', '')
            category = categories.split(',')[0].strip() if categories else ''
            
            # Check if vegetarian/vegan
            is_vegetarian = 'vegetarian' in categories.lower() if categories else False
            is_vegan = 'vegan' in categories.lower() if categories else False
            
            # Update barcode history with full metadata
            conn = get_db_connection()
            if conn:
                try:
                    update_barcode_history(conn, ean, product_name, category, 
                                         product.get('quantity', ''), '', is_vegetarian, is_vegan)
                    conn.commit()
                except Exception as e:
                    print(f"History update error: {e}")
                finally:
                    conn.close()
            
            return jsonify({
                'found': True,
                'name': product_name,
                'image_url': product.get('image_url', '')[:500],
                'quantity': product.get('quantity', '')[:50],
                'brands': product.get('brands', '')[:200],
                'category': category
            })
        else:
            return jsonify({'found': False, 'message': 'Produkt nicht in der Datenbank gefunden'}), 404
    except requests.Timeout:
        return jsonify({'found': False, 'error': 'API-Anfrage hat zu lange gedauert'}), 504
    except requests.RequestException as e:
        return jsonify({'found': False, 'error': 'Fehler bei der Verbindung zur externen API'}), 502
    except Exception as e:
        print(f"Unexpected error in scan_product: {e}")
        return jsonify({'found': False, 'error': 'Ein unerwarteter Fehler ist aufgetreten'}), 500

@app.route('/api/shopping-list', methods=['GET'])
def get_shopping_list():
    """Get all shopping list items."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        items = conn.execute('SELECT * FROM shopping_list ORDER BY checked ASC, created_at DESC').fetchall()
        return jsonify([dict(row) for row in items]), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/shopping-list', methods=['POST'])
def add_to_shopping_list():
    """Add item to shopping list."""
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    data = request.json
    name = sanitize_input(data.get('name'), 200)
    if not name:
        abort(400, description="Name is required")
    
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        conn.execute(
            'INSERT INTO shopping_list (name, quantity, category, notes) VALUES (?, ?, ?, ?)',
            (name, int(data.get('quantity', 1)), sanitize_input(data.get('category'), 50), sanitize_input(data.get('notes'), 500))
        )
        conn.commit()
        return jsonify({'message': 'Item added to shopping list'}), 201
    except sqlite3.Error as e:
        conn.rollback()
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/shopping-list/<int:id>', methods=['PUT'])
def update_shopping_item(id):
    """Update shopping list item (mainly for checking/unchecking)."""
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    data = request.json
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        conn.execute(
            'UPDATE shopping_list SET checked = ?, name = ?, quantity = ? WHERE id = ?',
            (1 if data.get('checked') else 0, sanitize_input(data.get('name'), 200), int(data.get('quantity', 1)), id)
        )
        conn.commit()
        return jsonify({'message': 'Item updated'}), 200
    except sqlite3.Error as e:
        conn.rollback()
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/shopping-list/<int:id>', methods=['DELETE'])
def delete_shopping_item(id):
    """Delete shopping list item."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        conn.execute('DELETE FROM shopping_list WHERE id = ?', (id,))
        conn.commit()
        return jsonify({'message': 'Item deleted'}), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/shopping-list/clear-checked', methods=['DELETE'])
def clear_checked_items():
    """Delete all checked items from shopping list."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        conn.execute('DELETE FROM shopping_list WHERE checked = 1')
        conn.commit()
        return jsonify({'message': 'Checked items cleared'}), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/shopping-list/generate', methods=['POST'])
def generate_shopping_list():
    """Generate shopping list from expired and low stock items."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        # Get expired or low stock items
        items = conn.execute('''
            SELECT name, category, quantity FROM products 
            WHERE (expiry_date < date('now') OR quantity <= 1)
            AND name NOT IN (SELECT name FROM shopping_list)
        ''').fetchall()
        
        added = 0
        for item in items:
            conn.execute(
                'INSERT INTO shopping_list (name, quantity, category, notes) VALUES (?, ?, ?, ?)',
                (item['name'], 1, item['category'], 'Auto-generiert')
            )
            added += 1
        
        conn.commit()
        return jsonify({'message': f'{added} items added to shopping list', 'count': added}), 200
    except sqlite3.Error as e:
        conn.rollback()
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/barcode-history', methods=['GET'])
def get_barcode_history():
    """Get barcode scan history."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        limit = request.args.get('limit', 10, type=int)
        history = conn.execute(
            'SELECT * FROM barcode_history ORDER BY last_scanned DESC LIMIT ?',
            (limit,)
        ).fetchall()
        return jsonify([dict(row) for row in history]), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

@app.route('/api/statistics/advanced', methods=['GET'])
def get_advanced_statistics():
    """Get advanced statistics including waste tracking and consumption patterns."""
    conn = get_db_connection()
    if not conn:
        abort(500, description="Database connection failed")
    
    try:
        from datetime import datetime, timedelta
        
        # Total waste value (expired items)
        waste = conn.execute(
            'SELECT COUNT(*) as count, SUM(price * quantity) as value FROM products WHERE expiry_date < date("now")'
        ).fetchone()
        
        # Category breakdown
        by_category = conn.execute(
            'SELECT category, COUNT(*) as count, SUM(quantity) as items FROM products WHERE category IS NOT NULL AND category != "" GROUP BY category'
        ).fetchall()
        
        # Most scanned items
        top_scanned = conn.execute(
            'SELECT name, scan_count, last_scanned FROM barcode_history ORDER BY scan_count DESC LIMIT 5'
        ).fetchall()
        
        # Weekly additions
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        weekly_additions = conn.execute(
            'SELECT COUNT(*) as count FROM products WHERE created_at >= ?',
            (week_ago,)
        ).fetchone()
        
        # Average price per category
        avg_by_category = conn.execute(
            'SELECT category, AVG(price) as avg_price FROM products WHERE category IS NOT NULL AND category != "" AND price > 0 GROUP BY category'
        ).fetchall()
        
        return jsonify({
            'waste': {
                'count': waste['count'] or 0,
                'value': round(waste['value'] or 0, 2)
            },
            'by_category': [{'category': row['category'], 'count': row['count'], 'items': row['items']} for row in by_category],
            'top_scanned': [{'name': row['name'], 'count': row['scan_count'], 'last_scanned': row['last_scanned']} for row in top_scanned],
            'weekly_additions': weekly_additions['count'] or 0,
            'avg_by_category': [{'category': row['category'], 'avg_price': round(row['avg_price'], 2)} for row in avg_by_category]
        }), 200
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        init_db()
    else:
        # Run init anyway to check for migrations
        init_db()
    
    # Use 0.0.0.0 to make it accessible in the local network
    app.run(debug=True, host='0.0.0.0', port=5000)
