from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import csv
import json

EMAIL = "monee@gmail.com"
PASSWORD = "12345678"
LOGIN_URL = "https://soft.reelly.io/sign-in"
DATA_URL = "https://find.reelly.io/?pricePer=unit&withDealBonus=false&handoverOnly=false&handoverMonths=1"

# Correctly escaped CSS selector for scroll container
SCROLL_CONTAINER_SELECTOR = "div.overflow-auto.grid.justify-items-center"



def scrape_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(LOGIN_URL)
        time.sleep(2)

        # Login
        page.fill("#email-2", EMAIL)
        page.fill("#field", PASSWORD)
        page.click("a[wized='loginButton']")
        print("Logged in")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Go to "Off-plan"
        page.click("div.div-block-121:has-text('Off-plan')")
        print("Clicked Off-plan")
        time.sleep(5)

        # Check if scroll container exists
        # Use Playwright's safe query selector
        container_element = page.locator(SCROLL_CONTAINER_SELECTOR).first
        if not container_element or container_element.count() == 0:
            print("❌ Scroll container not found. Exiting.")
            browser.close()
            return



        # Scrolling script
        scroll_script = f"""
        () => {{
            const selector = {json.dumps(SCROLL_CONTAINER_SELECTOR)};
            const scrollContainer = document.querySelector(selector);
            if (scrollContainer) {{
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
                return scrollContainer.scrollHeight;
            }} else {{
                return 0;
            }}
        }}
        """

        last_height = 0
        same_height_counter = 0
        max_attempts = 30

        # Scrolling loop
        for i in range(max_attempts):
            height = page.evaluate(scroll_script)
            if height == last_height:
                same_height_counter += 1
            else:
                same_height_counter = 0
                last_height = height

            print(f"Scroll attempt {i+1} - height: {height}")
            time.sleep(2)

            if same_height_counter >= 5:
                print("No more content loading, stopping scroll.")
                break

        # Scrape property cards
        html = page.content()
        soup = BeautifulSoup(html, "lxml")
        property_cards = soup.select("a.outline-none > div.border.bg-card.text-card-foreground")

        properties = []
        seen = set()

        for i, card in enumerate(property_cards, 1):
            title_elem = card.select_one("h4.text-base.text-accent-foreground")
            location_elem = card.select_one("p.text-xs.text-zinc-400")
            price_elem = card.select_one("h5.text-sm.text-accent-foreground")
            presale_info = [span.text.strip() for span in card.select("span.bg-white.text-xs.font-semibold")]

            title = title_elem.text.strip() if title_elem else "N/A"
            location = location_elem.text.strip() if location_elem else "N/A"
            price = price_elem.text.strip() if price_elem else "N/A"
            presale = ', '.join(presale_info)

            key = (title, location, price, presale)
            if key not in seen:
                seen.add(key)
                properties.append([title, location, price, presale])
                print(f"{i}. {title} | {location} | {price} | {presale}")

        # Save to CSV
        with open("properties.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Title", "Location", "Price", "Presale & Year"])
            writer.writerows(properties)

        print(f"✅ Scraped {len(properties)} unique properties.")
        browser.close()

scrape_data()
