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

# Setting up logging configuration
logging.basicConfig(filename='stock_watch.log', filemode='a', level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('urllib3').setLevel(logging.ERROR)

# Only principal matcha products are included
PRODUCT_LIST = ['Aoarashi', 'Wako', 'Isuzu']

def marukyu_extraction():
    '''
    Extracting site information from Marukyu Koyamaen's website.

    Returns:
        - html_source (str): The HTML source of the webpage.
    '''
    url = "https://www.marukyu-koyamaen.co.jp/english/shop/products/catalog/matcha?currency=USD"
    
    driver = uc.Chrome(version_main=146)
    time.sleep(3)
    
    driver.get(url)
    time.sleep(10)  # Wait for full page load + Cloudflare
    
    html_source = driver.page_source
    
    time.sleep(2)
    driver.quit()
    
    return html_source

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

def notify_user():
    '''
    Notify the user about stock availability.
    '''
    pass

def main():
    '''
    Main function for checking stock on Marukyu Koyamaen's website.
    '''
    html_source = marukyu_extraction()

    if html_source is None:
        logging.error("Failed to extract HTML source.")
        exit(1)
    else:
        logging.critical("Successfully extracted HTML source.")
        print(html_source)

    # information_list = stock_parser(html_source)

if __name__ == "__main__":
    main()

# To find in stock = "instock" and out of stock = "outofstock"
# Located in <li class="product product-type-variable status-publish [STOCKSTATUS] last swiper-slide swiper-slide-visible swiper-slide-active" id="item-2030" style="width: 175.5px;">

# links = soup.find_all('a')
# for link in links:
#     if link.get('title') != None:
#         print(link.get('href') + " " + link.get('title'))
#     else:
#         print(link.get('href'))