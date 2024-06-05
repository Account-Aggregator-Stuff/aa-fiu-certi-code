import json
import urllib

import requests

from aggregator.helpers.utils import lamdaClient
from jose import jwk, jws

from aggregator.models import FIUEntity

def generate_token(fiu):
    try:
        client_id = fiu.fiu_client_id
        client_secret = fiu.fiu_client_secret
        grant_type = "client_credentials"

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": grant_type
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(fiu.fiu_token_url, data=urllib.parse.urlencode(data), headers=headers)

        if response.status_code == 200 and response.text:
            response = response.json()
            return response['access_token']
        return None
    except Exception as e:
        raise e


def generate_jws_detached(payload, fiu=None):
        # Your key data here
    copy = {'payload': payload, 'usecase': "SIGN"}
    copy_payload_json = json.dumps(copy)
    print (copy_payload_json)
    copy_payload_bytes = copy_payload_json.encode('utf-8')
    
    response = lamdaClient.invoke(
        FunctionName='test',
        InvocationType='RequestResponse',  # Can be 'Event' for asynchronous invocation
        Payload=copy_payload_bytes,
    )

    response_payload = response['Payload'].read()

    print ("Response Payload:", response_payload)

    return response_payload.decode('utf-8')[1:-1]

