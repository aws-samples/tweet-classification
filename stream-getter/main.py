# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
import os
import queue
import threading

import requests

from backoff import Backoff
from sqs_helper import SqsHelper
from stream_match import StreamMatch

BEARER_TOKEN = os.environ.get('BEARER_TOKEN')
REQUEST_CONNECT_TIMEOUT_SECONDS = 4
REQUEST_READ_TIMEOUT_SECONDS = 30  # Twitter sends 20-second keep alive heartbeats
STREAM_QUERY_PARAMS = 'tweet.fields=created_at,source&expansions=author_id&user.fields=username'

matches_queue = queue.SimpleQueue()


def bearer_oauth(r):
    r.headers['Authorization'] = f'Bearer {BEARER_TOKEN}'
    r.headers['User-Agent'] = 'v2FilteredStreamPython'
    return r


def get_tweets_from_twitter():
    backoff = Backoff()
    while True:
        try:
            response = requests.get(
                f'https://api.twitter.com/2/tweets/search/stream?{STREAM_QUERY_PARAMS}',
                auth=bearer_oauth,
                stream=True,
                timeout=(REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS)
            )
            response.raise_for_status()
            logging.info('Connected to the Twitter stream')
            backoff.reset_wait_time()
            for line in response.iter_lines():
                if line:
                    logging.info('New match!')
                    decoded_line = line.decode('utf-8')
                    logging.info(decoded_line)
                    matches_queue.put(StreamMatch(decoded_line))
        except Exception as exception:
            logging.error(exception, exc_info=True)
            backoff.wait_on_exception(exception)
            continue


def send_tweets_to_sqs(sqs_helper):
    backoff = Backoff()
    while True:
        try:
            stream_match = matches_queue.get()
            if stream_match.has_errors():
                logging.info('Skipping error')
            else:
                logging.info('Sending tweet to SQS')
                sqs_helper.send_tweet_to_sqs(stream_match)
                logging.info('Tweet sent to SQS')
        except Exception as exception:
            logging.error(exception, exc_info=True)
            backoff.wait_on_exception(exception)
            continue


def main():
    sqs_helper = SqsHelper(os.environ.get('SQS_QUEUE_URL'))
    producer = threading.Thread(target=get_tweets_from_twitter)
    consumer = threading.Thread(target=send_tweets_to_sqs, args=[sqs_helper])
    producer.start()
    consumer.start()
    producer.join()
    consumer.join()


if __name__ == '__main__':
    logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'WARNING').upper())
    main()
