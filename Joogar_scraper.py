import pandas as pd
import uuid
import asyncio
import time
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

LOGIN_URL = "https://soft.reelly.io/sign-in"
EMAIL = "monee@gmail.com"
PASSWORD = "12345678"

INPUT_CSV = "links.csv"
OUTPUT_CSV = "output_data.csv"


def is_cyrillic(text):
    """Check if the text contains Cyrillic characters (used in Russian)."""
    return bool(re.search('[\u0400-\u04FF]', text))


async def perform_login(page):
    await page.goto(LOGIN_URL)
    await page.fill("#email-2", EMAIL)
    await page.fill("#field", PASSWORD)
    await page.click("a[wized='loginButton']")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(3)
    print("🔐 Logged in successfully")


async def is_login_page(page):
    try:
        await page.wait_for_selector("#email-2", timeout=3000)
        return True
    except PlaywrightTimeoutError:
        return False


async def scrape_page(page, url):
    try:
        await page.goto(url, timeout=60000)
        if await is_login_page(page):
            print(f"Redirected to login page from {url}, logging in again...")
            await perform_login(page)
            await page.goto(url, timeout=60000)

        await page.wait_for_selector("div.profile-header", timeout=15000)

        data = {
            "UUID": str(uuid.uuid4()),
            "Name": "",
            "Location": "",
            "Launch date": "",
            "Overview": "",
            "Unit Prices": "",
        }

        # Name
        try:
            await page.wait_for_selector(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 div.property-header-name-text",
                timeout=10000,
            )
            name = await page.text_content(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 div.property-header-name-text"
            )
            data["Name"] = name.strip() if name and "Loading" not in name else ""
        except:
            data["Name"] = ""

        # Location
        try:
            await page.wait_for_selector(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 div.property-header-location.new",
                timeout=10000,
            )
            location = await page.text_content(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 div.property-header-location.new"
            )
            data["Location"] = location.strip() if location and "Loading" not in location else ""
        except:
            data["Location"] = ""

        # Launch Date
        try:
            launch_date = await page.text_content(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 > div.profile-header > div.proparties-info-block._1 > div.property-header-text-block > div.data-block-project > div:nth-child(4)"
            )
            data["Launch date"] = launch_date.strip() if launch_date else ""
        except:
            data["Launch date"] = ""

        # Overview (combine all text inside the block, filter Russian)
        try:
            overview_container = await page.query_selector(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 > div.general-block.no-indentation > div:nth-child(3) > div > div.description_block._1"
            )
            if overview_container:
                paragraphs = await overview_container.query_selector_all("p, h5")
                texts = [await p.text_content() for p in paragraphs]
                cleaned_texts = [
                    t.strip() for t in texts if t and t.strip() and not is_cyrillic(t)
                ]
                data["Overview"] = "\n".join(cleaned_texts)
        except:
            data["Overview"] = ""

        # Unit Prices (simplified selector)
        try:
            await page.wait_for_selector(
                "#w-node-_24757de1-7ffc-051c-df3f-7ae59d75423e-12f38d96 div.project-info-test > div:nth-child(2) > h2",
                timeout=10000,
            )
            price = await page.text_content(
                "#w-node-_24757de1-7ffc-051c-df3f-7ae59d75423e-12f38d96 div.project-info-test > div:nth-child(2) > h2"
            )
            price_cleaned = price.strip() if price else ""
            if "Loading" in price_cleaned or not price_cleaned:
                data["Unit Prices"] = ""
            else:
                data["Unit Prices"] = f"Starting from: {price_cleaned}"
        except:
            data["Unit Prices"] = ""

        # Developer
        try:
            developer = await page.text_content(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 > div.profile-header > div.proparties-info-block._1 > div.back-company-agent-block > div > div"
            )
            data["Developer"] = developer.strip() if developer else ""
        except:
            pass

                # Detailed Pricing
        try:
            container = await page.query_selector(
                "#w-node-_252af881-6ac8-1fe9-c411-e949de04b7da-12f38d96 > div.general-block.no-indentation > div.right-slider-section > div > div.typical-units-block"
            )
            if container:
                cards = await container.query_selector_all("div.name_buildings_block")
                detailed_pricing = []

                for card in cards:
                    try:
                        unit_types = await card.query_selector_all(".unit-type")
                        unit_type_text = " - ".join([
                            await ut.text_content() for ut in unit_types if await ut.text_content()
                        ])

                        # Price
                        price_box = await card.query_selector(".price-range-box")
                        if price_box:
                            prices = await price_box.query_selector_all(".unit-price")
                            price_text = " — ".join([
                                await p.text_content() for p in prices if await p.text_content()
                            ])
                        else:
                            price_text = ""

                        # Area (sqft)
                        area_box = await card.query_selector(".unit-area-range-box")
                        if area_box:
                            areas = await area_box.query_selector_all(".unit-area")
                            area_text = " — ".join([
                                await a.text_content() for a in areas if await a.text_content()
                            ])
                        else:
                            area_text = ""

                        detailed_pricing.append({
                            "Unit Type": unit_type_text,
                            "Price (AED)": price_text,
                            "Area (sqft)": area_text
                        })
                    except:
                        continue

                data["Detailed Pricing"] = detailed_pricing
        except Exception as e:
            print(f"⚠️ Error scraping detailed pricing: {e}")
            data["Detailed Pricing"] = []


        return data

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return None


async def main():
    df = pd.read_csv(INPUT_CSV)
    urls = df.iloc[:, 0].dropna().tolist()
    urls = urls[:5]  # Only first 5 links
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await perform_login(page)

        for i, url in enumerate(urls):
            print(f"🔍 Scraping {i+1}/{len(urls)}: {url}")
            data = await scrape_page(page, url)
            if data:
                results.append(data)

        await browser.close()

    result_df = pd.DataFrame(results)
    result_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved {len(results)} records to {OUTPUT_CSV}")


if __name__ == "__main__":
    asyncio.run(main())