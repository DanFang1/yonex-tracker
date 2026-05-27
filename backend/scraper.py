from decimal import Decimal
from bs4 import BeautifulSoup
import requests
import re

price_selector = "span.price-item.price-item--regular"
item_selector = ".product__title h1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def find_products(soup):
    price_element = soup.select_one(price_selector)
    item_element = soup.select_one(item_selector)

    if not price_element or not item_element:
        raise ValueError("Price or item element not found. Please insert different URL.")

    price_clean = re.sub(r'[^\d\.]', '', price_element.get_text().strip())
    price_value = Decimal(price_clean)
    item_name = item_element.get_text().strip()

    return {"product_name": item_name, "product_price": price_value}

def return_dict(url):
    try:
        response = requests.get(url.strip(), headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        product = find_products(soup)
        product["product_url"] = url.strip()
        print(product)
        return product
    except ValueError:
        raise
    except Exception as e:
        print("Error:", e)
        raise ValueError(f"Failed to scrape product: {e}")
