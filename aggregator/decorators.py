import json
import os
import uuid
from datetime import datetime
from django.http import JsonResponse

import requests
from rest_framework import status
from rest_framework.response import Response

from aggregator.auth.jws import generate_jws_detached
from aggregator.globals.config import API_VERSION
from aggregator.helpers.encoding_decoding import base64url_decode
from aggregator.middlewares.JWSMiddleware import JWSMiddleware
from aggregator.models import FIUEntity
from filelogging import logger
from functools import wraps

crRegistryBaseUrl = os.getenv("CR_BASE_URL")


def fiu_token_required(f):
    @wraps(f)
    def decorated(request, *args, **kwargs):
        token = request.headers.get('FIU-Auth-Token')
        if not token:
            return JsonResponse({'error': 'FIU-Auth-Token is missing from headers'}, status=401)
        try:
            fiu = FIUEntity.objects.get(pyro_token=token)  # Adjust to match your model and field names
            request.fiu = fiu  # Attach the FIU object to the request
        except FIUEntity.DoesNotExist:
            return JsonResponse({'error': 'Invalid FIU-Auth-Token'}, status=401)

        return f(request, *args, **kwargs)
    return decorated


def jws_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        response = JWSMiddleware().process_request(request)
        logger.warning(request.data)
        logger.warning(request.headers)
        if response is not None:
            response_data = {
                "ver": API_VERSION,
                "timestamp": datetime.now().isoformat(),
                "txnid": str(uuid.uuid4()),
                "errorMsg": "Error code specific error message",
                "errorCode": "SignatureDoesNotMatch"
            }
            status_code = status.HTTP_400_BAD_REQUEST
            payload = json.dumps(response_data, separators=(',', ':'))
            jws = generate_jws_detached(payload)
            return Response(response_data, status=status_code)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def access_token(view_func):
    def _wrapped_view(request, *args, **kwargs):
        aa_api_key = request.headers.get('Aa-Api-Key', "")
        print ("AA API KEY in Notification Request: ", aa_api_key)
        try:
            headers = {"Authorization": "Bearer " + aa_api_key}
            response = requests.request("GET", crRegistryBaseUrl+ '/entityInfo/AA', headers=headers)
            if response.status_code == status.HTTP_401_UNAUTHORIZED:
                # print (response.json())
                response_data = {
                    "ver": API_VERSION,
                    "timestamp": datetime.now().isoformat(),
                    "txnid": str(uuid.uuid4()),
                    "errorMsg": "Error code specific error message",
                    "errorCode": "Unauthorized"
                }
                status_code = status.HTTP_401_UNAUTHORIZED
                payload = json.dumps(response_data, separators=(',', ':'))
                jws = generate_jws_detached(payload)
                print ("Unauthorized Request.. AA NOT VERIFIED")
                return Response(response_data, status=status_code, headers={"x-jws-signature": jws})
            elif response.status_code == status.HTTP_200_OK:
                payload = aa_api_key.split('.')[1]
                decoded_str = base64url_decode(payload)
                decoded_json = json.loads(decoded_str)
                aa = decoded_json['azp']

                if aa != 'SUMASOFTAA-1':
                    response_data = {
                        "ver": API_VERSION,
                        "timestamp": datetime.now().isoformat(),
                        "txnid": str(uuid.uuid4()),
                        "errorMsg": "Error code specific error message",
                        "errorCode": "InvalidRequest"
                    }
                    status_code = status.HTTP_400_BAD_REQUEST
                    payload = json.dumps(response_data, separators=(',', ':'))
                    jws = generate_jws_detached(payload)
                    print ("Unauthorized Request.. AA IS NOT SUMASOFTAA-1")
                    return Response(response_data, status=status_code, headers={"x-jws-signature": jws})
        except Exception as e:
            response_data = {
                        "ver": API_VERSION,
                        "timestamp": datetime.now().isoformat(),
                        "txnid": str(uuid.uuid4()),
                        "errorMsg": "Error code specific error message",
                        "errorCode": "InvalidRequest"
                    }
            return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
            print(e.with_traceback())
        return view_func(request, *args, **kwargs)

    return _wrapped_view
