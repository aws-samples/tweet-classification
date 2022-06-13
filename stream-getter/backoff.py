# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import time

import requests


class Backoff:

    def __init__(self):
        self.wait_time = 0

    def wait_on_exception(self, exception):
        if isinstance(exception, requests.exceptions.HTTPError):
            if exception.response.status_code == 429:
                # Rate limit exceeded:
                # Start with a 1 minute wait and double each attempt.
                self.update_wait_time(60, 2, 3600)
            else:
                # Other HTTP errors:
                # Start with a 5 second wait, doubling each attempt, up to 320 seconds.
                self.update_wait_time(5, 2, 320)
        elif isinstance(exception, requests.exceptions.RequestException):
            # Increase the delay in reconnects by 250ms each attempt, up to 16 seconds.
            self.update_wait_time(.25, 1, 16)
        else:
            self.update_wait_time(1, 1, 1)
        logging.info(f'Sleeping for {self.wait_time} seconds...')
        time.sleep(self.wait_time)

    def update_wait_time(self, interval, multiplier, max_wait_time):
        if self.wait_time == 0:
            self.wait_time = interval
        else:
            self.wait_time = self.wait_time * multiplier if multiplier != 1 else self.wait_time + interval
        self.wait_time = self.wait_time if self.wait_time <= max_wait_time else max_wait_time

    def reset_wait_time(self):
        self.wait_time = 0
