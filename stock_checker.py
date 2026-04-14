from selenium import webdriver
import undetected as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import logging
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()
APP_PASSWORD = os.getenv("APP_PASSWORD")
USER_EMAIL = os.getenv("USER_EMAIL")

# For notifications (not env)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Setting up logging configuration
logging.basicConfig(filename='stock_watch.log', filemode='a', level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('urllib3').setLevel(logging.ERROR)

# Only principal matcha products are included
PRODUCT_LIST = ['Aoarashi', 'Wako', 'Isuzu']

# File name for history
HISTORY_FILE = 'matcha_history.csv'

def marukyu_extraction():
    '''
    Extracting the HTML source of Marukyu Koyamaen's matcha product page.

    Returns:
        - html_source (str): The HTML source of the webpage.
    '''
    url = "https://www.marukyu-koyamaen.co.jp/english/shop/products/catalog/matcha?currency=USD"
    
    driver = None
    try:
        options = uc.ChromeOptions()
        
        # Check if running in CI environment (GitHub Actions)
        if os.getenv('CI'):
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            driver = uc.Chrome(options=options)  # Let it auto-detect version
        else:
            driver = uc.Chrome(options=options, version_main=146, use_subprocess=True)
        
        time.sleep(3)
        
        driver.get(url)
        time.sleep(10)
        
        html_source = driver.page_source
        
        return html_source
    except Exception as e:
        logging.error(f"Error during extraction: {e}")
        return None
    finally:
        if driver is not None:
            try:
                driver.quit()
                time.sleep(2)
            except Exception as e:
                logging.warning(f"Error closing driver: {e}")

def stock_parser(html_source):
    '''
    Parsing the extracted information to check stock availability.

    Args:
        - html_source (str): The HTML source of the webpage.

    Returns:
        - information_list (list): A list of tuples containing item name, link, and stock status.
    '''
    # Check if html_source is None before parsing
    if html_source is None:
        logging.error("No HTML source provided for parsing.")
        exit(1)

    matcha_soup = BeautifulSoup(html_source, "html.parser")
    information_list = []

    for product in PRODUCT_LIST:
        matcha = matcha_soup.find("a", title=product)

        if matcha is not None:
            matcha_product_information = {}
            matcha_product_information['product_name'] = product
            
            # Getting the link for the product
            if matcha.get('href') is None:
                logging.warning(f"No link found for {product}.")

            matcha_product_information['link'] = matcha.get('href', 'No Link')

            # Getting stock status for the product
            matcha_parent = matcha.find_parent("li")
            if 'outofstock' in matcha_parent['class']:
                matcha_product_information['stock_status'] = 'Out of Stock'
            elif 'instock' in matcha_parent['class']:
                matcha_product_information['stock_status'] = 'In Stock'
            else:
                logging.warning(f"Stock status of {product} is unknown.")
                matcha_product_information['stock_status'] = 'Unknown'

            information_list.append(matcha_product_information)
        else:
            logging.warning(f"{product} not found on the page.")

    return information_list

def update_history(information_list):
    '''
    Update the history of stock status for each product.

    Args:
        - information_list (list): A list of tuples containing item name, link, and stock status.
    '''
    # Opening the history file or creating a new one if it doesn't exist
    matcha_history = pd.read_csv(HISTORY_FILE) if pd.io.common.file_exists(HISTORY_FILE) else pd.DataFrame(columns = ['matcha_product', 'link', 'stock_status', 'last_updated'])

    # List to keep track of products that updated from OOS to IS
    instock_changed_products = []
    
    for info in information_list:
        # Check if product exists in history
        if info['product_name'] in matcha_history['matcha_product'].values:
            # Check if stock status has changed
            existing_status = matcha_history.loc[matcha_history['matcha_product'] == info['product_name'], 'stock_status'].values[0]

            if existing_status != info['stock_status']:
                # If product has changed from OOS to IS, add it to the list for notification
                if (info['stock_status'] == 'In Stock') and (existing_status == 'Out of Stock'):
                    product_info = {'matcha_product': info['product_name'], 'link': info['link']}
                    instock_changed_products.append(product_info)

                # Changes if stock status has changed (both OOS to IS and IS to OOS)
                matcha_history.loc[matcha_history['matcha_product'] == info['product_name'], ['stock_status', 'last_updated']] = [info['stock_status'], pd.Timestamp.now()]
            else:
                matcha_history.loc[matcha_history['matcha_product'] == info['product_name'], 'last_updated'] = str(pd.Timestamp.now())
        else:
            if info['stock_status'] == 'In Stock':
                product_info = {'matcha_product': info['product_name'], 'link': info['link']}
                instock_changed_products.append(product_info)

            # If product does not exist in history, add it
            new_entry = {
                'matcha_product': info['product_name'],
                'link': info['link'],
                'stock_status': info['stock_status'],
                'last_updated': pd.Timestamp.now()
            }
            matcha_history = pd.concat([matcha_history, pd.DataFrame([new_entry])], ignore_index=True)

        # Save the updated history back to the CSV file
        matcha_history.to_csv(HISTORY_FILE, index=False)

    return instock_changed_products

def notify_user(instock_changed_products):
    '''
    Notify the user about stock availability.
    '''
    message = MIMEMultipart()
    message["From"], message["To"] = USER_EMAIL, USER_EMAIL
    message["Subject"] = f"Matcha Restock Alert: {len(instock_changed_products)} product(s) available!"

    body = "The following matcha products are now in stock:\n\n"
    
    for product in instock_changed_products:
        product_name = product['matcha_product']
        product_link = product['link']
        body += f"- {product_name}: {product_link}\n"
    
    body += "\nAct fast - these may sell out quickly!\n"
    body += f"\nChecked at: {pd.Timestamp.now()}"

    message.attach(MIMEText(body, "plain"))

    try:
        # Connect and Send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(USER_EMAIL, APP_PASSWORD)
        server.send_message(message)
        logging.info("Email sent successfully!")
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        server.quit()

def main():
    '''
    Main function for checking stock on Marukyu Koyamaen's website.
    '''
    html_source = marukyu_extraction()
    if html_source is None:
        logging.error("Failed to extract HTML source.")
        exit(1)

    information_list = stock_parser(html_source)

    instock_changed_products = update_history(information_list)

    if len(instock_changed_products) > 0:
        notify_user(instock_changed_products)
    else:
        logging.info("No products changed their status.")

if __name__ == "__main__":
    main()