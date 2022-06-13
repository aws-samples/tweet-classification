# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os

import boto3

from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, batch_processor

MIN_SCORE = 0.70
DEFAULT_LABEL = 'other'

sns_client = boto3.client('sns')
sagemaker = boto3.client('runtime.sagemaker')
processor = BatchProcessor(event_type=EventType.SQS)
logging.getLogger().setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())


def publish_alert_message(item):
    logging.info('Publishing alert in SNS')
    message = json.dumps(item, ensure_ascii=False)
    sns_client.publish(TargetArn=os.environ['SNS_TOPIC_ARN'], Message=message)


def categorize_tweet(tweet):
    endpoint_name = os.environ['ENDPOINT_NAME']
    labels = os.environ['LABELS'].split(',')
    logging.info(f'Invoking endpoint {endpoint_name} with the following labels: {labels}')
    data = {
        'inputs': tweet,
        'parameters': {
            'candidate_labels': labels,
            'multi_class': False
        }
    }
    response = sagemaker.invoke_endpoint(EndpointName=endpoint_name,
                                         ContentType='application/json',
                                         Body=json.dumps(data))
    logging.info(response)

    response_body = json.loads(response['Body'].read())
    score = max(response_body['scores'])
    if score > MIN_SCORE:
        label_index = response_body['scores'].index(score)
        label = response_body['labels'][label_index]
    else:
        label = DEFAULT_LABEL
        score = 0
    score_by_labels = dict(zip(response_body['labels'], response_body['scores']))
    score_by_labels_str = json.dumps(score_by_labels, ensure_ascii=False)
    logging.info(f'Category: {label}\nScore: {score}\nScores: {score_by_labels_str}')
    return label, score, score_by_labels_str


def should_notify(item):
    return item['category_type'] != DEFAULT_LABEL


def process_item(item):
    tweet = item['text']
    logging.info(f'Tweet: {tweet}')
    item['category_type'], item['category_type_score'], item['category_type_model_result'] = \
        categorize_tweet(tweet)
    item['notification'] = should_notify(item)
    logging.info("The processed tweet")
    logging.info(item)


def record_handler(record):
    message_body = record.body

    if message_body:
        logging.info('SQS message body:')
        logging.info(message_body)
        item = json.loads(message_body, strict=False)
        process_item(item)

        if 'notification' in item and item['notification']:
            publish_alert_message(item)
        else:
            logging.info('Will not publish an alert')


@batch_processor(record_handler=record_handler, processor=processor)
def handler(_event, _context):
    return processor.response()
