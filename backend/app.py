# app.py
import os
import re
from flask import Flask, jsonify, session, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from auth import login_user, register_user
from database import insert_user_products, get_connection, get_price_graph_data
import scraper as scraper


app = Flask(__name__)
_secret_key = os.getenv("FLASK_KEY")

if not _secret_key:
    raise RuntimeError("FLASK_KEY environment variable is not set")

app.secret_key = _secret_key
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
CORS(app, resources={r"/*": {"origins": [_frontend_url]}}, supports_credentials=True)
 

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=_redis_url,
    default_limits=["200 per day", "50 per hour"],
)


def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


ALLOWED_DOMAINS = {'www.yonex.com', 'yonex.com', 'us.yonex.com'}


def is_valid_url(url):
    """Validate URL format and restrict to allowed domains to prevent SSRF."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and parsed.hostname in ALLOWED_DOMAINS
    except Exception:
        return False


@app.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    # Validate required fields
    if 'username' not in request.form or not request.form['username'].strip():
        return jsonify({"error": "Username is required"}), 400
    if 'email' not in request.form or not request.form['email'].strip():
        return jsonify({"error": "Email is required"}), 400
    if 'password' not in request.form or not request.form['password'].strip():
        return jsonify({"error": "Password is required"}), 400
    
    username = request.form['username'].strip()
    email = request.form['email'].strip()
    password = request.form['password']
    
    # Validate username length
    if len(username) < 3 or len(username) > 50:
        return jsonify({"error": "Username must be between 3 and 50 characters"}), 400
    
    # Validate email format
    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    
    # Validate password strength
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    try:
        user_id = register_user(username, password, email)
        session['user_id'] = user_id
        return jsonify({"message": "Registration successful"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    # Validate required fields
    if 'username' not in request.form or not request.form['username'].strip():
        return jsonify({"error": "Username is required"}), 400
    if 'password' not in request.form or not request.form['password'].strip():
        return jsonify({"error": "Password is required"}), 400
    
    username = request.form['username'].strip()
    password = request.form['password']
    
    try:
        user_id = login_user(username, password)
        session['user_id'] = user_id
        return jsonify({"message": "Login successful"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401


@app.route('/add_product', methods=['POST'])
@limiter.limit("10 per minute")
def add_product():
    query1 = """
    UPDATE usertrackeditems SET notified = FALSE WHERE usersitemid = %s;
    """

    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    # Validate required fields
    if 'product_url' not in request.form or not request.form['product_url'].strip():
        return jsonify({"error": "Product URL is required"}), 400
    if 'target_price' not in request.form or not request.form['target_price'].strip():
        return jsonify({"error": "Target price is required"}), 400
    
    product_url = request.form['product_url'].strip()
    
    # Validate URL format
    if not is_valid_url(product_url):
        return jsonify({"error": "Invalid URL format. URL must start with http:// or https://"}), 400
    
    # Validate target price is a valid number
    try:
        target_price = float(request.form['target_price'])
    except ValueError:
        return jsonify({"error": "Target price must be a valid number"}), 400
    
    # Validate target price is positive
    if target_price <= 0:
        return jsonify({"error": "Target price must be greater than 0"}), 400

    product = scraper.return_dict(product_url)
    print(product)
    current_price = product["product_price"]

    if target_price >= current_price:
        return jsonify({"error": "Target price must be less than current price"}), 400

    usersitemid = insert_user_products(user_id, product_url, target_price)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query1, (usersitemid,))
            conn.commit()

    return jsonify({"message": "Product added successfully"}), 200


@app.route('/delete_product', methods=['POST'])
def delete_product():
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    # Get the product ID from the request
    if 'product_id' not in request.form:
        return jsonify({"error": "Product ID is required"}), 400
    
    try:
        product_id = int(request.form['product_id'])
    except ValueError:
        return jsonify({"error": "Invalid product ID"}), 400
    
    # Verify the product belongs to the user before deleting
    query_verify = """
    SELECT 1 FROM usertrackeditems 
    WHERE usersitemid = %s AND userprofileid = %s;
    """
    
    query_delete = "DELETE FROM usertrackeditems WHERE usersitemid = %s;"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute(query_verify, (product_id, user_id))
            if not cur.fetchone():
                return jsonify({"error": "Product not found or unauthorized"}), 403
            
            # Delete the product
            cur.execute(query_delete, (product_id,))
            conn.commit()
    
    return jsonify({"message": "Product deleted successfully"}), 200


@app.route('/dashboard', methods=['GET'])
def dashboard():
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    # Query database for user's products
    query = """
    SELECT ut.usersitemid, p.product_name, p.current_price, ut.target_price
    FROM usertrackeditems ut
    JOIN products p ON ut.usersitemid = p.product_id
    WHERE ut.userprofileid = %s
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            products = cur.fetchall()
    
    return jsonify({"products": products}), 200


@app.route('/price_graph', methods=['GET'])
def price_graph():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    product_id = request.args.get('product_id')

    if not product_id:
        return jsonify({"error": "Product ID is required"}), 400

    try:
        product_id = int(product_id)
    except ValueError:
        return jsonify({"error": "Invalid product ID"}), 400

    # Verify the product belongs to this user before returning data
    query_verify = "SELECT 1 FROM usertrackeditems WHERE usersitemid = %s AND userprofileid = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query_verify, (product_id, user_id))
            if not cur.fetchone():
                return jsonify({"error": "Product not found or unauthorized"}), 403

    points = get_price_graph_data(product_id)

    return jsonify({"data": points})