#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import sys
import json
import datetime
import argparse
import codecs

try:
    import bs4
    import requests
    import colorama
    import django
    from django.conf import settings
    from django.template import loader
    from googletrans import Translator

    from get_impact_factor import get_impact_factor

except ImportError as e:
    print 'ImportError: \033[32m{}\033[0m'.format(e)
    print (
        'This program needs some modules: bs4, requests, fuzzywuzzy, django, googletrans, colorama, lxml\n'
        'You can use \033[32m` pip install module_name `\033[0m to install them'
    )
    exit(1)

__version__ = '2.3'
__author__ = 'suqingdong'
__email__ = 'suqingdong@novogene.com'

reload(sys)
sys.setdefaultencoding('utf8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [
                    BASE_DIR,
                    os.path.join(BASE_DIR, 'templates')
                ]
            }
        ]
    )
    django.setup()


def get_now_time(time_fmt='%Y-%m-%d %H:%M:%S'):

    return datetime.datetime.now().strftime(time_fmt)


class Pubmed(object):

    def __init__(self):

        self.term = args.get('term')
        self.retmax = args.get('retmax')
        self.format = args.get('out_format')
        self.min_factor = args['min_impact_factor']
        self.out = args.get('out_prefix') or \
            self.term.strip().replace(' ', '_').replace('(', '').replace(')', '')

        self.each_page_max = 100
        self.title = ['pmid', 'title', 'pubdate', 'authors', 'abstract', 'abstract_cn', 'journal', 'impact_factor', 'pmc']
        self.translator = Translator(service_urls=['translate.google.cn'])

        self.BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'

    def start(self):

        term_list = self.term.split(',')

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

        print '{fore_red}{back_yellow}[info] Use {length}{total_length} pmids:{back_reset}{fore_reset} {pmids}'.format(
            length=len(pmids),
            total_length=total_length,
            pmids=pmids
            if len(pmids) <= 10 else '[{}, ...]'.format(', '.join(pmids[:10])),
            **color_dict)

        # pmids = ['17284678', '9997']
        # print pmids

        xmls = self.get_xmls(pmids)

        results = self.parse_xml(xmls, pmids)

        if self.min_factor:
            print '{fore_yellow}Number of results(IF >= {mif}): {number}{fore_reset}'.format(
                time=get_now_time(), mif=self.min_factor, number=len(results), **color_dict)

        if self.format in ('xls', 'all'):
            with codecs.open(self.out + '.xls', 'w', encoding='gbk', errors='ignore') as out:
                out.write('\t'.join(self.title) + '\n')
                for result in results:
                    linelist = [result[each] for each in self.title]
                    out.write('\t'.join(linelist) + '\n')
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

            with codecs.open(self.out + '.html', 'w', encoding='utf8', errors='ignore') as out:
                out.write(html)

            print 'save result to: {}.html'.format(self.out)

    def get_pmids(self, term):

        url = self.BASE_URL + 'esearch.fcgi'

        payload = {
            'db': 'pubmed',
            'retmode': 'json',
            'term': term,
            'retmax': '65535'
        }

        return requests.get(url, params=payload).json()['esearchresult']['idlist']

    def get_xmls(self, pmids):

        url = self.BASE_URL + 'efetch.fcgi'

        for i in range(0, len(pmids), self.each_page_max):
            pmid_list = pmids[i:i+self.each_page_max]

            if i + self.each_page_max >= len(pmids):
                end = len(pmids)
            else:
                end = i + self.each_page_max
            print '{fore_green}===== dealing with pmids: {start} ~ {end}{fore_reset}'.format(start=i + 1, end=end, **color_dict)

            payload = {
                'db': 'pubmed',
                'rettype': 'abstract',
                'id': pmid_list
            }

            xml = requests.get(url, params=payload).text
            yield xml

    def parse_xml(self, xmls, pmids):

        results = []

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
                    time=get_now_time(), n=n, length=len(pmids), pmid=pmid, **color_dict)
                n += 1
                pubdate = self.get_text(pubmedarticle, 'pubdate')
                title = self.get_text(pubmedarticle, 'articletitle')
                abstract = self.get_text(pubmedarticle, 'abstracttext')
                abstract_cn = self.translator.translate(abstract, dest='zh-cn').text
                pmc = self.get_text(pubmedarticle, 'articleid[idtype="pmc"]')
                doi = self.get_text(pubmedarticle, 'articleid[idtype="doi"]')
                journal = self.get_text(pubmedarticle, 'journal isoabbreviation')
                journal_full = self.get_text(pubmedarticle, 'journal title')
                author_lastnames = pubmedarticle.select('authorlist author lastname')
                author_initials = pubmedarticle.select('authorlist author initials')
                authors = [' '.join([each[0].text, each[1].text]) for each in zip(author_lastnames, author_initials)]
                authors = ', '.join(authors)

                if os.path.exists('impact_factor.db'):
                    impact_factor = get_impact_factor(journal, 'impact_factor.db')
                else:
                    impact_factor = get_impact_factor(journal)

                if self.min_factor:
                    if (impact_factor == '.') or (float(impact_factor) < self.min_factor):
                        continue

                context = {}
                for each in self.title:
                    context.update({
                        each: locals()[each]
                    })

                results.append(context)

        print '{fore_green}[info {time}] all done!{fore_reset}'.format(time=get_now_time(), **color_dict)
        return results

    @staticmethod
    def get_text(soup, key):

        if soup.select(key):
            text = soup.select(key)[0].text.strip().replace('\n', '-')
            return text
        return '.'


def main():

    pubmed = Pubmed()
    pubmed.start()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='pubmed',
        version=__version__,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='contact: {} <{}>'.format(__author__, __email__))

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
        default='all',
        choices=['xls', 'html', 'json', 'all'])
    parser.add_argument(
        '-m',
        '--retmax',
        type=int,
        help='The max count to return[default=%(default)s], 0 for no limits',
        default=100)
    parser.add_argument(
        '-mif', '--min-impact-factor', type=float, help='The minimum of impact factor to save')

    args = vars(parser.parse_args())

    main()
