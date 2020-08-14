"""
Application designed to scrape prices of goodies in the Brazilian web store "Mercado Livre": https://www.mercadolivre.com.br/.
"""

import sys
import time
import requests
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

    # Handling number of items per page (48)
    if '_DisplayType_LF' in subject_of_search:
        ml_suffix = '-'.join(subject_of_search.split())
    else:
        ml_suffix = '-'.join(subject_of_search.split()) + '_DisplayType_LF'

    # Handling page loading:
    testing = []
    while len(testing) == 0: # Waits until the page has loaded up, if it hasn't already.
        ml_request_status = 0
        while ml_request_status != 200:
            try:
                ml_request = requests.get('https://lista.mercadolivre.com.br//{}'.format(ml_suffix), time.sleep(10))
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
        test_soup = BeautifulSoup(ml_request.text, 'html.parser')
        testing = test_soup.find_all('li', {'class': 'results-item'})
    return ml_request

def print_html(html_doc):
    """
    Simple function that uses Beautiful Soup to print an HTML string from requests in a structured way. Useful for debugging.

    INPUT:
    html_doc: an HTML document (requests.Response).

    OUTPUT:
    Prints the document formatted.
    """
    soup = BeautifulSoup(html_doc.text, 'html.parser')
    print(soup.prettify())

def number_of_pages(html_doc):
    """
    Calculates the number of items, pages, and items per page the search returned.

    INPUT:
    html_doc: an HTML document (requests.Response).

    OUTPUT
    total_pages: the total number of pages the products are divided into (int).
    total_results_formatted: the total number of products (int).
    """
    soup = BeautifulSoup(html_doc.text, 'html.parser')

    # Finding how many results the search has returned:
    total_results = soup.find('div', {'class': 'quantity-results'}).text.strip().split()[0] # UNRELIABLE! Using it just for an estimate. No other way to read the real total of items.
    total_results_formatted = int(''.join(total_results.split('.'))) if '.' in total_results else int(total_results)

    # Finding the maximum pages the products are divide into:
    if total_results_formatted / 50 > 40: # ML pages are divided in steps of 50 elements, even when there are more than 50 elements per page.
        total_pages = 40 # Maximum number of pages an ML search returns, even if there are more products.
    elif total_results_formatted % 50 != 0: # If the maximum number of pages is less than 40 and there is a reminder:
        total_pages = total_results_formatted // 50 + 1 # Adds another page to comport the remaining products.
    else:
        total_pages = total_results_formatted // 50
    return total_pages

def content_search(html_doc):
    """
    From a web page, gets the items' URL, name, price, installments multiplier, price per installment with this multiplier, whether it can be bought interest-free, 
    seller (when it's discriminated), and whether the shipping is free.
    A typical ML product web page is composed of an ordered list tag, which contains list items that are the products themselves.

    INPUT:
    html_doc: an HTML document (requests.Response).

    OUTPUT:
    content_matrix: a 2D matrix containing all content of a product in its lines and all products in its columns (numpy.ndarray).
    """
    soup = BeautifulSoup(html_doc.text, 'html.parser')
    items = soup.find_all('li', {'class': 'results-item'}) # Get all list element tags of the ordered list tag and stores them as a Python list. 48 per page.
    content_list_of_lists = [] # An 8 by number of products list (of lists) that will be later converted into a matrix.
    for item in items:
        content_list = []

        # Handling basic URL and name:
        content_list.append(item.a['href']) # URL.
        content_list.append(item.find('span', {'class': 'main-title'}).text.strip()) # Product name.

        # Handling prices:
        price_fraction_span = item.find('span', {'class': 'price__fraction'})
        price_decimals_span = item.find('span', {'class': 'price__decimals'})
        if price_decimals_span != None: # If there're decimals in the decimal span tag:
            price_decimals = price_decimals_span.text
        else:
            price_decimals = '0' # Some prices are integers.
        if price_fraction_span == None: # If there is not span tag:
            price = item.find('div', {'class': 'pdp_options__text'}).text.strip().split()[1]
            price_fraction = price[1].split(',')[0]
            price_decimals = price[1].split(',')[1] if len(price[1].split(',')) > 1 else '0' # Some prices are integers.
        else:
            price_fraction = price_fraction_span.text
        if '.' in price_fraction:
            price_fraction = ''.join(price_fraction.split('.')) # Getting rid of the coma that separate decimals.
        content_list.append(float(price_fraction + '.' + price_decimals)) # Price (in BRL).

        # Handling installments:
        installments_multiplier_span = item.find('span', {'class': 'item-installments-multiplier'})
        if installments_multiplier_span != None:# If there is a multiplier (there's also installments):
            installments_multiplier = int(installments_multiplier_span.text.strip().split('x')[0]) # Installments multiplier. We don't want the multiply sign to be part of the price.
            list_inst = item.find('span', {'class': 'item-installments-price'}).text.strip().split()
            if len(list_inst) <= 2:
               installments = float(list_inst[1]) # Some installments are integers.
            else:
                installments = float(list_inst[1] + '.' + list_inst[2]) # Installments price (fraction plus decimals). The first element (0) is not needed, for it's R$.
        else:
            installments_multiplier = 'Not discriminated'
            installments = 'Not discriminated'
        content_list.append(installments_multiplier)
        content_list.append(installments)

        # Handling interest free items (free or not):
        is_interest_free = True if item.find('span', {'class': 'item-installments-interest'}) != None else False
        content_list.append(is_interest_free)

        # Handling seller:
        seller_span = item.find('span', {'class': 'item__brand-title-tos'})
        if seller_span != None:
            seller = seller_span.text.strip().split()[1] # Gets the seller's name (if it's discriminated).
        else:
            seller = 'Not discriminated'
        content_list.append(seller)

        # Handling shipping price:
        is_free_shipping_span = item.find('span', {'class': 'text-shipping'})
        if is_free_shipping_span != None and is_free_shipping_span.text.strip() != '':
            free_shipping = True
        else:
            free_shipping = False
        content_list.append(free_shipping)

        # content_list has, by the end of a loop, [url, product_name, price, inst_multiplier inst_prices, is_interest_free, seller, ship_price].
        # Saves content_list in the list of lists.
        content_list_of_lists.append(content_list)
    content_matrix = np.array(content_list_of_lists) # Transforms a the list of lists into a NumPy 2D array.
    return content_matrix

def content_to_df(array_2d):
    """
    Transforms a matrix into a Pandas dataframe. The column names are the variables read in a ML product.

    INPUT:
    array_2d: a matrix (ndarray).

    OUTPUT:
    ml_df: a Pandas dataframe (pandas.Dataframe).
    """
    column_labels = ['URL', 'Name', 'Price (BRL)', 'Installments Multiplier', 'Installments', 'Interest-free', 'Seller', 'Free shipping']
    ml_df = pd.DataFrame(array_2d, columns=column_labels)
    return ml_df

def df_to_file(df, file_name, type_of_file='CSV'):
    """
    Converts a Pandas dataframe to a file.

    INPUT:
    df: Pandas dataframe (pandas.Dataframe).
    file_name: name of the output file (str).
    type_of_file: which type of file the dataframe will be converted to (str):
        CSV (default); and
        EXCEL.

    OUTPUT:
    The file inside this script's folder.
    """
    formatted_file_name = 'ML_' + '_'.join(file_name.split())
    if type_of_file == 'CSV':
        df.to_csv('{}.csv'.format(formatted_file_name), index=False) # No need for indices.
        print('The output file is inside the same folder as the script was executed and it is called {}.csv.'.format(formatted_file_name))
    elif type_of_file == 'EXCEL':
        df.to_excel('{}.xlsx'.format(formatted_file_name), sheet_name='Products', index=False) # No need for indices.
        print('The output file is inside the same folder as the script was executed and it is called {}.xlsx.'.format(formatted_file_name))

if __name__ == "__main__":
    print('\n')
    search = input('What product do you wish to search for? ')
    print('\n')
    start_timer = time.time() # Measuring execution time.

    # Handling the first request:
    print('Requesting web page for the product...\n')
    html = get_ml_html(search)
    maximum_pages = number_of_pages(html)
    print('The search returned a total of {} pages'.format(maximum_pages))
    print('NOTE: ML caps the maximum page to 40, even when there are more products.')
    print('NOTE: The total number of items shown in the web page is unreliable: sometimes it is completetly wrong.')
    print('The reliable amount of items is discriminated in the final spreadsheet generated at the end.\n')

    # Searching the first page:
    content = content_search(html)
    content_df = content_to_df(content)

    # Handling maximum of pages:
    pages = int(input('For how many pages do you wish to iterate through? '))
    print('\n')
    while pages > maximum_pages:
        print('{} is greater than the maximum of pages for this product, which is {} pages. Please, try again.\n'.format(pages, maximum_pages))
        pages = int(input('For how many pages do you wish to iterate through? '))

    # Handling iteration:
    if pages > 1:
        print('First page already scraped.')
        print('Scraping over {} more page(s)...'.format(pages-1))
        for page_num in range(1, pages):
            print('Page {}...'.format(page_num+1))
            html = get_ml_html(search + '_Desde_{}_DisplayType_LF'.format(page_num*50+1)) # Steps of 50.
            content_other_page = content_search(html)
            content_other_page_df = content_to_df(content_other_page)
            content_df = content_df.append(content_other_page_df)
    print('{} items scraped.\n'.format(content_df.shape[0] - 1)) # Total items scraped = number of rows minus the index row.

    # Handling file type:
    file_type = input('What kind of file do you wish to convert the data into? CSV or EXCEL: \n').upper()
    while file_type != 'CSV' and file_type != 'EXCEL':
        file_type = input('Invalid file format. What kind of file do you wish to convert the data into? CSV or EXCEL: \n').upper()

    # Converting the file:
    df_to_file(content_df, search, file_type)
    execution_time = round((time.time()-start_timer), 2)
    print('Done. Execution time: {} s.'.format(execution_time))
