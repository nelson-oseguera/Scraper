from flask import Flask, request, jsonify
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

app = Flask(__name__)

def configure_browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)

def extract_price(soup, price_id):
    price_element = soup.select_one(f'td#{price_id} .js-price')
    if price_element:
        price_text = price_element.text.strip().replace('$', '').replace(',', '')
        return float(price_text) if price_text.replace('.', '', 1).isdigit() else 0.0
    return 0.0

def extract_game_data(soup):
    loose_price = extract_price(soup, "used_price")
    complete_price = extract_price(soup, "complete_price")
    new_price = extract_price(soup, "new_price")
    box_price = extract_price(soup, "box_only_price")
    manual_price = extract_price(soup, "manual_only_price")

    image_tag = soup.select_one('img.js-show-dialog')
    image_url = image_tag["src"] if image_tag and 'src' in image_tag.attrs else ""

    upc = ""
    upc_label = soup.find("td", class_="title", string="UPC:")
    if upc_label:
        upc_value = upc_label.find_next_sibling("td", class_="details")
        if upc_value:
            upc = upc_value.text.strip()

    title = soup.find("h1", id="product_name")
    title_text = title.text.strip() if title else "Unknown"

    platform_tag = soup.select_one("a[href^='/console/']")
    platform = platform_tag.text.strip() if platform_tag else "Unknown"

    return {
        "title": title_text,
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
        formatted_title = title.replace(" ", "-").lower()
        formatted_platform = platform.lower().replace(" ", "-")
        url = f"https://www.pricecharting.com/game/{formatted_platform}/{formatted_title}"

        browser = configure_browser()
        browser.get(url)
        time.sleep(3)
        soup = BeautifulSoup(browser.page_source, 'html.parser')
        browser.quit()

        return jsonify(extract_game_data(soup))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/scrape-upc", methods=["GET"])
def scrape_upc():
    upc = request.args.get("upc")
    if not upc:
        return jsonify({"error": "Missing UPC"}), 400

    try:
        url = f"https://www.pricecharting.com/search-products?type=videogames&q={upc}"

        browser = configure_browser()
        browser.get(url)
        time.sleep(3)

        # Automatically redirected to the game page? If not, extract and follow
        if "/search-products?" in browser.current_url:
            link_tag = BeautifulSoup(browser.page_source, "html.parser").select_one("a[href^='/game/']")
            if not link_tag:
                browser.quit()
                return jsonify({"error": f"No game found for UPC {upc}"}), 404
            game_url = "https://www.pricecharting.com" + link_tag["href"]
            browser.get(game_url)
            time.sleep(3)

        soup = BeautifulSoup(browser.page_source, "html.parser")
        browser.quit()

        return jsonify(extract_game_data(soup))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()
