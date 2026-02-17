#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=cyclic-import
import sys
import faulthandler
faulthandler.enable(file=sys.__stderr__)  # will catch segfaults and write to stderr

import os

from lib import error_helpers
from lib.db import DB
from lib.job.base import Job
from lib.global_config import GlobalConfig

CURRENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':

    try:
        with open(os.path.join(CURRENT_DIR, 'queries_check_empty.sql'), encoding='utf-8') as f:
            content = f.read()

        for query in content.split('\n######\n'):
            if query.strip() == '':
                continue

            print('Running query:', query)
            data = DB().fetch_all(query)
            if data:
                Job.insert(
                    'email-simple',
                    user_id=0,
                    email=GlobalConfig().config['admin']['error_email'],
                    name='Query returned non empty result',
                    message=f"Query: {query}\n\nData: {data}"
                )

        with open(os.path.join(CURRENT_DIR, 'queries_info.sql'), encoding='utf-8') as f:
            content = f.read()

        for query in content.split('\n######\n'):
            if query.strip() == '':
                continue

            print('Running query:', query)
            data = DB().fetch_all(query)

            if data:
                Job.insert(
                    'email-simple',
                    user_id=0,
                    email=GlobalConfig().config['admin']['notification_email'],
                    name='Info query',
                    message=f"Query: {query}\n\nData: {data}"
                )

    except Exception as exception: #pylint: disable=broad-except
        error_helpers.log_error('Base exception occurred in GMT Helpers db/check_consistency.py: ', exception=exception)
