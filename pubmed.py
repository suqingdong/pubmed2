#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import sys
import json
import argparse

try:
    import bs4
    import requests

    import django
    from django.conf import settings
    from django.template import loader
    from get_impact_factor import getIF
except ImportError:
    print (
        'This program needs some modules: bs4, requests, django, docopt\n'
        'You can use `pip install module_name` to install'
    )
    exit(1)


reload(sys)
sys.setdefaultencoding('utf8')

BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
PMC_URL = 'https://www.ncbi.nlm.nih.gov/pmc/articles/'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def configure_django():

    settings.configure(
        DEBUG=True,
        TEMPLATE_DEBUG=True,
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [
                    os.path.join(BASE_DIR, 'templates')
                ]
            }
        ]
    )
    django.setup()


class Pubmed(object):

    def __init__(self):

        self.term = args.get('term')
        self.retmax = args.get('retmax')
        self.format = args.get('out_format')
        self.out = args.get('out_prefix') or \
            self.term.strip().replace(' ', '_').replace('(', '').replace(')', '')
        self.title = ['pmid', 'title', 'pubdate', 'authors', 'abstract', 'journal', 'impact_factor', 'pmc']

    def start(self):

        if self.term.isdigit():
            pmids = [self.term]
            print 'Use pmids: {}'.format(pmids)
        else:
            pmids = self.get_pmids(self.term)
            if not pmids:
                print 'No pubmed for term: "{}"'.format(self.term)
                exit(0)
            print 'Found {} pmids: {}'.format(len(pmids), pmids)

        # pmids = ['17284678', '9997']
        # print pmids

        xml = self.get_info(pmids)

        results = self.parse_xml(xml)

        if self.format in ('xls', 'all'):
            with open(self.out + '.xls', 'w') as out:
                out.write('\t'.join(self.title) + '\n')
                for result in results:
                    linelist = [result[each] for each in self.title]
                    out.write('\t'.join(linelist) + '\n')
            print 'save result to: {}.xls'.format(self.out)

        if self.format in ('json', 'all'):
            with open(self.out + '.json', 'w') as out:
                json.dump(results, out, indent=2)
            print 'save result to: {}.json'.format(self.out)

        if self.format in ('html', 'all'):
            configure_django()
            template = loader.get_template('base.html')
            html = template.render({'results': results})
            with open(self.out + '.html', 'w') as out:
                out.write(html)
            print 'save result to: {}.html'.format(self.out)

    def get_pmids(self, term):

        # url = BASE_URL + 'esearch.fcgi?db=pubmed&retmode=json&term={term}&retmax={retmax}'.format(**self.__dict__)
        url = BASE_URL + 'esearch.fcgi'

        payload = {
            'db': 'pubmed',
            'retmode': 'json',
            'term': self.term,
            'retmax': self.retmax
        }

        return requests.get(url, params=payload).json()['esearchresult']['idlist']

    def get_info(self, pmids):

        url = BASE_URL + 'efetch.fcgi'

        payload = {
            'db': 'pubmed',
            'rettype': 'abstract',
            'id': ','.join(pmids)
        }

        return requests.get(url, params=payload).text

    def parse_xml(self, xml):

        results = []

        soup = bs4.BeautifulSoup(xml, 'lxml')

        for pubmedarticle in soup.select('pubmedarticle'):
            pmid = self.get_text(pubmedarticle, 'pmid')
            print '\033[31m> dealing with pmid: {}\033[0m'.format(pmid)
            pubdate = self.get_text(pubmedarticle, 'pubdate')
            title = self.get_text(pubmedarticle, 'articletitle')
            abstract = self.get_text(pubmedarticle, 'abstracttext')
            pmc = self.get_text(pubmedarticle, 'articleid[idtype="pmc"]')
            doi = self.get_text(pubmedarticle, 'articleid[idtype="doi"]')
            journal = self.get_text(pubmedarticle, 'journal isoabbreviation')
            journal_full = self.get_text(pubmedarticle, 'journal title')
            author_lastnames = pubmedarticle.select('authorlist author lastname')
            author_initials = pubmedarticle.select('authorlist author initials')
            authors = [' '.join([each[0].text, each[1].text]) for each in zip(author_lastnames, author_initials)]
            authors = ', '.join(authors)

            impact_factor = getIF(journal)

            context = {}
            for each in self.title:
                context.update({
                    each: locals()[each]
                })

            results.append(context)

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

    parser = argparse.ArgumentParser()

    parser.add_argument('term', help='The input term to search, could be like NCBI search format. eg: "(NGS) AND CVD"')
    parser.add_argument('-o', '--out-prefix', help='The prefix of the output filename')
    parser.add_argument('-m', '--retmax', help='The max count to return[default=%(default)s]', default='20')
    parser.add_argument('-O', '--out-format', help='The output format[default=%(default)s]', default='all', choices=['xls', 'html', 'json', 'all'])

    args = vars(parser.parse_args())

    main()
