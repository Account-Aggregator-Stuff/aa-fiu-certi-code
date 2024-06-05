import json
import os

import requests

from aggregator.auth.jws import generate_jws_detached, generate_token
from aggregator.globals.config import API_VERSION
from aggregator.globals.consent_constant import CONSENT_ACTIVE, CONSENT_FAILED
from aggregator.helpers.encoding_decoding import base64url_decode
from aggregator.helpers.time_utils import validate_given_time, create_timestamp
from aggregator.middlewares.JWSMiddleware import JWSMiddleware
from aggregator.models import ConsentDetail, FIUEntity
from filelogging import logger


def check_authenticity_of_consent_id_response(response, consent_id):
    response_data = response.json()
    # TODO createTimestamp,signedConsent,consentUse,
    if response_data.get('ver') != API_VERSION:
        logger.warning("Version Failed ")
        print("API Version mismatch for Consent ID response")
        return False
    elif not validate_given_time(response_data.get('createTimestamp', create_timestamp())):
        logger.warning("timestamp Failed ")
        print ("Timestamp not in range for Consent ID response")
        return False
    elif response_data.get('consentId') != consent_id:
        logger.warning("consent id Failed ")
        print ("Consent ID mismatch for Consent ID response")
        return False

    payload = response_data.get('signedConsent').split('.')[1]
    decoded_str = base64url_decode(payload)
    decoded_json = json.loads(decoded_str)

    if decoded_json.get('Notifier', {}).get('id') == 'SUMASOFTAA':
        print("Notifier id is SUMASOFTAA, incorrect AA")
        logger.warning("notifier failed ")
        return False

    consent_details = ConsentDetail.objects.filter(consent_id=consent_id).first()

    jsw_valid_response = JWSMiddleware().process_response(response)
    if jsw_valid_response is not None:
        print ("JWS signature invalid for Consent ID response")
        logger.warning("jsw failed ")
        return False

    jwt_string = response_data.get('signedConsent')
    header, payload, signature = jwt_string.split(".")

    # Create a new token without the payload
    new_jwt = f"{header}..{signature}"
    response.headers['x-jws-signature'] = new_jwt
    jsw_valid_response = JWSMiddleware().process_response(response, decoded_json)
    if jsw_valid_response is not None:
        print ("JWS signature invalid for Consent ID response")
        logger.warning("detached sign failed ")
        return False

    # TODO put the  proper check
    if response_data.get('ConsentUse',{}).get('count') != 0:
        logger.warning("consent use count Failed ")
        return False

    return True


def get_from_consent_id(consent_id, fiu: FIUEntity, aa):
    jws_token = generate_jws_detached(f"/Consent/{consent_id}", fiu)

    client_api_key = generate_token(fiu)

    headers = {
        'x-jws-signature': jws_token,
        'client_api_key': client_api_key
    }
    external_api_url = f"{aa.aa_base_path}/Consent/{consent_id}"
    response = requests.request("GET", external_api_url, headers=headers)
    print ("Response from Consent ID:", response.text)
    if response.status_code == 200:
        authentic = check_authenticity_of_consent_id_response(response, consent_id)
        update_in_consent_id(response, authentic, consent_id)

    return response


def update_in_consent_id(response, authentic, consent_id):
    try:
        response_data = response.json()
        record_to_update = ConsentDetail.objects.filter(consent_id=consent_id).first()

        # Check if the record exists
        if record_to_update:
            record_to_update.status = response_data.get('status') if authentic else CONSENT_FAILED
            record_to_update.consent_details = response_data if authentic else record_to_update.consent_details
            record_to_update.save()
            logger.warning(f"Record updated with new value status {response}")
        else:
            logger.warning("Record not found")
    except Exception as e:
        logger.warning(f"Unable to update the consnet details due to {e}")
