#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=cyclic-import
import sys
import faulthandler
faulthandler.enable(file=sys.__stderr__)  # will catch segfaults and write to stderr

import re
from collections import defaultdict
from http import HTTPStatus

from lib import error_helpers
from lib.job.base import Job
from lib.global_config import GlobalConfig

STATUS_100_EXCLUDES = {
    'GET /v1/ci/badge/get',
    'GET / HTTP/1.1',
    'GET /v2/jobs',
    'GET /ci.html',
    'GET /v2/runs',
    'GET /robots.txt HTTP/1.1',
    'GET /stats.html',
    'GET /v1/machines HTTP/1.1',
    'GET /dist/js/jquery.min.js HTTP/1.1',
    'GET /dist/js/toast.min.js HTTP/1.1',
    'GET /js/helpers/main.js HTTP/1.1',
    'GET /dist/js/transition.min.js HTTP/1.1',
    'GET /js/helpers/config.js HTTP/1.1',
    'GET /dist/css/semantic_reduced.min.css HTTP/1.1',
    'GET /images/favicon.ico HTTP/1.1',
    'GET /css/green-coding.css HTTP/1.1',
    'GET /dist/themes/default/assets/fonts/icons.woff2 HTTP/1.1',
}

STATUS_202_EXCLUDES = {
    'POST /v2/carbondb/add HTTP/1.1',
    'POST /v2/hog/add HTTP/1.1',
    'POST /v3/ci/measurement/add HTTP/1.1',
    'POST /v2/ci/measurement/add HTTP/1.1',
}

STATUS_204_EXCLUDES = {
    'GET /v2/jobs',
    'GET /v1/ci/badge/get',
    'GET /v1/badge/single/[a-z0-9-]{36}',
}

STATUS_301_EXCLUDES = {'GET / HTTP/1.1'}
STATUS_307_EXCLUDES = {'GET / HTTP/1.1'}
STATUS_401_EXCLUDES = {'POST /v2/hog/add HTTP/1.1'}
STATUS_410_EXCLUDES = {'POST /v1/hog/add HTTP/1.1'}
STATUS_422_EXCLUDES = {'GET /v1/ci/badge/get'}


def _is_interesting_request(status, request, count):
    status_int = int(status)

    if status_int == 200:
        return count > 200
    if status_int == 100:
        return count > 50 and request not in STATUS_100_EXCLUDES
    if status_int == 202:
        return request not in STATUS_202_EXCLUDES
    if status_int == 204:
        return not any(re.fullmatch(pattern, request) for pattern in STATUS_204_EXCLUDES)
    if status_int == 206:
        return True
    if status_int == 301:
        return request not in STATUS_301_EXCLUDES
    if status_int == 304:
        return True
    if status_int == 307:
        return request not in STATUS_307_EXCLUDES
    if status_int == 400:
        return True
    if status_int == 401:
        return request not in STATUS_401_EXCLUDES
    if status_int == 410:
        return request not in STATUS_410_EXCLUDES
    if status_int == 404:
        return True
    if status_int == 422:
        return request not in STATUS_422_EXCLUDES
    if status_int == 444:
        return count > 150
    return False


def _is_critical_outside_rules(status, _request, _count):
    return int(status) >= 500


def _format_status_heading(status):
    try:
        HTTPStatus(int(status))  # can fail bc NGINX has custom HTTP codes like 499
    except Exception as e:
        print(e)
    return f'Status Code {status}:'


def parse_nginx_access_log(log_file, always, limit=0):
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

    interesting_groups = defaultdict(list)
    critical_groups = defaultdict(list)

    for status, urls in sorted(status_groups.items(), key=lambda item: int(item[0])):
        for url, count in sorted(urls.items(), key=lambda x: x[1], reverse=True):
            if count < limit:
                continue
            if _is_interesting_request(status, url, count):
                interesting_groups[status].append((count, url))
            elif _is_critical_outside_rules(status, url, count):
                critical_groups[status].append((count, url))

    buffer = []
    for status, entries in interesting_groups.items():
        if not entries:
            continue
        buffer.append(_format_status_heading(status))
        for count, url in entries:
            buffer.append(f'- {count}: {url}')
        buffer.append('')

    if critical_groups:
        buffer.append('Critical Findings Outside Rules:')
        for status, entries in critical_groups.items():
            if not entries:
                continue
            buffer.append(_format_status_heading(status))
            for count, url in entries:
                buffer.append(f'- {count}: {url}')
            buffer.append('')

    while buffer and buffer[-1] == '':
        buffer.pop()

    return buffer


def parse_nginx_error_log(log_file):
    buffer = ['Errors:']

    with open(log_file, 'r', errors='backslashreplace') as f:
        for line in f:
            if 'open()' in line and '(2: No such file or directory)' in line:
                continue
            buffer.append(line)

    return buffer


if __name__ == '__main__':

    try:
        access_log_file = '/var/log/nginx/access.log.1'
        error_log_file = '/var/log/nginx/error.log.1'
        access_log = parse_nginx_access_log(access_log_file, limit=5)
        error_log = parse_nginx_error_log(error_log_file)

        message = '\n'.join(access_log)
        message += '\n\n\n'
        message += '\n'.join(error_log)
        Job.insert(
            'email-simple',
            user_id=0,
            email=GlobalConfig().config['admin']['notification_email'],
            name='NGINX Logs parsed',
            message=message
        )
    except Exception as exception: #pylint: disable=broad-except
        error_helpers.log_error('Base exception occurred in send_nginx_logs.py: ', exception=exception)
