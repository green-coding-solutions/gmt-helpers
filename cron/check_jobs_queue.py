#!/usr/bin/env python3

import sys
import faulthandler
faulthandler.enable(file=sys.__stderr__)  # will catch segfaults and write to stderr

import os
import argparse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from lib.global_config import GlobalConfig
from lib.db import DB
from lib import error_helpers
from lib.job.base import Job

"""
    This file checks the jobs queue for overdue jobs which might need admin attention to check if processing of the cluster is blocked / delayed
"""

def check_queue(hours=6):
    query = """
        SELECT id, name
        FROM jobs
        WHERE type = 'run' AND state = 'WAITING' AND created_at <= CURRENT_TIMESTAMP - make_interval(hours => %s)
       """
    data = DB().fetch_all(query, params=(hours, ))

    errors = []
    for [job_id, name] in data:
        errors.append(f"Name {name}; ID: {job_id}")

    if errors:
        Job.insert(
            'email-simple',
            user_id=0,
            email=GlobalConfig().config['admin']['notification_email'],
            name=f"Jobs in queue are waiting for longer than {hours} hours",
            message='\n'.join(errors)
        )
    else:
        print('All good. Nothing to alert ...')


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('hours', type=int, help='Amount of hours for waiting jobs from which an alert shall be issued')

        args = parser.parse_args()  # script will exit if arguments not present

        check_queue(args.hours)

    except Exception as exc: # pylint: disable=broad-except
        error_helpers.log_error(f'Processing in {__file__} failed.', exception=exc, machine=GlobalConfig().config['machine']['description'])
