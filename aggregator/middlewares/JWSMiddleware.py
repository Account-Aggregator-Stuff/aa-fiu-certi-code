import json
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

from aggregator.helpers.utils import validate_jws_signature, lamdaClient


class JWSMiddleware():
    def process_request(self, request):
        if request.method == 'POST':
            x_jws_signature = request.headers.get('X-Jws-Signature')
            print (x_jws_signature)
            if not x_jws_signature:
                return JsonResponse({'error': 'Missing x-jws-signature header'}, status=400)

            try:
                # if(request.body['ver'] != '1.1.2'):
                #     return JsonResponse({'error': 'Invalid version'}, status=400)
                data = json.loads(request.body)
                print ("Request headers of Notification: ", request.headers)
                print ("Request data of Notification: ", data)
                # if(data['ver'] != '1.1.2'):
                #     return JsonResponse({'error': 'Invalid version'}, status=400)
                # payload = json.dumps(data, separators=(',', ':'))
                copy = {'payload': data, 'usecase': "Verification", "signature": x_jws_signature}
                copy_payload_json = json.dumps(copy)
                # print ("copy payload in notification request: ", copy_payload_json)
                copy_payload_bytes = copy_payload_json.encode('utf-8')
                response = lamdaClient.invoke(
                    FunctionName='test',
                    InvocationType='RequestResponse',  # Can be 'Event' for asynchronous invocation
                    Payload=copy_payload_bytes,
                )
                response_payload = response['Payload'].read()
                valid = response_payload.decode('utf-8')[1:-1]
                print ("Notification response from lambda verification: ", response_payload)
                if valid != 'True':
                    return JsonResponse({'error': 'Invalid JWS signature'}, status=403)

            except (KeyError, ValueError):
                return JsonResponse({'error': 'Invalid request data'}, status=400)
        return None

    def process_response(self, response, decode_json=None):
        # print (response.headers)
        x_jws_signature = response.headers.get('x-jws-signature')
        if not x_jws_signature:
            return JsonResponse({'error': 'Missing x-jws-signature header'}, status=400)

        try:
            if decode_json is not None:
                data = decode_json
            else:
                data = response.json()
            
            print ("JWS Verfication of Response: ", data)
            payload = json.dumps(data, separators=(',', ':'))
            # sign = request.headers.get('Aa-Api-Key')

            copy = {'payload': payload, 'usecase': "Verification", "signature": x_jws_signature}
            copy_payload_json = json.dumps(copy)
            copy_payload_bytes = copy_payload_json.encode('utf-8')
            # print ("copy payload in API response: ", copy_payload_json)
            response = lamdaClient.invoke(
                FunctionName='test',
                InvocationType='RequestResponse',  # Can be 'Event' for asynchronous invocation
                Payload=copy_payload_bytes,
            )
            response_payload = response['Payload'].read()
            valid = response_payload.decode('utf-8')[1:-1]
            print ("Response from lambda verification: ", response_payload)
            if valid != 'True':
                return JsonResponse({'error': 'Invalid JWS signature'}, status=403)

        except (KeyError, ValueError):
            return JsonResponse({'error': 'Invalid request data'}, status=400)

        return None
