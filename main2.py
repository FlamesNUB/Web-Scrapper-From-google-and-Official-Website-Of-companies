import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
import time
import os


def scrape_google_news_links(company_name, start_date, end_date, max_pages):
    print(f"\n🔄 Starting scraping for: {company_name}")
    options = uc.ChromeOptions()
    options.headless = False
    options.add_argument("--disable-gpu")
    options.add_argument("--blink-settings=imagesEnabled=false")
    driver = uc.Chrome(options=options)
    driver.get(f"https://www.google.com/search?q={company_name.replace('_', ' ')}&tbm=nws&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}")

    try:
        WebDriverWait(driver, 7).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Accept') or contains(text(),'I agree')]"))).click()
        print("✅ Cookie popup accepted.")
    except TimeoutException:
        print("ℹ️ No cookie popup detected.")

    links = []
    seen = set()
    page = 1
    while page <= max_pages:
        try:
            if "detected unusual traffic" in driver.page_source:
                print("🛑 CAPTCHA detected! Stopping scraping for this company.")
                break

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            WebDriverWait(driver, 7).until(EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, 'http')]")))
            results = driver.find_elements(By.XPATH, "//a[contains(@href, 'http')]")

            for result in results:
                href = result.get_attribute("href")
                if href and "google.com" not in href and href not in seen:
                    links.append(href)
                    seen.add(href)

            print(f"📄 Page {page} — Total Links: {len(links)}")

            try:
                WebDriverWait(driver, 7).until(EC.element_to_be_clickable((By.LINK_TEXT, "Next"))).click()
                time.sleep(1.5)
            except:
                print("ℹ️ No more pages. Stopping pagination.")
                break

            page += 1
        except Exception as e:
            print(f"⚠️ Error on page {page}: {e}")
            break

    driver.quit()
    return links


def main():
    company_ids = [company.strip() for company in input("Enter company IDs (comma-separated): ").split(",") if company.strip()]
    start_date, end_date = input("Enter start date (MM-DD-YYYY): "), input("Enter end date (MM-DD-YYYY): ")

    # Create output folder with today’s date
    today_folder = datetime.now().strftime("%Y-%m-%d") + "_output"
    os.makedirs(today_folder, exist_ok=True)
    print(f"\n📁 Output folder: {today_folder}")

    for company_id in company_ids:
        print(f"\n🚀 Processing company: {company_id}")
        print("--------------------------------------------")
        links = scrape_google_news_links(company_id, start_date, end_date, max_pages=20)
        if links:
            data = [{"Company_ID": company_id, "Link": link} for link in links]
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"filtered_news_links_{company_id}_{start_date}to{end_date}_{timestamp}.xlsx"
            filepath = os.path.join(today_folder, filename)
            pd.DataFrame(data).to_excel(filepath, index=False)
            print(f"💾 Saved {len(links)} links for {company_id} to:\n    {filepath}")
        else:
            print(f"⚠ No links found for {company_id}")
        print("--------------------------------------------")

if __name__ == "__main__":
    main()
