import sys
import pandas as pd
from urllib.parse import urljoin
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
from datetime import datetime
from htmldate import find_date

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.setBlockedURLs", {
        "urls": [".jpg", ".jpeg", ".png", ".gif", ".css", ".woff", ".svg", ".mp4", ".webm", ".avi"]
    })
    driver.set_page_load_timeout(30)
    return driver

def scrape(company_ids, start_date, end_date, timeout=15):
    df = pd.read_excel('official.xlsx')
    filtered_df = df[df['company_id'].isin(company_ids)]

    if filtered_df.empty:
        logger.error("No matching company IDs found in the Excel file.")
        return

    driver = setup_driver()
    output_rows = []

    logger.info("Scraping Started\n")
    for company_id in tqdm(company_ids, desc="Processing companies"):
        company_row = filtered_df[filtered_df['company_id'] == company_id]

        if company_row.empty or pd.isna(company_row.iloc[0]['base_url']):
            output_rows.append({'company_id': company_id, 'link': 'news path not available', 'date': ''})
            continue

        base_url = company_row.iloc[0]['base_url']
        logger.info(f"Scraping for: {company_id}")
        visited_links = set()

        try:
            current_url = base_url
            for page_num in range(2):
                try:
                    driver.get(current_url)
                    WebDriverWait(driver, timeout).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                    news_elements = driver.find_elements(By.CSS_SELECTOR, "article a, .news-item a, li.article a")
                    if not news_elements:
                        news_elements = driver.find_elements(By.TAG_NAME, "a")
                except Exception as e:
                    logger.warning(f"Page load or element timeout on {current_url}: {e}")
                    break

                for elem in news_elements:
                    link = elem.get_attribute("href")
                    if link and base_url in link and link not in visited_links:
                        visited_links.add(link)
                        try:
                            date = find_date(link)
                        except Exception:
                            date = ""
                        output_rows.append({'company_id': company_id, 'link': link, 'date': date})
                        logger.info(f"Captured: {link} | Date: {date if date else 'N/A'}")

                # Pagination
                try:
                    next_elem = driver.find_element(By.CSS_SELECTOR, 'a[rel="next"], a.next, li.next a')
                    current_url = urljoin(current_url, next_elem.get_attribute("href"))
                except:
                    try:
                        next_elem = driver.find_element(By.PARTIAL_LINK_TEXT, 'Next')
                        current_url = urljoin(current_url, next_elem.get_attribute("href"))
                    except:
                        break

            if not visited_links:
                output_rows.append({'company_id': company_id, 'link': 'no news found', 'date': ''})

        except Exception as e:
            logger.error(f"Error scraping {base_url}: {e}")
            output_rows.append({'company_id': company_id, 'link': 'no news found', 'date': ''})

    driver.quit()

    # Filter by date
    total_scraped = len(output_rows)
    filtered_rows = []
    valid_date_count = 0
    out_of_range_count = 0

    for row in output_rows:
        date_str = row['date']
        if not date_str:
            continue
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            if start_date <= parsed_date <= end_date:
                filtered_rows.append(row)
                valid_date_count += 1
            else:
                out_of_range_count += 1
        except:
            continue

    final_df = pd.DataFrame(filtered_rows, columns=['company_id', 'link', 'date'])
    timestamp = datetime.now().strftime("%H%M%S")
    output_filename = f"scraped_links_with_dates_{timestamp}.xlsx"
    final_df.to_excel(output_filename, index=False)

    logger.info("\nScraping Summary:")
    logger.info(f"Total links scraped: {total_scraped}")
    logger.info(f"Links with valid dates in range: {valid_date_count}")
    logger.info(f"Links out of range: {out_of_range_count}")
    logger.info(f"Final links saved to Excel: {len(filtered_rows)}")
    logger.info(f"Output saved to: {output_filename}")

if __name__ == '__main__':
    companies_input = input("Enter comma-separated company_ids (e.g. apple_inc,amd): ")
    try:
        company_ids = [x.strip() for x in companies_input.split(',')]
    except Exception:
        logger.error("Invalid input for company_ids.")
        sys.exit(1)

    try:
        start_date_str = input("Enter start date (MM-DD-YYYY): ")
        end_date_str = input("Enter end date (MM-DD-YYYY): ")
        start_date = datetime.strptime(start_date_str, "%m-%d-%Y")
        end_date = datetime.strptime(end_date_str, "%m-%d-%Y")
    except Exception:
        logger.error("Invalid date format. Use MM-DD-YYYY.")
        sys.exit(1)

    timeout_input = input("Enter timeout in seconds for page load (default 15): ")
    try:
        timeout = int(timeout_input) if timeout_input.strip() else 15
    except ValueError:
        timeout = 15

    scrape(company_ids, start_date, end_date, timeout)
