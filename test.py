#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import sys

import django
from django.conf import settings
from django.template import loader, Context


reload(sys)
sys.setdefaultencoding('utf8')


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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


print settings.default_settings

data = {'name': 'roronoa zoro', 'age': 20}

template = loader.get_template('base.html')

print template.render(data)
