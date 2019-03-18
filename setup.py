#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
from setuptools import setup, find_packages

from pubmed2 import info

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

setup(
    name='pubmed2',
    version=info.__version__,
    author=info.__author__,
    author_email=info.__author_email__,
    description='search pubmeds quickly',
    long_description=open(os.path.join(BASE_DIR, 'README.rst')).read(),
    url='https://github.com/suqingdong/pubmed2',
    license='BSD License',
    install_requires=[
        'bs4',
        'requests',
        'xlwt',
        'colorama',
        'django',
        'googletrans',
        'fuzzywuzzy',
        'python-Levenshtein',
    ],
    packages=find_packages(),
    include_package_data=True,
    scripts=['pubmed2/pubmed.py'],
    entry_points = {  
        'console_scripts': [  
            'pubmed = pubmed2.pubmed:main'  
        ]  
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries'
    ],
)