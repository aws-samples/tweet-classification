# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3


class SqsHelper:

    def __init__(self, sqs_queue_url):
        self.sqs_client = boto3.client('sqs')
        self.sqs_queue_url = sqs_queue_url

    def send_tweet_to_sqs(self, stream_match):
        self.sqs_client.send_message(
            QueueUrl=self.sqs_queue_url,
            MessageBody=stream_match.to_tweet_json(),
            MessageAttributes={
                'matching_rule': {
                    'StringValue': stream_match.get_matching_rule(),
                    'DataType': 'String'
                }
            }
        )
