#!/usr/bin/env python2
# -*- coding=utf-8 -*-
'''
    search pubmeds quickly
'''
import os
import re
import sys
import json
import time
import datetime
import argparse
import textwrap
import codecs

import bs4
import requests
import colorama
import django
import xlwt
from django.conf import settings
from django.template import loader
from googletrans import Translator


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))


from pubmed2.tools import GetIF, try_again

from pubmed2.info import __version__, __author__, __author_email__


reload(sys)
sys.setdefaultencoding('utf8')

colorama.init()

color_dict = {
    'fore_reset': colorama.Fore.RESET,
    'back_reset': colorama.Back.RESET,
    'fore_red': colorama.Fore.RED,
    'fore_green': colorama.Fore.GREEN,
    'fore_cyan': colorama.Fore.CYAN,
    'fore_yellow': colorama.Fore.YELLOW,
    'back_yellow': colorama.Back.YELLOW,
    'style_bright': colorama.Style.BRIGHT,
}


def configure_django():

    settings.configure(
        DEBUG=True,
        TEMPLATE_DEBUG=True,
        TEMPLATES=[{
            'BACKEND':
            'django.template.backends.django.DjangoTemplates',
            'DIRS': [BASE_DIR, os.path.join(BASE_DIR, 'templates')]
        }])
    django.setup()


def get_now_time(time_fmt='%Y-%m-%d %H:%M:%S'):

    return datetime.datetime.now().strftime(time_fmt)


class Pubmed(object):

    def __init__(self, **args):

        self.args = args
        self.term = args.get('term')
        self.retmax = args.get('retmax')
        self.format = args.get('out_format')
        self.min_factor = args['min_impact_factor']
        self.out = args.get('out_prefix') or \
            re.sub(r' |\(|\)|/', '_', self.term.strip()).strip('_')

        self.each_page_max = args['page_size']
        self.encoding = args['encoding']
        self.start_point = args['start_point']

        self.not_trans = args['not_translate']

        self.title = args['title'].split(',')

        self.translator = Translator(service_urls=['translate.google.cn'])
        self.BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        self.timeout = 60

    def start(self):

        for field in self.title:
            if field not in default_title:
                print '[error] invalid title field "{}"\nyou can only choose from {}'.format(field, default_title)
                exit(1)

        if self.not_trans and 'abstract_cn' in self.title:
            self.title.pop(self.title.index('abstract_cn'))

        if self.min_factor == -1 and 'impact_factor' in self.title:
            self.title.pop(self.title.index('impact_factor'))

        # print 'output title: {}'.format(self.title)

        # term_list = self.term.split(',')
        term_list = re.split(r',|\s+|;', self.term)

        total_length = ''
        if self.term.isdigit():
            pmids = [self.term]
        elif all([each.isdigit() for each in term_list]):
            pmids = term_list
            self.out = '{}_{}'.format(pmids[0], pmids[-1])
        elif os.path.isfile(self.term):
            with open(self.term) as f:
                pmids = [line.strip() for line in f]
        else:
            total_pmids = self.get_pmids(self.term)
            if self.retmax == 0 or len(total_pmids) <= self.retmax:
                pmids = total_pmids
            else:
                pmids = total_pmids[:self.retmax]
                total_length = '/{}'.format(len(total_pmids))

        if not pmids:
            print '{fore_red}[error {time}] No pubmed for term: "{term}"{fore_reset}'.format(
                time=get_now_time(), term=self.term, **color_dict)
            exit(0)

        print '{fore_red}{back_yellow}Use {length}{total_length} pmids:{back_reset}{fore_reset} {pmids}'.format(
            length=len(pmids),
            total_length=total_length,
            pmids=pmids
            if len(pmids) <= 10 else '[{}, ...]'.format(', '.join(pmids[:10])),
            **color_dict)

        if self.start_point < len(pmids):
            print 'start craw from the {}st pmid'.format(self.start_point)
            pmids = pmids[self.start_point - 1:]

        xmls = self.get_xmls(pmids)

        # results = self.parse_xml(xmls, pmids)
        # results = [result for result in self.parse_xml(xmls, pmids)]
        results = self.parse_xml(xmls, pmids)

        result_len = self.save_result(results)

        if self.min_factor:
            print '{fore_yellow}\nNumber of results(IF>={mif}): {number}{fore_reset}'.format(
                time=get_now_time(),
                mif=self.min_factor,
                number=result_len,
                **color_dict)

    def save_result(self, results):

        # write from generator
        if self.format == 'xls':
            with codecs.open(
                    self.out + '.xls',
                    'w',
                    encoding=self.encoding,
                    errors='ignore') as out:
                out.write('\t'.join(self.title) + '\n')
                for num, result in enumerate(results):
                    linelist = [result[each] for each in self.title]
                    out.write('\t'.join(linelist) + '\n')
            print 'save result to: {}.xls'.format(self.out)
            return num + 1

        # otherwise, convert generator to list
        results = list(results)

        if self.format in ('xls', 'all'):
            with codecs.open(
                    self.out + '.xls',
                    'w',
                    encoding=self.encoding,
                    errors='ignore') as out:
                out.write('\t'.join(self.title) + '\n')
                for result in results:
                    linelist = [result[each] for each in self.title]
                    out.write('\t'.join(linelist) + '\n')
            print 'save result to: {}.xls'.format(self.out)

        if self.format in ('xlsx', 'all'):
            wb = xlwt.Workbook()
            ws = wb.add_sheet('result')


            # align: wrap yes,vert centre, horiz left;
            # font: name Arial, bold True, height 200;
            # pattern: pattern solid,fore-colour light_yellow;

            header_style = xlwt.easyxf('''
                font: name Times New Roman, bold on, height 200;
                pattern: pattern solid, fore-colour white;
            ''')

            row_styles = [
                xlwt.easyxf('pattern: pattern solid, fore-colour light_green;'),
                xlwt.easyxf('pattern: pattern solid, fore-colour light_yellow;')
            ]

            row = 0
            col = 0
            for name in self.title:
                ws.write(row, col, name.upper(), header_style)
                col += 1
            row += 1

            for each in results:
                col = 0
                for name in self.title:
                    value = each[name]
                    if name == 'impact_factor' and value != '.':
                        value = float(value)
                    ws.write(row, col, value, row_styles[row % 2])
                    col += 1
                row += 1

            if 'abstract_cn' in self.title:
                ws.col(self.title.index('abstract_cn')).width = 256 * 50

            wb.save(self.out + '.xls')

            print 'save result to: {}.xls'.format(self.out)

        if self.format in ('json', 'all'):
            with open(self.out + '.json', 'w') as out:
                # with codecs.open(self.out + '.json', 'w', encoding='utf8', errors='ignore') as out:
                json.dump(results, out, indent=2, ensure_ascii=False)
            print 'save result to: {}.json'.format(self.out)

        if self.format in ('html', 'all'):
            configure_django()
            template = loader.get_template('index.html')
            html = template.render({'results': results})
            # html = template.render({'results': json.dumps(results).replace("'", "\\'")})

            with codecs.open(
                    self.out + '.html', 'w', encoding='utf8',
                    errors='ignore') as out:
                out.write(html)

            print 'save result to: {}.html'.format(self.out)

        return len(results)

    @try_again()
    def get_response(self, url, **kwargs):

        return requests.get(url, **kwargs)


    @try_again()
    def get_pmids(self, term):

        url = self.BASE_URL + 'esearch.fcgi'

        payload = {
            'db': 'pubmed',
            'retmode': 'json',
            'term': term,
            'retmax': '65535'
        }

        return self.get_response(
            url, params=payload,
            timeout=self.timeout).json()['esearchresult']['idlist']

    @try_again()
    def get_xmls(self, pmids):

        url = self.BASE_URL + 'efetch.fcgi'

        for i in range(0, len(pmids), self.each_page_max):
            pmid_list = pmids[i:i + self.each_page_max]

            if i + self.each_page_max >= len(pmids):
                end = len(pmids)
            else:
                end = i + self.each_page_max
            print '{fore_green}===== dealing with pmids: {start} ~ {end}{fore_reset}'.format(
                start=i + 1, end=end, **color_dict)

            payload = {'db': 'pubmed', 'rettype': 'abstract', 'id': pmid_list}

            xml = self.get_response(url, params=payload, timeout=self.timeout).text
            yield xml

    @try_again(10)
    def translate(self, text):

        return self.translator.translate(text, dest='zh-cn').text

    @try_again()
    def parse_xml(self, xmls, pmids):

        # results = []

        n = 1
        for xml in xmls:
            try:
                soup = bs4.BeautifulSoup(xml, 'lxml')
            except Exception:
                print '[warn] lxml was not installed, use html.parser instead'
                soup = bs4.BeautifulSoup(xml, 'html.parser')

            for pubmedarticle in soup.select('pubmedarticle'):
                pmid = self.get_text(pubmedarticle, 'pmid')
                print '{fore_cyan}[info {time}] {n}/{length} dealing with pmid: {pmid}{fore_reset}'.format(
                    time=get_now_time(),
                    n=n,
                    length=len(pmids),
                    pmid=pmid,
                    **color_dict)
                n += 1
                pubdate = self.get_text(pubmedarticle, 'pubdate')
                title = self.get_text(pubmedarticle, 'articletitle')
                abstract = self.get_text(pubmedarticle, 'abstracttext')

                if 'abstract_cn' in self.title:
                    abstract_cn = self.translate(abstract)

                pmc = self.get_text(pubmedarticle, 'articleid[idtype="pmc"]')
                doi = self.get_text(pubmedarticle, 'articleid[idtype="doi"]')
                journal = self.get_text(pubmedarticle, 'journal isoabbreviation')
                journal_full = self.get_text(pubmedarticle, 'journal title')
                issn = self.get_text(pubmedarticle, 'journal issn')
                author_lastnames = pubmedarticle.select(
                    'authorlist author lastname')
                author_initials = pubmedarticle.select(
                    'authorlist author initials')
                authors = [
                    ' '.join([each[0].text, each[1].text])
                    for each in zip(author_lastnames, author_initials)
                ]
                authors = ', '.join(authors)

                pubtype = pubmedarticle.select(
                    'publicationtypelist publicationtype')
                pubtype = '|'.join([each.text for each in pubtype])

                if 'impact_factor' in self.title:
                    impact_factor = GetIF().get_impact_factor(searchname=journal, database=self.args['database']) or '.'

                    if self.min_factor:
                        if (impact_factor == '.') or (float(impact_factor) < self.min_factor):
                            continue

                context = {}
                for each in self.title:
                    context.update({each: locals()[each]})

                yield context
                # results.append(context)

        print '{fore_green}[info {time}] all pmids done!{fore_reset}\n'.format(
            time=get_now_time(), **color_dict)
        # return results

    @staticmethod
    def get_text(soup, key):

        if soup.select(key):
            text = soup.select(key)[0].text.strip().replace('\n', '-')
            return text
        return '.'


def main():

    global default_title
    default_title = ['pmid', 'title', 'pubdate', 'authors', 'abstract', 'abstract_cn', 'journal', 'impact_factor', 'pmc', 'doi', 'pubtype', 'issn']

    epilog = '''
    example: \033[36mpython pubmed.py 'ngs AND disease'
             python pubmed.py '(LVNC) AND (mutation OR variation)' -m 50 -mif 5\033[0m

    contact: {} <{}>
    '''.format(__author__, __author_email__)

    parser = argparse.ArgumentParser(
        prog='pubmed',
        version=__version__,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.dedent(epilog))

    parser.add_argument(
        'term',
        help=(
            '{fore_green}The input term to search\n'
            'could be like NCBI search format. eg: "(NGS) AND CVD"\n'
            'or pmid. eg: 25261758\n'
            'or pmids. eg: 25261758,24564649,24191723\n'
            'or a file contains pmids, one pmid per line{fore_reset}').format(
                **color_dict))
    parser.add_argument(
        '-o', '--out-prefix', help='The prefix of the output filename')
    parser.add_argument(
        '-O',
        '--out-format',
        help='The output format[default=%(default)s]',
        default='xlsx',
        choices=['xls', 'xlsx', 'html', 'json', 'all'])
    parser.add_argument(
        '-m',
        '--retmax',
        type=int,
        help='The max count to return[default=%(default)s], 0 for no limits',
        default=100)
    parser.add_argument(
        '-p',
        '--page-size',
        type=int,
        help='The max number of each page to craw[default=%(default)s]',
        default=100)
    parser.add_argument(
        '-enc',
        '--encoding',
        help='The encoding of output xls file[default="%(default)s"]',
        default='gbk',
        choices=['gbk', 'utf8', 'utf-8'])
    parser.add_argument(
        '-mif',
        '--min-impact-factor',
        type=float,
        help='The minimum of impact factor to save, -1 for no impact_factor')
    parser.add_argument(
        '-start',
        '--start-point',
        type=int,
        help='The start point for all pmids',
        default=1)
    parser.add_argument(
        '-nt',
        '--not-translate',
        action='store_true',
        help='Do not translate abstract')
    parser.add_argument(
        '-t',
        '--title',
        help='The title to craw\n'
        'you can choose one or more from [%(default)s]\n'
        'and separate by ","',
        default=','.join(default_title))
    parser.add_argument(
        '-d',
        '--database',
        help='the impact factor database[default=%(default)s]',
        default=os.path.join(BASE_DIR, 'tools', 'impact_factor.sqlite3'))

    args = vars(parser.parse_args())

    print 'searching term: "{}"'.format(args['term'])

    start = time.time()

    pubmed = Pubmed(**args)
    pubmed.start()

    end = time.time()

    print '\nTotal time: {:.2f}s'.format(end - start)


if __name__ == "__main__":

    main()