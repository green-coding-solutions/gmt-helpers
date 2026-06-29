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

        affected = [(q, s) for q, s in results if s and not s.endswith(' 0')]

        if affected:
            message = 'Maintenance queries with affected rows:\n\n'
            for query, status in affected:
                message += f"Status: {status}\nQuery:\n{query}\n\n"
            Job.insert(
                'email-simple',
                user_id=0,
                email=GlobalConfig().config['admin']['notification_email'],
                name='DB maintenance summary',
                message=message
            )

    except Exception as exception: #pylint: disable=broad-except
        error_helpers.log_error('Base exception occurred in GMT Helpers db/run_maintenance.py: ', exception=exception)
