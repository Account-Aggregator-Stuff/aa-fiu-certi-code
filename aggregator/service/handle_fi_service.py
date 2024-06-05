import datetime
import os
import uuid

import requests

from aggregator.auth.jws import generate_jws_detached, generate_token
from aggregator.globals.config import API_VERSION
from aggregator.helpers.json_schema_checker import validate_json, json_schema_for_get_fi_handle
from aggregator.helpers.time_utils import validate_given_time
from aggregator.middlewares.JWSMiddleware import JWSMiddleware
from aggregator.models import FIDataRequest, FIUEntity, SessionDetails
import boto3

from settings import AWS_ACCESS_KEY_ID, AWS_S3_CUSTOM_DOMAIN, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
import base64
import xmltodict
import json

def decode_and_parse_xml(encoded_xml_data):
    # Step 1: Decode the data (assuming it's base64 encoded)
    decoded_data = base64.b64decode(encoded_xml_data)

    # Step 2: Parse the XML
    parsed_data = xmltodict.parse(decoded_data)

    return parsed_data

def save_to_s3(file_name, data):
    s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    s3_client.put_object(Bucket=AWS_STORAGE_BUCKET_NAME, Key=file_name, Body=data)
    return f"https://{AWS_S3_CUSTOM_DOMAIN}/{file_name}"


def decrypt_data(encrypted_data, your_nonce, remote_nonce, your_private_key, remote_key_material):
    url = 'https://rahasya.setu.co/ecc/v1/decrypt'

    print (remote_nonce, your_nonce, your_private_key, remote_key_material)
    payload = {
        "base64Data": encrypted_data,  # The encrypted FI data in base64 format
        "base64RemoteNonce": remote_nonce,  # The nonce from the KeyMaterial in the FI fetch response
        "base64YourNonce": your_nonce,  # Your nonce that was used in the encryption process (you should have this stored)
        "ourPrivateKey": your_private_key,  # The private key you received from the generateKey API
        "remoteKeyMaterial": remote_key_material  # The public key material from the FI fetch response
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        decrypted_data = response.json()  # This should contain the decrypted FI data
        return decrypted_data['base64Data']
    else:
        print(f"Error decrypting data: {response.text}")
        return None


def check_authenticity_of_fi_response(response, consent_handle):
    response_data = response.json()
    # status is setting REJECTED if you get api is not responding properly
    if response_data.get('ver') != API_VERSION:
        return False
    elif not validate_given_time(response_data.get('timestamp')):
        return False
    elif not validate_json(response_data, json_schema_for_get_fi_handle):
        return False

    jsw_valid_response = JWSMiddleware().process_response(response)
    if jsw_valid_response is not None:
        return False

    return True


def handle_fi_handle_service(session_id, fiu, aa):
    jws_token = generate_jws_detached(f"/FI/fetch/{session_id}")

    client_api_key = generate_token(fiu)

    headers = {
        'x-jws-signature': jws_token,
        'client_api_key': client_api_key
    }

    external_api_url = f"{aa.aa_base_path}/FI/fetch/{session_id}"

    response = requests.request("GET", external_api_url, headers=headers)

    print ("Response from FI Data fetch Service: ", response.text)

    authentic = False

    if response.status_code == 200:
        authentic = check_authenticity_of_fi_response(response, session_id)
        authentic = True
    
    if authentic:
        # Assuming 'response' is the response object from your FI data fetch request
        response_data = response.json()
        txn_id = response_data.get('txnid')
    
        # Fetch the FIDataRequest instance using txn_id
        # Make sure to handle cases where the FIDataRequest might not exist for the given txn_id
        try:
            fi_data_request = FIDataRequest.objects.get(txnid=txn_id)
        except FIDataRequest.DoesNotExist:
            # Handle the case where there's no FIDataRequest with the given txn_id
            # For example, you might create a new FIDataRequest instance here
            fi_data_request = None  # Or replace with code to handle this case appropriately

        if fi_data_request:
            # Assuming 'localKeyMaterial' and 'localPrivateKey' are available in your context
            # These should be the key material and private key you used/generated for the request
            local_key_material = fi_data_request.key_material
            local_private_key = fi_data_request.private_key

            for FIP in response_data.get('FI', []):
                fipID = FIP.get("fipID")
                for account in FIP.get("data", []):
                    # Decrypt data for each account using the decrypt_data function
                    # Ensure you pass the correct parameters to the decrypt_data function
                    decrypted_data = decrypt_data(
                        encrypted_data=account.get('encryptedFI'),
                        your_nonce=local_key_material.get('Nonce'),  # Your nonce used in the encryption process
                        remote_nonce=FIP.get('KeyMaterial', {}).get('Nonce'),  # Remote nonce from the response
                        your_private_key=local_private_key,  # Your private key used in the request
                        remote_key_material=FIP.get('KeyMaterial')  # Remote public key material from the response
                    )
    else:
        # Handle the case where the response is not authentic
        # For example, you might log the response and return an error
        print("Response not authentic")
        return None
    return response


# def generate_file_name(fipID, account):
#     # Extract an account identifier from the account data, e.g., account number
#     account_identifier = account.get('accountNumber', 'unknown_account')

#     # Current timestamp in a compact format (yyyyMMddHHmmss)
#     timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

#     # Generate a short UUID for uniqueness
#     unique_id = uuid.uuid4().hex[:8]

#     # Construct the file name
#     file_name = f"{fipID}_{account_identifier}_{timestamp}_{unique_id}.json"

#     return file_name

# def update_fi_data_request(response, authentic, session_id):

# def update_in_fi_request(response, authentic, session_id):
#     try:
#         response_data = response.json()
#         consent_handler = response_data['ConsentHandle']
#         record_to_update = SessionDetails.objects.filter(session_id=session_id).first()
#
#         # Check if the record exists
#         if record_to_update:
#             record_to_update.consent_id = response_data.get('ConsentStatus', {}).get('id')
#             record_to_update.status = response_data.get('ConsentStatus', {}).get(
#                 'status') if authentic else CONSENT_REJECTED
#             record_to_update.save()
#             logger.warning(f"Record updated with new value status {response}")
#         else:
#             logger.warning("Record not found")
#     except Exception as e:
#         logger.warning(f"Unable to update the consnet details due to {e}")
