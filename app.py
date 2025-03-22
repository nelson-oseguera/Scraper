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

def extract_upc(soup):
    upc_label = soup.find("td", class_="title", string="UPC:")
    if upc_label:
        upc_value = upc_label.find_next_sibling("td", class_="details")
        if upc_value:
            return upc_value.text.strip()
    return ""

def extract_game_data(soup, upc=""):
    title = "Unknown"
    platform = "Unknown"

    page_title = soup.title.string if soup.title else ""
    match = re.search(r'(.+?)\s+\((.+?)\)', page_title)
    if match:
        title = match.group(1).strip()
        platform = match.group(2).strip()

    loose_price = extract_price(soup, "used_price")
    complete_price = extract_price(soup, "complete_price")
    new_price = extract_price(soup, "new_price")
    box_price = extract_price(soup, "box_only_price")
    manual_price = extract_price(soup, "manual_only_price")

    image_tag = soup.select_one('img.js-show-dialog')
    image_url = image_tag["src"] if image_tag and 'src' in image_tag.attrs else ""

    extracted_upc = extract_upc(soup)

    return {
        "title": title,
        "platform": platform,
        "loose_price": loose_price,
        "complete_price": complete_price,
        "new_price": new_price,
        "manual_price": manual_price,
        "box_price": box_price,
        "image_url": image_url,
        "upc": extracted_upc or upc
    }

def scrape_pricecharting_by_upc(target_upc):
    search_url = f"https://www.pricecharting.com/search-products?type=videogames&q={target_upc}"

    browser = configure_browser()
    browser.get(search_url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    game_links = soup.select("a[href*='/game/']")
    checked_urls = []

    for link in game_links:
        href = link.get("href")
        if not href:
            continue

        full_url = "https://www.pricecharting.com" + href
        if full_url in checked_urls:
            continue

        checked_urls.append(full_url)
        browser.get(full_url)
        time.sleep(2)
        game_soup = BeautifulSoup(browser.page_source, 'html.parser')
        extracted_upc = extract_upc(game_soup)

        if extracted_upc == target_upc:
            browser.quit()
            return extract_game_data(game_soup, extracted_upc)

    browser.quit()
    return {"error": f"No exact game match found for UPC {target_upc}"}

def scrape_pricecharting(title, platform):
    formatted_title = title.replace(" ", "-").lower()
    formatted_platform = platform.lower().replace(" ", "-")
    url = f"https://www.pricecharting.com/game/{formatted_platform}/{formatted_title}"

    browser = configure_browser()
    browser.get(url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, 'html.parser')
    browser.quit()

    return extract_game_data(soup)

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
