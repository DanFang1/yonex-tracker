from decimal import Decimal
from playwright.sync_api import sync_playwright, TimeoutError
import re

price_selector = "span.price-item.price-item--regular"
item_selector = ".product__title h1"

def find_products(page):
    """ scrape product name and price from a given URL """
    price_element = page.query_selector(price_selector)
    item_element = page.query_selector(item_selector)

    if not price_element or not item_element:
        raise ValueError("Price or item element not found. Please insert different URL.")
    else:
        price_element = price_element.inner_text().strip()
        price_clean = re.sub(r'[^\d\.]', '', price_element)
        price_value = Decimal(price_clean)
        item_element = item_element.inner_text().strip()
    
    return {"product_name": item_element, "product_price": price_value}

def return_dict(url):
    """ return product name, price and, url as a dictionary"""
    with sync_playwright() as p:
        browser= p.chromium.launch(headless=True).new_page()
        
        try:
            browser.goto(url.strip())
            browser.wait_for_timeout(5000)
            product = find_products(browser)
            product["product_url"] = url.strip()
            print(product)
            return product
        except Exception as e:
            print("Error:", e)
            raise ValueError(f"Failed to scrape product: {e}")
        finally:
            browser.close()
            