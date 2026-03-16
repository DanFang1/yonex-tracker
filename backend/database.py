import psycopg2
from psycopg2 import sql, IntegrityError
from dotenv import load_dotenv  
import os
import scraper as scraper

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


def insert_user_products(user_id, product_url, target_price):
    """""Inserts a new product into the products table based on product URL, then links to user.
    Uses INSERT...ON CONFLICT to safely handle multiple concurrent processes."""
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # Fetch product data
                product = scraper.return_dict(product_url)
                
                # Insert product if new; if it already exists, reuse existing product_id.
                # Keep current_price fresh on existing rows.
                insert_product_query = sql.SQL(
                    """
                    INSERT INTO products (product_url, product_name, current_price)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (product_url)
                    DO NOTHING
                    RETURNING product_id;
                    """
                )
                cur.execute(insert_product_query, (product["product_url"], product["product_name"], product["product_price"]))
                inserted_row = cur.fetchone()

                if inserted_row:
                    product_id = inserted_row[0]
                    is_new_product = True
                else:
                    is_new_product = False
                    cur.execute("SELECT product_id FROM products WHERE product_url = %s", (product["product_url"],))
                    product_id = cur.fetchone()[0]
                    cur.execute("UPDATE products SET current_price = %s WHERE product_id = %s", (product["product_price"], product_id))
                conn.commit()
                print(f"Product ensured with ID: {product_id}")
                
                # Insert into usertrackeditems (ON CONFLICT handles duplicate user-product pairs)
                user_tracking_query = sql.SQL(
                    """
                    INSERT INTO usertrackeditems (usersitemid, userprofileid, target_price)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (usersitemid, userprofileid) 
                    DO UPDATE SET target_price = EXCLUDED.target_price
                    RETURNING usersitemid;
                    """
                )
                cur.execute(user_tracking_query, (product_id, user_id, target_price))
                user_item_id = cur.fetchone()[0]
                conn.commit()
                print(f"User item upserted for user {user_id}")

                # Insert initial price snapshot only when this product is first created.
                if is_new_product:
                    price_history_query = sql.SQL(
                        """
                        INSERT INTO price_history (history_pid, recorded_price)
                        VALUES (%s, %s)
                        """
                    )
                    cur.execute(price_history_query, (product_id, product["product_price"]))
                    conn.commit()
                
                return user_item_id
                
            except IntegrityError as e:
                conn.rollback()
                print(f"Error inserting product: {e}")
                return None


def get_price_graph_data(product_id):
    """Return time-series points for a product's historical and current price."""
    query = """
        SELECT time_change AS t, recorded_price AS price
        FROM price_history
        WHERE history_pid = %s
        UNION ALL
        SELECT NOW() AS t, current_price AS price
        FROM products
        WHERE product_id = %s
        ORDER BY t ASC
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (product_id, product_id))
            rows = cur.fetchall()

    return [
        {"date": row[0].isoformat(), "price": float(row[1])}
        for row in rows
    ]


def check_connection() -> bool:
    "Checks if database connection is successful"
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                print("Database successfully connected.")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
                
print(check_connection())