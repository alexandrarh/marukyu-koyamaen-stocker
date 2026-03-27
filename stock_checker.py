from selenium import webdriver
import undetected as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Only principal matcha products are included
PRODUCT_LIST = ['Aoarashi', 'Wako', 'Isuzu']

def marukyu_extraction():
    '''
    Extracting site information from Marukyu Koyamaen's website.

    Returns:
        - html_source (str): The HTML source of the webpage.
    '''
    url = "https://www.marukyu-koyamaen.co.jp/english/shop/products/catalog/matcha?currency=USD"
    driver = uc.Chrome()
    driver.get(url)

    # driver.maximize_window()
    time.sleep(2)

    try:
        # Wait until the product title is visible
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception as e:
        print(f"Error waiting for product title: {e}")
        driver.quit()
        return

    html_source = driver.page_source
    driver.quit()

    return html_source

def stock_parser(html_source):
    '''
    Parsing the extracted information to check stock availability.

    Args:
        - html_source (str): The HTML source of the webpage.
    '''
    # Implementing BeautifulSoup to parse the HTML source and check for stock availability
    matcha_soup = BeautifulSoup(html_source, "html.parser")

    pass

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

    stock_parser(html_source)

if __name__ == "__main__":
    main()