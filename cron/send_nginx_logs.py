#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=cyclic-import
import sys
import faulthandler
faulthandler.enable(file=sys.__stderr__)  # will catch segfaults and write to stderr

import re
from collections import defaultdict

from lib import error_helpers
from lib.job.base import Job
from lib.global_config import GlobalConfig

def parse_nginx_access_log(log_file):
    status_groups = defaultdict(lambda: defaultdict(int))

    log_pattern = re.compile(r'\S+ \S+ \S+ \[.*?\] "(.*?)" (\d+)')

    with open(log_file, 'r', errors='backslashreplace') as f:
        for line in f:
            match = log_pattern.search(line)
            if match:
                url, status = match.groups()
                status_groups[status][url.rsplit('?', maxsplit=1)[0]] += 1
            else:
                raise RuntimeError('Could not match line', line)

    buffer = []
    for status, urls in sorted(status_groups.items()):
        buffer.append(f"\n\nStatus Code {status}:")
        for url, count in sorted(urls.items(), key=lambda x: x[1], reverse=True):
            buffer.append(f"  {url}: {count}")


    return buffer


def parse_nginx_error_log(log_file):
    error_groups = defaultdict(int)

    log_pattern = re.compile(r'\S+ \S+ \S+ \S+ \S+ (.*)$')

    with open(log_file, 'r', errors='backslashreplace') as f:
        for line in f:
            match = log_pattern.search(line)
            if match:
                error = match.groups()
                error_groups[error] += 1
            else:
                raise RuntimeError('Could not match line', line)

    buffer = []
    buffer.append(f"Errors:")

    for group, count in sorted(error_groups.items()):
        buffer.append(f"  {group}: {count}")

    return buffer


if __name__ == '__main__':

    try:
        access_log_file = '/var/log/nginx/access.log.1'
        error_log_file = "/var/log/nginx/error.log.1"
        access_log = parse_nginx_access_log(access_log_file)
        error_log = parse_nginx_error_log(error_log_file)

        message = '\n'.join(access_log)
        message += '\n\n\n'
        message += '\n'.join(error_log)
        Job.insert(
            'email',
            user_id=0,
            email='arne@green-coding.io',
            name='NGINX Logs parsed',
            message=message
        )
    except Exception as exception: #pylint: disable=broad-except
        error_helpers.log_error('Base exception occurred in send_nginx_logs.py: ', exception=exception)
