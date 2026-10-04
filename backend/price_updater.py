from decimal import Decimal
from database import get_connection
import scraper as scraper
from notifications import send_price_alert


def price_refresher():
    """Refreshes current prices of all products in the database."""
    try:
        select_query = "SELECT product_url from products;"
        check_query = "SELECT current_price from products WHERE product_url = %s;"
        update_query = "UPDATE products SET current_price = %s WHERE product_url = %s;"
        add_history_query = "INSERT INTO price_history (history_pid, recorded_price) VALUES ((SELECT product_id from products WHERE product_url = %s), %s)"
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(select_query)
                urls_list = cur.fetchall()

                for (product_urls, ) in urls_list:
                    new_price = scraper.return_dict(product_urls)["product_price"]
                    cur.execute(check_query, (product_urls,))
                    old_price = Decimal(cur.fetchone()[0])
                    if new_price != old_price:
                        cur.execute(update_query, (new_price, product_urls))
                        print(f"Price updated for {product_urls}")
                    # Always store a price snapshot for charting, even when price is unchanged.
                    cur.execute(add_history_query, (product_urls, new_price))
                    conn.commit()
    except Exception as e:
        print(f"Error in price_refresher: {e}")
        raise


def check_and_notify_targets():
    """Check for products that hit target prices and notify users."""
    try:
        query = """
        SELECT u.email, p.product_url, p.current_price, ut.target_price, p.product_name, ut.userprofileid, ut.usersitemid
        FROM usertrackeditems ut
        JOIN products p ON ut.usersitemid = p.product_id
        JOIN accounts u ON ut.userprofileid = u.user_id
        WHERE p.current_price <= ut.target_price AND ut.notified = FALSE;
        """
        
        update_query = "UPDATE usertrackeditems SET notified = TRUE WHERE userprofileid = %s AND usersitemid = %s;"
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()
                
                for email, product_url, current_price, target_price, product_name, userprofileid, usersitemid in results:
                    if not send_price_alert(email, product_name, target_price, current_price):
                        # Leave notified = FALSE so the next run retries this alert.
                        continue
                    
                    cur.execute(update_query, (userprofileid, usersitemid))
                    conn.commit()
                    print(f"Notification sent to {email} for {product_name}")
    except Exception as e:
        print(f"Error in check_and_notify_targets: {e}")
        raise


def reset_notified_prices():
    """Reset notified flag if price went up above target."""
    try:
        query = """
        UPDATE usertrackeditems SET notified = FALSE WHERE notified = TRUE 
        AND target_price < (
            SELECT current_price FROM products 
            WHERE products.product_id = usertrackeditems.usersitemid
        );
        """
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                conn.commit()
                print(f"Reset {cur.rowcount} items")
    except Exception as e:
        print(f"Error in reset_notified_prices: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    jobs = {
        "price_refresher": price_refresher,
        "check_and_notify_targets": check_and_notify_targets,
        "reset_notified_prices": reset_notified_prices,
    }
    
    if len(sys.argv) < 2:
        print("Usage: python price_updater.py <job_name>")
        print(f"Available jobs: {', '.join(jobs.keys())}")
        sys.exit(1)
    
    job_name = sys.argv[1]
    
    if job_name in jobs:
        jobs[job_name]()
    else:
        print(f"Unknown job: {job_name}")
        sys.exit(1)
