import psycopg2
from psycopg2 import sql, IntegrityError
from dotenv import load_dotenv  
import os
load_dotenv()


def get_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))


def insert_user_products(user_id, product, target_price):
    """""Inserts a new product into the products table based on product URL, then links to user.
    Uses INSERT...ON CONFLICT to safely handle multiple concurrent processes."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            try:

                # Insert product if URL and name are both new; otherwise reuse existing row.
                insert_product_query = sql.SQL(
                    """
                    INSERT INTO products (product_url, product_name, current_price)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING product_id;
                    """
                )
                cur.execute(insert_product_query, (product["product_url"], product["product_name"], product["product_price"]))
                row = cur.fetchone()
                if row is None:
                    # Product already exists — look up its id to still link the user.
                    cur.execute(
                        "SELECT product_id FROM products WHERE product_url = %s OR product_name = %s",
                        (product["product_url"], product["product_name"])
                    )
                    existing = cur.fetchone()
                    if existing is None:
                        print("Could not find existing product. Skipping.")
                        return None
                    product_id = existing[0]
                    is_new_product = False
                    print(f"Product already exists with ID: {product_id}")
                else:
                    product_id = row[0]
                    is_new_product = True
                    conn.commit()
                    print(f"Product inserted with ID: {product_id}")

                # Link product to user; if already tracked by this user, do nothing.
                user_tracking_query = sql.SQL(
                    """
                    INSERT INTO usertrackeditems (usersitemid, userprofileid, target_price)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (usersitemid, userprofileid)
                    DO NOTHING
                    RETURNING usersitemid;
                    """
                )
                cur.execute(user_tracking_query, (product_id, user_id, target_price))
                user_row = cur.fetchone()
                if user_row is None:
                    print(f"Item has already been added for user {user_id}.")
                    return None
                user_item_id = user_row[0]
                conn.commit()
                print(f"User item added for user {user_id}")

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
        {"date": row[0].strftime("%m/%d/%Y"), "price": float(row[1])}
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
                
