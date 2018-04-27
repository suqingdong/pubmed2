#!/usr/bin/env python
# -*- coding=utf-8 -*-
"""
Usage:
    getIF.py <searchname>

Options:
    <searchname>  The journal name to search

Contact:
    suqingdong <suqingdong@novogene.com>
"""
import time
import bs4
import docopt
import requests
import fuzzywuzzy.process


URL = 'http://www.letpub.com.cn/index.php?page=journalapp&view=search&searchsort=relevance&searchname='
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}


def getIF(searchname):
    """
        :param searchname: the journal name
    """
    print 'Your input searchname: "%s"' % searchname

    i = 0
    while i < 10:
        try:
            response = requests.get(URL + searchname, headers=HEADERS)
            break
        except:
            i += 1
            print 'Failed {}th times'.format(i)
            time.sleep(5)

    if i < 10:
        soup = bs4.BeautifulSoup(response.content, 'html.parser')
        # print soup.select('table.table_yjfx')[0].prettify()
        table = soup.select('table.table_yjfx')[0]

        journal_IF = {}
        for tr in table.select('tr')[2:-1]:
            tds = tr.select('td')
            if len(tds) < 3:
                print 'No match for searchname: "%s"' % searchname
                return '.'
            journal = tds[1].contents[-1].text
            IF = tds[2].text
            # print journal, IF
            journal_IF[journal] = IF

        # use fuzzywuzzy to select a best one
        result = fuzzywuzzy.process.extractOne(searchname, journal_IF.keys())
        best_journal = result[0]
        best_IF = journal_IF[best_journal]

        if result[1] < 90:
            best_IF = '.'
            print 'Bad match: {} [IF: {}](Score: {})'.format(best_journal, best_IF, result[1])
        else:
            print 'Best match: {} [IF: {}](Score: {})'.format(best_journal, best_IF, result[1])
        return best_IF

    print 'Failed too many times'

if __name__ == "__main__":

    arguments = docopt.docopt(__doc__)
    searchname = arguments.get('<searchname>')

    getIF(searchname)

    # test
    # getIF('CLIN BIOCHEM')
