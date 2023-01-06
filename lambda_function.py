import json
from roulette import processRequest

def lambda_handler(event, context):
    
        result = processRequest(event)
        return json.loads(result)
