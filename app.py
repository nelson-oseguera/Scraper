from flask import Flask, request, jsonify
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

app = Flask(__name__)

def configure_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=chrome_options)

def extract_price(soup, price_id):
    price_element = soup.select_one(f'td#{price_id} .js-price')
    if price_element:
        price_text = price_element.text.strip().replace('$', '').replace(',', '')
        if price_text == "-" or not price_text.replace('.', '', 1).isdigit():
            return 0.0
        return float(price_text)
    return 0.0

def extract_game_info(soup, upc=""):
    # Clean title
    title_tag = soup.find("h1", id="product_name")
    title = title_tag.contents[0].strip() if title_tag else "Unknown"

    # Platform from inner <a> tag
    platform_tag = soup.select_one("h1 a[href^='/console/']")
    platform = platform_tag.text.strip() if platform_tag else "Unknown"

    # Prices
    loose_price = extract_price(soup, "used_price")
    complete_price = extract_price(soup, "complete_price")
    new_price = extract_price(soup, "new_price")
    box_price = extract_price(soup, "box_only_price")
    manual_price = extract_price(soup, "manual_only_price")

    # Image
    image_tag = soup.select_one('img.js-show-dialog')
    image_url = image_tag["src"] if image_tag and 'src' in image_tag.attrs else ""

    # UPC (if empty, try to scrape)
    if not upc:
        upc_label = soup.find("td", class_="title", string="UPC:")
        if upc_label:
            upc_value = upc_label.find_next_sibling("td", class_="details")
            if upc_value:
                upc = upc_value.text.strip()

    return {
        "title": title,
        "platform": platform,
        "loose_price": loose_price,
        "complete_price": complete_price,
        "new_price": new_price,
        "manual_price": manual_price,
        "box_price": box_price,
        "image_url": image_url,
        "upc": upc
    }

def scrape_pricecharting(title, platform):
    formatted_title = title.replace(" ", "-").lower()
    formatted_platform = platform.lower().replace(" ", "-")
    url = f"https://www.pricecharting.com/game/{formatted_platform}/{formatted_title}"

    browser = configure_browser()
    browser.get(url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()

    return extract_game_info(soup)

def scrape_pricecharting_by_upc(upc):
    search_url = f"https://www.pricecharting.com/search-products?type=videogames&q={upc}"

    browser = configure_browser()
    browser.get(search_url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    link_tag = soup.select_one("a[href*='/game/']")
    if not link_tag:
        browser.quit()
        return {"error": f"No game found for UPC {upc}"}

    game_url = "https://www.pricecharting.com" + link_tag["href"]
    browser.get(game_url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()

    return extract_game_info(soup, upc=upc)

@app.route("/scrape", methods=["GET"])
def scrape():
    title = request.args.get("title")
    platform = request.args.get("platform")
    if not title or not platform:
        return jsonify({"error": "Missing title or platform"}), 400

    try:
        data = scrape_pricecharting(title, platform)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/scrape-upc", methods=["GET"])
def scrape_upc():
    upc = request.args.get("upc")
    if not upc:
        return jsonify({"error": "Missing UPC"}), 400

    try:
        data = scrape_pricecharting_by_upc(upc)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()
