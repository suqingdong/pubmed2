#!/usr/bin/env python2
# -*- coding=utf-8 -*-
import os
import sys
import re
import argparse

import fuzzywuzzy.process

from pubmed2.tools import utils


__author__ = 'suqingdong'
__version__ = '3.0'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = 'http://www.letpub.com.cn/index.php'

reload(sys)
sys.setdefaultencoding('utf8')


class GetIF(object):

    def __init__(self, **kwargs):

        self.__dict__.update(kwargs)

        self.logger = utils.logger()

    def get_impact_factor(self, searchname=None, database=None):
        
        searchname = searchname or ' '.join(self.__dict__['searchname']).replace('.', '').strip()
        database = database or self.__dict__['database']

        searchname = re.sub(r'\(.*?\)|\.', '', searchname).strip()

        try:
            import sqlite3
            sqlite_not_installed = False
        except ImportError as e:
            print '[warn] SQLite not installed...'
            sqlite_not_installed = True

        if not os.path.exists(database) or sqlite_not_installed:
            print 'get impact factor from website ...'
            payload = {
                'page': 'journalapp',
                'view': 'search',
                'searchsort': 'relevance',
                'searchname': searchname
            }

            result = {}
            for journal, impact_factor, journal_full, _ in self.craw_impact_factor(payload):
                result[journal] = impact_factor
                result[journal_full] = impact_factor
        else:
            print 'search for: {searchname}'.format(**locals())

            # cmd  = '''
            #     sqlite3 {database} 'SELECT * FROM factor WHERE journal LIKE "%{searchname}%";'
            # '''.format(**locals()).strip()
            with sqlite3.connect(database) as conn:
                conn.text_factory = bytes
                cursor = conn.cursor()
                sql = 'SELECT * FROM factor WHERE journal LIKE "%{searchname}%";'.format(**locals())
                # print sql
                cursor.execute(sql)

                result = cursor.fetchall()
                # print result

            if not result:
                print '[warn] no journal names "{searchname}"'.format(**locals())
                return

            result = dict(result)

        match_journal, match_score = fuzzywuzzy.process.extractOne(searchname, result.keys())
        match_impact_factor = result[match_journal]

        if match_score < 90:
            info = 'bad match: {match_journal} [IF={match_impact_factor}] (Sore={match_score})'
        else:
            info = 'best match: \033[32m{match_journal}\033[0m [IF=\033[32m{match_impact_factor}\033[0m]] (Sore={match_score})'
            
        print info.format(**locals())

	return match_impact_factor

    @utils.try_again(5)
    def craw_impact_factor(self, payload):

        soup = utils.get_soup(BASE_URL, params=payload)

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

    @utils.try_again(5)
    def get_max_page(self):

        payload = {'page': 'journalapp'}

        soup = utils.get_soup(BASE_URL, params=payload)

        max_page = re.findall(
            r'/(\d+)',
            soup.select('form[name="jumppageform"]')[0].text)

        max_page = int(max_page[0])

        self.logger.info('Total page: {max_page}'.format(**locals()))

        return max_page


    def update_database(self):

        payload = {
            'page': 'journalapp',
            'fieldtag': '',
            'firstletter': '',
            'currentpage': 1
        }

        max_page = self.get_max_page()

        out_xls = os.path.splitext(self.__dict__['database'])[0] + '.xls'

        journal_done = {}

        with open(out_xls, 'w') as out:

            while True:
                self.logger.info('\033[31mDealing with page {currentpage}/{max_page}\033[0m'.format(max_page=max_page, **payload))

                for journal, impact_factor, journal_full, issn in self.craw_impact_factor(payload):
                    if journal.strip():

                        # 去重
                        if journal_done.get(journal):
                            continue
                        journal_done[journal] = True

                        self.logger.info('Journal: {journal}({journal_full})\tIF: {impact_factor}'.format(**locals()))

                        line = '{journal}\t{impact_factor}\n{journal_full}\t{impact_factor}\n'.format(**locals())
                        out.write(line)

                if payload['currentpage'] >= max_page:
                # if payload['currentpage'] >= 10:
                    self.logger.info('\033[32mAll {currentpage} page done!\033[0m'.format(**payload))
                    break
                    
                payload['currentpage'] += 1

        print journal_done

        utils.text2sqlite3(self.__dict__['database'], out_xls)
        

def main():

    g = GetIF(**args)

    if args['update']:
        g.update_database()

    elif args['searchname']:
        g.get_impact_factor()

    else:
        parser.print_help()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='getIF',
        version='%(prog)s {}'.format(__version__),
        usage='%(prog)s <searchname> [options]',
        description='\t\033[1mget impact factor for given journal name\033[0m',
        epilog='contact: {0} < {0}@novogene.com> '.format(__author__),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('searchname', help='the input journal name', nargs='*')
    parser.add_argument(
        '-d',
        '--database',
        help='the database name of impact factor[default=%(default)s]',
        default=os.path.join(BASE_DIR, 'impact_factor.sqlite3'))

    parser.add_argument('-u', '--update', help='update the database from website', action='store_true')

    args = vars(parser.parse_args())

    main()
