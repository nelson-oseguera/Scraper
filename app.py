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

def scrape_pricecharting(title, platform):
    formatted_title = title.replace(" ", "-").lower()
    formatted_platform = platform.lower().replace(" ", "-")
    url = f"https://www.pricecharting.com/game/{formatted_platform}/{formatted_title}"

    browser = configure_browser()
    browser.get(url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()

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

def scrape_pricecharting_by_upc(upc):
    search_url = f"https://www.pricecharting.com/search-products?type=videogames&q={upc}"

    browser = configure_browser()
    browser.get(search_url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()

    # Step 1: Look through all rows in the search results
    rows = soup.select("table#products_table tr")

    exact_link = None

    for row in rows:
        upc_cell = row.find("td", string="UPC:")
        if upc_cell:
            upc_value_cell = upc_cell.find_next_sibling("td")
            if upc_value_cell and upc_value_cell.text.strip() == upc:
                link = row.find("a", href=True)
                if link:
                    exact_link = "https://www.pricecharting.com" + link["href"]
                    break

        # Alternate check: Sometimes UPC is inside the link's data-upc attribute (less common)
        link_tag = row.find("a", href=True)
        if link_tag and upc in link_tag.get("href", ""):
            exact_link = "https://www.pricecharting.com" + link_tag["href"]
            break

    if not exact_link:
        return {"error": f"No exact game match found for UPC {upc}"}

    # Step 2: Load the exact matching game page
    browser = configure_browser()
    browser.get(exact_link)
    time.sleep(3)
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()

    # Step 3: Parse details like title, platform, and prices
    page_title = soup.title.string if soup.title else ""
    match = re.search(r'^(.*?)\s+Prices\s+(.*?)\s+\|', page_title)
    title = match.group(1).strip() if match else "Unknown"
    platform = match.group(2).strip() if match else "Unknown"

    loose_price = extract_price(soup, "used_price")
    complete_price = extract_price(soup, "complete_price")
    new_price = extract_price(soup, "new_price")
    box_price = extract_price(soup, "box_only_price")
    manual_price = extract_price(soup, "manual_only_price")

    image_tag = soup.select_one('img.js-show-dialog')
    image_url = image_tag["src"] if image_tag and 'src' in image_tag.attrs else ""

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
