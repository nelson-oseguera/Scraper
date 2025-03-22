from flask import Flask, request, jsonify
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

app = Flask(__name__)

def scrape_pricecharting(title, platform):
    formatted_title = title.replace(" ", "-").lower()
    formatted_platform = platform.lower().replace(" ", "-")
    url = f"https://www.pricecharting.com/game/{formatted_platform}/{formatted_title}"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    browser = webdriver.Chrome(options=chrome_options)
    browser.get(url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()

    def extract_price(price_id):
        price_element = soup.select_one(f'td#{price_id} .js-price')
        if price_element:
            price_text = price_element.text.strip().replace('$', '').replace(',', '')
            return float(price_text) if price_text else 0.0
        return 0.0

    loose_price = extract_price("used_price")
    complete_price = extract_price("complete_price")
    new_price = extract_price("new_price")
    box_price = extract_price("box_only_price")
    manual_price = extract_price("manual_only_price")

    image_tag = soup.select_one('img.js-show-dialog')
    image_url = image_tag["src"] if image_tag and 'src' in image_tag.attrs else ""

    upc = ""
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

if __name__ == "__main__":
    app.run()
