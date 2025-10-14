import boto3
import json

sts = boto3.client("sts")

def handler(event, context):
    identity = sts.get_caller_identity()

    i = 5
    j = 2
    k = i + j

    return {
        "statusCode": 200,
        "body": "HELLO WORLD " + json.dumps(identity)
    }