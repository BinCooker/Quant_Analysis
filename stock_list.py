 # -*- coding: utf-8 -*-

import requests
import logging
from bs4 import BeautifulSoup as bs
import json
import os

def get_stock_pool(benchmark = 'nsdq'):
    '''
    This function will output a list of stocks for NDAQ/DOW/S&P benchmarkes
    Designed for stock analysis and picking
    
    In:
        benchmark: specify the NDAQ/DOW/S&P benchmark
        
    Out:
        a list of stocks in the benchmark
    
    Author: Bin Zhang 08/15/2019
    '''
    
    if os.path.exists('stock_list\\{}_tickers.json'.format(benchmark)):

        with open('stock_list\\{}_tickers.json'.format(benchmark),'r') as f:
            tickers = json.load(f)
        source = 'json'
        return tickers, source
    
    
    if benchmark == 'ndaq':
        url = 'https://en.wikipedia.org/wiki/NASDAQ-100'
        table_col = 1
    elif benchmark == 's&p500':
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        table_col = 0
    elif benchmark == 's&p100':
        url = 'https://en.wikipedia.org/wiki/S%26P_100'
        table_col = 0
    elif benchmark == 'dow':
        url = 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
        table_col = 2
    elif benchmark == 's&p400':
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies'
        table_col = 1
    else:
        logging.warning('Please enter: 1. ndaq, 2.s&p, 3.dow')
        return
    
    
    res = requests.get(url)
    
    soup = bs(res.text, 'html.parser')
    table = soup.find('table', {'class':'wikitable sortable'})
    tickers = []
    source = 'wiki'
    for row in table.findAll('tr')[1:]:
        ticker = row.findAll('td')[table_col].text.replace('\n','')
        tickers.append(ticker)
        
    return tickers, source

def save_pool_local(benchmark):
    try:
        stock_pool, source = get_stock_pool(benchmark)
        with open('stock_list\\{}_tickers.json'.format(benchmark),'w') as f:
            json.dump(stock_pool, f)
    except Exception:
        logging.warning('Please enter: 1. ndaq, 2.s&p, 3.dow')
        
    return 1
        

if __name__ == '__main__':
    stock_pool, source = get_stock_pool('s&p400')
    save_pool_local('s&p400')
    
    
    