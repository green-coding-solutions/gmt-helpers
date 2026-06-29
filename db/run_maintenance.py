#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=cyclic-import
import sys
import faulthandler
faulthandler.enable(file=sys.__stderr__)  # will catch segfaults and write to stderr

import os
import pprint

from lib import error_helpers
from lib.db import DB
from lib.job.base import Job
from lib.global_config import GlobalConfig

CURRENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':

    try:
        with open(os.path.join(CURRENT_DIR, 'queries_maintenance.sql'), encoding='utf-8') as f:
            content = f.read()

        results = []

        for query in content.split('\n######\n'):
            if query.strip() == '':
                continue

            print('Running query:', query)
            status = DB().query(query)
            print('Result:', status)
            results.append((query, status))

    except Exception as exception: #pylint: disable=broad-except
        error_helpers.log_error('Base exception occurred in GMT Helpers db/run_maintenance.py: ', exception=exception)
