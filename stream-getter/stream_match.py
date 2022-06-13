# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json


class StreamMatch:

    def __init__(self, content):
        self.content = content

    def to_tweet_json(self):
        input_object = json.loads(self.content)
        user = next(filter(lambda x: x['id'] == input_object['data']['author_id'], input_object['includes']['users']))
        output_object = {
            'text': input_object['data']['text'],
            'user': user['username'],
            'created_at': input_object['data']['created_at'],
            'source': input_object['data']['source']
        }
        return json.dumps(output_object, ensure_ascii=False)

    def get_matching_rule(self):
        input_object = json.loads(self.content)
        matching_rule = input_object['matching_rules'][0]['tag']
        return matching_rule

    def has_errors(self):
        return 'errors' in json.loads(self.content)
