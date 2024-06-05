import json

import boto3
import jwt
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.http import JsonResponse

aws_access_key_id = ""
aws_secret_access_key = ""

lamdaClient = boto3.client('lambda', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,
                           region_name='ap-south-1')

def validate_jws_signature(encoded_header, encoded_payload, encoded_signature, certificate_json):
    cert_data = json.loads(certificate_json)

    n = int.from_bytes(base64.urlsafe_b64decode(cert_data['n'] + '=='), 'big')
    e = int.from_bytes(base64.urlsafe_b64decode(cert_data['e'] + '=='), 'big')
    public_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())

    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    jws_token = f"{encoded_header}.{encoded_payload}.{encoded_signature}"

    try:
        jwt.decode(jws_token, pem, algorithms=[cert_data['alg']], options={"verify_signature": True})

        print("Signature is valid.")
        return True
    except jwt.InvalidTokenError as e:
        print(f"Token validation error: {e}")
        return False
    

def create_response(status_code=200, message=None, error=None, data=None):
    response_data = {
        'status_code': status_code,
        'data': data or {},
    }

    if message:
        response_data['message'] = message

    if error:
        response_data['error'] = error

    return JsonResponse(response_data, status=status_code)
