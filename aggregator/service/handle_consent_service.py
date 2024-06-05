import os
import json
import requests

from aggregator.auth.jws import generate_jws_detached, generate_token
from aggregator.globals.config import API_VERSION
from aggregator.helpers.json_schema_checker import validate_json, json_schema_for_consent_handle_request
from aggregator.helpers.time_utils import validate_given_time
from aggregator.middlewares.JWSMiddleware import JWSMiddleware
from aggregator.models import ConsentDetail, FIUEntity
from filelogging import logger


def check_authenticity_of_response(response, consent_handle):
    response_data = response.json()
    # status is setting REJECTED if you get api is not responding properly
    if response_data.get('ver') != API_VERSION:
        print ("API VERSION mismatch for consent handle")
        logger.warning("ver issue")
        return False
    elif not validate_given_time(response_data.get('timestamp')):
        print ("Timestamp not in range for consent handle..")
        logger.warning("error time stamp")
        return False
    elif response_data.get('ConsentHandle') != consent_handle:
        print ("Consent handle mismatch for consent handle")
        logger.warning("error in consent handle")
        return False
    elif not validate_json(response_data, json_schema_for_consent_handle_request):
        print ("Invalid JSON schema for consent handle RESPONSE")
        logger.warning("error in json schema")
        return False

    jsw_valid_response = JWSMiddleware().process_response(response)
    if jsw_valid_response is not None:
        print ("Invalid JWS in response for consent handle")
        logger.warning("jsw invalid json")
        return False

    return True


def handle_consent_service(consent_handle, fiu: FIUEntity, aa):
    jws_token = generate_jws_detached(f"/Consent/handle/{consent_handle}", fiu)

    client_api_key = generate_token(fiu)

    headers = {
        'x-jws-signature': jws_token,
        'client_api_key': client_api_key
    }

    external_api_url = f"{aa.aa_base_path}/Consent/handle/{consent_handle}"
    response = requests.request("GET", external_api_url, headers=headers)
    print (response.text)
    if response.status_code == 200:
        authentic = check_authenticity_of_response(response, consent_handle)
        update_in_consent_details(response, authentic, consent_handle)
    return response


def update_in_consent_details(response, authentic, consent_handle):
    try:
        response_data = response.json()
        record_to_update = ConsentDetail.objects.filter(consent_handle=consent_handle).first()

        # Check if the record exists
        if record_to_update:
            record_to_update.status = response_data.get('ConsentStatus', {}).get(
                'status') if authentic else record_to_update.status
            if record_to_update.status == "READY":
                record_to_update.consent_id = response_data.get('ConsentStatus', {}).get('id')
            record_to_update.save()
            logger.warning(f"Record updated with new value status {response}")
        else:
            logger.warning("Record not found")
    except Exception as e:
        logger.warning(f"Unable to update the consnet details due to {e}")


def payload_changing_based_on_client(data, client):
    if client == 'SUMA-SOFT':
        return json.dumps(data, separators=(',', ':'))
    elif client == 'SAAFE':
        return json.dumps(data, indent=4)
