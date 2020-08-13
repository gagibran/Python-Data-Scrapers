"""
Application designed to scrape prices of goodies in the Brazilian web store "Mercado Livre": https://www.mercadolivre.com.br/.
"""

import requests
import time
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

def get_ml_html(subject_of_search):
    """
    Requests https://www.mercadolivre.com.br/ for an item. If there are no problems in the request, returns the HTML document of the page.
    For a full documentation on HTTP status, refer to: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status.

    INPUT:
    subject_of_search: subject that you wish to search for in https://www.mercadolivre.com.br/ (str).

    OUTPUT:
    ml_request: an HTML document (requests.Response).
    """
    ml_suffix = '-'.join(subject_of_search.split())
    ml_request_status = 0
    while ml_request_status != 200:
        try:
            ml_request = requests.get('https://lista.mercadolivre.com.br//{}_DisplayType_G'.format(ml_suffix), time.sleep(7))
            ml_request_status = ml_request.status_code # Since only one request is made, a season doesn't need to be created, thus it doesn't need closing.
            ml_request.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            print("An HTTP error was detected. Please, address this error and try again.")
            raise SystemExit(http_err)
        except requests.exceptions.ConnectionError as con_err:
            print("Connection error: check tour Internet connection and try again.")
            raise SystemExit(con_err)
        except requests.exceptions.Timeout as to_err:
            print ("Timeout error: {}. Trying again...".format(to_err))
            continue
        except requests.exceptions.RequestException as err:
            print ("An error has occurred. Please, address this error and try again.")
            raise SystemExit(err)
    return ml_request

def print_html(html_doc):
    """
    Simple function that uses Beautiful Soup to print an HTML string from requests in a structured way. Useful for debugging.

    INPUT:
    html_doc: an HTML document (str).

    OUTPUT:
    Prints the document formatted.
    """
    soup = BeautifulSoup(html_doc.text, 'html.parser')
    print(soup.prettify())

def content_search(html_doc):
    """
    From a web page, gets the items' URL, name, price, maximum installments multiplier, price per installment with this multiplier, whether it can be bought interest-free, 
    seller (when it's discriminated), and shipping price.
    A typical ML product web page is composed of an ordered list tag, which contains list items that are the products themselves.

    INPUT:
    html_doc: an HTML document (str).

    OUTPUT:
    content_matrix: a 2D matrix containing all content of a product in its lines and all products in its columns.
    """
    soup = BeautifulSoup(html_doc.text, 'html.parser')
    items = soup.find_all('li', {'class': 'results-item'}) # Get all list element tags of the ordered list tag and stores them as a Python list. 48 per page.
    content_list_of_lists = [] # An 8 by number of products list (of lists) that will be later converted into a matrix.
    for item in items:
        content_list = []

        # Handling basic elements:
        content_list.append(item.a['href']) # URL.
        content_list.append(item.h2.text.strip().split('por')[0].strip()) # Product name.

        # Handling price:
        price_decimals = item.find('span', {'class': 'price__decimals'}).text if item.find('span', {'class': 'price__decimals'}) != None else '0' # Some prices are integers.
        price_fraction = item.find('span', {'class': 'price__fraction'}).text
        if '.' in price_fraction:
            price_fraction = ''.join(item.find('span', {'class': 'price__fraction'}).text.split('.')) # Getting rid of the coma that separate decimals.
        content_list.append(float(price_fraction + '.' + price_decimals)) # Price (in BRL).

        # Handling installments:
        content_list.append(int(item.find('span', {'class': 'item-installments-multiplier'}).text.strip().split('x')[0])) # Installments multiplier. We don't want the multiply sign to be part of the price.
        list_inst = item.find('span', {'class': 'item-installments-price'}).text.strip().split()
        if len(list_inst) <= 2:
            content_list.append(float(list_inst[1])) # Some installments are integers.
        else:
            content_list.append(float(list_inst[1] + '.' + list_inst[2])) # Installments price. The first element (0) is not needed, for it's R$.

        # Handling interest free items (free or not):
        is_interest_free = True if item.find('span', {'class': 'item-installments-interest'}) != None else False
        content_list.append(is_interest_free)

        # Handling seller:
        try:
            seller = item.h2.text.strip().split('por')[1].strip() # Gets the seller's name from the inner h2 tag (if it's discriminated).
        except:
            seller = 'Not discriminated'
        content_list.append(seller)

        # Handling shipping price:
        if item.find('span', {'class': 'text-shipping'}) != None and item.find('span', {'class': 'text-shipping'}).text.strip() != 'Frete grátis':
            content_list.append(item.find('span', {'class': 'text-shipping'}).text.strip())
        elif item.find('span', {'class': 'text-shipping'}) != None and item.find('span', {'class': 'text-shipping'}).text.strip() == 'Frete grátis':
            content_list.append('Free')
        else:
            content_list.append('Not discriminated')

        # content_list has, by the end of a loop, [url, product_name, price, inst_multiplier inst_prices, is_interest_free, seller, ship_price].
        # Saves content_list in the list of lists.
        content_list_of_lists.append(content_list)
    content_matrix = np.array(content_list_of_lists) # Transforms a the list of lists into a NumPy 2D array.
    return content_matrix

def content_to_df(html_doc):
    """
    Transforms the search result matrix into a Pandas dataframe.
    """
    pass

if __name__ == "__main__":
    search = input('What product do you wish to search for?')
    print('Requesting web page for the product...')
    content = []
    while len(content) == 0:
        html = get_ml_html(search)
        content = content_search(html)
    print('Content found. Converting items into .csv...')
    print(content)
