from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import csv

EMAIL = "monee@gmail.com"
PASSWORD = "12345678"
LOGIN_URL = "https://soft.reelly.io/sign-in"
DATA_URL = "https://find.reelly.io/?pricePer=unit&withDealBonus=false&handoverOnly=false&handoverMonths=1"

def scrape_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Step 1: Go to Login Page
        page.goto(LOGIN_URL)
        time.sleep(2)

        # Step 2: Fill Login Form
        page.fill("#email-2", EMAIL)
        page.fill("#field", PASSWORD)  # Confirm ID of password field
        page.click("a[wized='loginButton']")
        print("Logged in")

        # Step 3: Wait for login to complete
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Step 4: Click the Off-Plan button
        page.click("div.div-block-121:has-text('Off-plan')")
        print("Clicked Off-plan")

        # Step 5: Wait for the page to load
        time.sleep(5)

        # Step 6: Scrape all Property Cards
        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        # Find all property cards
        property_cards = soup.select("a.outline-none > div.border.bg-card.text-card-foreground")  # Adjust to actual structure

        # Store the scraped data in a list
        properties = []

        for card in property_cards:
            title = card.select_one("h4.text-base.text-accent-foreground").text.strip() if card.select_one("h4.text-base.text-accent-foreground") else "N/A"
            location = card.select_one("p.text-xs.text-zinc-400").text.strip() if card.select_one("p.text-xs.text-zinc-400") else "N/A"
            price = card.select_one("h5.text-sm.text-accent-foreground").text.strip() if card.select_one("h5.text-sm.text-accent-foreground") else "N/A"
            presale_info = [span.text.strip() for span in card.select("span.bg-white.text-xs.font-semibold")]  # Extract Presale & Year info

            # Add the scraped data to the list
            properties.append([title, location, price, ', '.join(presale_info)])

        # Step 7: Save the data to CSV (optional)
        with open("properties.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Title", "Location", "Price", "Presale & Year"])
            writer.writerows(properties)

        print("Data saved to properties.csv")
        browser.close()

scrape_data()
