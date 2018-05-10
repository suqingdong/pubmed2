#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import sys
import time
import datetime
import json
import argparse
import functools
import random
import sqlite3

import bs4
import requests
import fuzzywuzzy.process


__author__ = 'suqingdong'
__version__ = '2.0'

reload(sys)
sys.setdefaultencoding('utf8')

BASE_URL = 'http://www.letpub.com.cn/index.php'


# 自定义的装饰器
def try_again(N=10, default='.'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            n = 0
            while n < N:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    n += 1
                    print '[warn] `{}` failed {}st time: {}'.format(func.__name__, n, e)
                    time.sleep(random.randint(5, 10))
            if n == N:
                print '[error] `{}` failed too many times({})'.format(func.__name__, N)
                return default
        return wrapper
    return decorator

@try_again()
def get_soup(url, **kwargs):

    headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
    }

    response = requests.get(url, headers=headers, **kwargs)
    soup = bs4.BeautifulSoup(response.content, 'lxml')

    return soup

@try_again(5)
def get_journal_impact_factor(payload):

    soup = get_soup(BASE_URL, params=payload)

    table_index = 0 if 'searchname' in payload else 1

    table = soup.select('table.table_yjfx')[table_index]

    for tr in table.select('tr')[2:-1]:
        tds = tr.select('td')

        if len(tds) < 3:
            yield '', '.', '', ''

        journal = tds[1].contents[-1].text
        journal_full = tds[1].contents[-4].text
        style = tds[1].contents[0].attrs['style']
        impact_factor = tds[2].text

        issn = tds[0].text

        if 'text-decoration:underline' not in style:
            continue

        yield journal, impact_factor, journal_full, issn


@try_again(5)
def get_impact_factor(searchname, database=None):
    """
        :param searchname: the journal name
        :param database: the database filename
    """
    print 'Input name:', searchname

    if database and os.path.exists(database) and os.path.getsize(database):
        print 'Use local database: {}'.format(database)

        if database.endswith('.json'):
            with open(database) as f:
                journal_impact_factor = json.load(f)
        elif database.endswith('.db'):
            db = sqlite3.connect(database)
            cursor = db.cursor()
            sql = "SELECT * FROM `factor` WHERE journal LIKE '%{}%';".format(searchname.replace("'", ""))
            cursor.execute(sql)
            result = cursor.fetchall()
            journal_impact_factor = dict(result)
    else:
        journal_impact_factor = {}

        payload = {
            'page': 'journalapp',
            'view': 'search',
            'searchsort': 'relevance',
            'searchname': searchname
        }

        for journal, impact_factor, journal_full, _ in get_journal_impact_factor(payload):
            if journal.strip():
                journal_impact_factor[journal] = impact_factor
                journal_impact_factor[journal_full] = impact_factor
            else:
                print '[warn] no journal for searchname: {}'.format(searchname)
                return '.'

    if not journal_impact_factor:
        print '[warn] no journal for searchname: {}'.format(searchname)
        return '.'

    # use fuzzywuzzy to select a best one
    result = fuzzywuzzy.process.extractOne(searchname, journal_impact_factor.keys())
    best_journal = result[0]
    best_impact_factor = journal_impact_factor[best_journal]

    if result[1] < 93:
        best_impact_factor = '.'
        print 'Bad match: {} [IF: {}](Score: {})'.format(
            best_journal, best_impact_factor, result[1])
    else:
        print 'Best match: {} [IF: {}](Score: {})'.format(
            best_journal, best_impact_factor, result[1])

    return best_impact_factor


def craw_all_journal(start_page):

    # issn_list = []

    payload = {
        'page': 'journalapp',
        'fieldtag': '',
        'firstletter': '',
        'currentpage': start_page
    }

    # finish = False
    while True:

        print '\033[0m\033[32m[info] [{}] dealing with page {}\033[0m'.format(
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            payload['currentpage'])

        for journal, impact_factor, journal_full, issn in get_journal_impact_factor(payload):

            # 判断是否全部完成
            # if issn in issn_list:
            # finish = True

            if journal.strip():
                # issn_list.append(issn)
                print issn, journal, impact_factor

                yield journal, impact_factor, journal_full

        payload['currentpage'] += 1

        # 全部完成时退出循环
        # if finish:
        if payload['currentpage'] > 1000:
            print '\033[35m[info] [{}] all done!\033[0m'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            break


def main():

    args = vars(parser.parse_args())

    database_xls = args['database'] + '.xls'
    database_json = args['database'] + '.json'
    database_sqlite3 = args['database'] + '.db'

    if args['craw_all']:

        with open(database_xls, 'w') as out:
            for journal, impact_factor, journal_full in craw_all_journal(args['start_page']):
                out.write('{}\t{}\n'.format(journal, impact_factor))
                out.write('{}\t{}\n'.format(journal_full, impact_factor))

        with open(database_xls) as f, open(database_json, 'w') as out:
            impact_factor = dict([
                line.strip().split('\t') for line in f
                if len(line.strip().split('\t')) == 2
            ])
            json.dump(impact_factor, out, indent=2)

    elif args['searchname']:

        if os.path.exists(database_json):
            a = time.time()
            print get_impact_factor(args['searchname'], database_json)
            print 'json:', time.time() - a

        if os.path.exists(database_sqlite3):
            b = time.time()
            print get_impact_factor(args['searchname'], database_sqlite3)
            print 'sqlite3:', time.time() - b

        c = time.time()
        print get_impact_factor(args['searchname'])
        print 'web:', time.time() - c

    else:
        print parser.format_version()
        print parser.format_help()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='get_impact_factor',
        version='%(prog)s {}'.format(__version__),
        description='get impact factor for given journal name',
        epilog='contact: {0} < {0}@novogene.com> '.format(__author__),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-s', '--searchname', help='The input journal name')
    parser.add_argument('-c', '--craw-all', help='Craw all journal from web to local', action='store_true')
    parser.add_argument('-d', '--database', help='The database name of impact factor', default='impact_factor')
    parser.add_argument('-sp', '--start-page', help='The start page number to craw', default=1, type=int)

    main()
