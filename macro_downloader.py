# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 13:49:21 2019

@author: bz68
"""

import requests
from bs4 import BeautifulSoup as bs
import re
import json
import pandas as pd
from stock_list import get_stock_pool
import datetime
import os
import math
import sys

'''
This modulus: 
    1. download the fundamental data from Macrotrends
    2. update the fscore based on downloaded data

Input:
    benchmark: 
        1. this can be a folder path or
        2. a benchmark name, e.g. ndaq
        3. or a dataframe with tickers as index

'''

def single_downloader(ticker, comp_name, freq):
    
    tab_names = ['income-statement','balance-sheet','cash-flow-statement','financial-ratios']
    
    df_all = pd.DataFrame()
    
    for tab_name in tab_names:
        try:
            url = 'https://www.macrotrends.net/stocks/charts/{}/{}/{}?freq={}'.format(ticker,comp_name,tab_name,freq)
            
            res = requests.get(url)    
            soup = bs(res.text, 'html.parser')
            scripts = soup.findAll('script')
            
            max_len = 0
                
            for i in range(len(scripts)):
                if len(scripts[i].text) > max_len:
                    max_len = len(scripts[i].text)
                    index_script = i
                
            data = scripts[index_script].text
            matchObj = re.search('var originalData = \[.*?\]', data)
            data = matchObj.group()
            data_var = data[data.find('['):];
            
            data_parameters = data_var.split("field_name")[1:]
            
            df = pd.DataFrame()
            
            for i in range(len(data_parameters)):
                var_name_start = 0
                var_name_len = 0
                var_name_start = data_parameters[i].find('s:')
                if var_name_start < 0:
                    continue
                var_name_start += len('s:')
                var_name_len = data_parameters[i][var_name_start:].find(',')
                
                col = data_parameters[i][var_name_start:var_name_start + var_name_len].replace("'", "").strip()
                dict_data = json.loads('{' + data_parameters[i].split('<\/div>",')[1].split('}')[0] + '}')
                df[col] = pd.Series(dict_data)
            
            df_all = pd.concat([df_all, df], axis=1, sort=False)
        except Exception as e:
            print('Error with {}, {}'.format(ticker, e))
        
    return df_all

def batch_downloader(benchmark, freq='Q'):
    
    day_today = datetime.date.today().day
    month_today = datetime.date.today().month
    year_today = datetime.date.today().year
    
    df = pd.read_csv(r'fundamental data\\fundamental_data_all.csv', usecols=['ticker','comp_name','zacks_x_sector_desc'])
    df.set_index(['ticker'], inplace=True)
    
    if benchmark in ['ndaq', 'dow', 's&p500', 's&p100', 's&p400']:
        stock_list = get_stock_pool(benchmark)[0]
        folder_name = benchmark
    elif isinstance(benchmark, str) :
        if os.path.exists(benchmark):
            stock_list = [stock.split('.')[0] for stock in os.listdir(benchmark)]
            folder_name = benchmark.split('\\')[-1].split('(')[0]
        else:
            print('{} not found as a folder'.format(benchmark))
    elif isinstance(benchmark, pd.DataFrame):
        stock_list = benchmark.index
        folder_name = '{}-{}-{}'.format(year_today, month_today, day_today)
    
    folder_path = 'fundamental data\\{}-{}\\{}'.format(year_today, month_today, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    else:
        return folder_path

    for ticker in stock_list:
        path = '{}\\{}.csv'.format(folder_path, ticker)
        if os.path.exists(path):
            continue
        try:
            comp_name = df.loc[ticker, 'comp_name']        
            df_all = single_downloader(ticker, comp_name, freq)
            
            df_all.to_csv(path, index_label='Date')
            print('{} Downloaded!'.format(ticker))
        except Exception as e:
            print('Error with {}, {}'.format(ticker, e))
            
    return folder_path
    

def single_fscore_update(folder_path, ticker):

    path = '{}\\{}.csv'.format(folder_path, ticker)
    df = pd.read_csv(path)
    df.set_index('Date', inplace=True)
    df.dropna(how='all', inplace=True)
    
    if 'fscore' in df.columns:
        return df
    
    for row, date in enumerate(df.index):
        if row > len(df.index) - 8:
            break
        fscore = 0
        
        try:
            # Profitability Criteria
            net_income = df['net-income'][row:row+4].sum()
            if net_income > 0:
                fscore += 1
        except KeyError:
            pass
        
        try:
            roa = df['roa'][row:row+4].mean()
            if roa > 0:
                fscore += 1
        except KeyError:
            pass

        try:
            cfo = df['cash-flow-from-operating-activities'][row:row+4].mean()
            if cfo > 0:
                fscore += 1

            if cfo > net_income:
                fscore += 1
        except KeyError:
            pass
        
        # Leverage, Liquidity and Source of Funds Criteria
        try:
            if not 'long-term-debt' in df.columns:
                fscore += 1
            else:
                ltd = df['long-term-debt'][row:row+4].mean()
                ltd_last_year = df['long-term-debt'][row+4:row+8].mean()
                if (ltd < ltd_last_year) | (math.isnan(ltd)):
                    fscore += 1
        except KeyError:
            pass
        
        try:
            cr = df['current-ratio'][row:row+4].mean()
            cr_last_year = df['current-ratio'][row+4:row+8].mean()
            if cr > cr_last_year:
                fscore += 1
        except KeyError:
            pass
        
        try:
            so = df['shares-outstanding'][row:row+4].mean()
            so_last_year = df['shares-outstanding'][row+4:row+8].mean()
            if so < so_last_year:
                fscore += 1
        except KeyError:
            pass
        
        try:
            gm = df['gross-margin'][row:row+4].mean()
            gm_last_year = df['gross-margin'][row+4:row+8].mean()
            if gm > gm_last_year:
                fscore += 1
        except KeyError:
            pass
        
        try:    
            at = df['asset-turnover'][row:row+4].mean()
            at_last_year = df['asset-turnover'][row+4:row+8].mean()
            if at > at_last_year:
                fscore += 1
        except KeyError:
            pass
            
        df.loc[date, 'fscore'] = fscore
    
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]
    df.to_csv(path)
    
    return df

def batch_fscore_update(folder_path):
    stock_error = []
    if os.path.exists(folder_path):
        filenames = os.listdir(folder_path)
    else:
        sys.exit('{} not created. Please check.'.format(folder_path))
    
    for f in filenames:
        ticker = f.rsplit('.',1)[0]
        try:
            single_fscore_update(folder_path, ticker)
        except Exception as e:
            print('Error with {}. {}'.format(ticker, e))
            stock_error.append(ticker)

    print('fscore updated!')
    return stock_error

def find_stock_fscore(folder_path):

    if os.path.exists(folder_path):
        filenames = os.listdir(folder_path)
    else:
        sys.exit('{} not created. Please check.'.format(folder_path))
    
    df = pd.DataFrame()
    for f in filenames:
        try:
            ticker = f.split('.')[0]
            ticker_path = '{}\\{}'.format(folder_path, f)
            df_data = pd.read_csv(ticker_path, usecols=['Date','fscore'])
            df_data.set_index('Date', inplace=True)
            df_data.index = pd.to_datetime(df_data.index)
            fscore = df_data.iloc[0,0]
            df.loc[ticker, 'fscore'] = fscore
        except (ValueError, KeyError):
            pass
        
    df.sort_values('fscore',inplace=True, ascending=False)
    
    return df

def main(benchmarks):
    for benchmark in benchmarks:
        folder_path = batch_downloader(benchmark)
        batch_fscore_update(folder_path)
        df_fscore = find_stock_fscore(folder_path)
    
    return df_fscore

if __name__ == '__main__':
    
#    benchmarks = ['ndaq', 'dow', 's&p500', 's&p100', 's&p400']
    benchmarks = ['s&p400']
    
    df_fscore = main(benchmarks)