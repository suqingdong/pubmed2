#!/usr/bin/env python
# -*- coding=utf-8 -*-
import re
import sys
import time

import requests

from proxy import Proxy


reload(sys)
sys.setdefaultencoding('utf8')


BASE_URL = 'http://sci-hub.tw'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'}


def get_pdf(term):

    proxy = Proxy(ipPage=30)

    data = {'request': term}

    n = 0
    while n < 10:
        try:
            proxies = proxy.get_random_proxies(protocol='https')
            print 'use proxies:', proxies
            response = requests.post(
                BASE_URL,
                data=data,
                headers=HEADERS,
                proxies=proxies,
                timeout=10)
            pdf = re.findall(r"href='(.+?pdf)", response.text)[0]
            return pdf
        except Exception as e:
            n += 1
            print n, e
            print response.content
            time.sleep(3)
    print 'fail too many times'
    return '.'


def main():

    pdf = get_pdf('29693493')
    print pdf


if __name__ == '__main__':
    main()
