#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import time
import random
import sqlite3
import logging
import functools
import bs4
import requests


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


def logger(log_format='[%(asctime)s %(levelname)s] %(message)s', log_level=logging.INFO):

    logging.basicConfig(level=log_level, format=log_format)

    logger = logging.getLogger(__name__)

    return logger


def text2sqlite3(database, textfile):

    if os.path.exists(database):
        enter = raw_input('database alread exists, enter "r" to remove it, "b" to backup it[default], "q" to quit:').lower()
        if enter == 'q':
            exit()
        elif enter == 'r':
            os.remove(database)
        elif enter == 'b':
	    os.system('mv {database} {database}.bak'.format(**locals()))
        else:
            exit(1)
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    create_table_sql = '''
        CREATE TABLE `factor` (
            journal VARCHAR(100) PRIMARY KEY,
            impact_factor VARCHAR(20)
        );
    '''

    cursor.execute(create_table_sql)

    data = {}
    with open(textfile) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            journal, impact_factor = line.strip().rsplit('\t', 1)
            data.update({journal: impact_factor})

    for context in data.iteritems():
        insert_sql = 'INSERT INTO `factor` VALUES("{}", "{}")'.format(*context)
        print insert_sql
        cursor.execute(insert_sql)

    conn.commit()

    cursor.close()
    conn.close()

    print 'database upated done!'


def sqlite3_execute(database, sql):

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute(sql)

    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return result


if __name__ == '__main__':
    
    import sys
    if len(sys.argv) < 3:
	print 'usage: python %s <database> <textfile>' % sys.argv[0]
	exit()

    text2sqlite3(*sys.argv[1:])
    
