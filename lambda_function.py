import json
from roulette import process_request


def lambda_handler(event, context):
    result = process_request(event)
    return json.loads(result)
