import os

import requests

from aggregator.auth.jws import generate_token, generate_jws_detached
from aggregator.globals.config import API_VERSION
from aggregator.globals.session_status import SESSION_FAILED, SESSION_ACTIVE
from aggregator.helpers.json_schema_checker import validate_json, json_schema_for_fi_request_handle
from aggregator.helpers.time_utils import create_timestamp, validate_given_time
from aggregator.helpers.uuid_utils import create_new_txn_id
from aggregator.middlewares.JWSMiddleware import JWSMiddleware
from aggregator.models import FIDataRequest, FIUEntity, SessionDetails
from aggregator.service.consent_service import payload_changing_based_on_client
from filelogging import logger


def error_handling_fi_request(response, txn_id, consent_id):
    response_in_json = response.json()
    if not validate_json(response_in_json, json_schema_for_fi_request_handle):
        logger.warning("Validation Failed in JSON schema")
        return SESSION_FAILED
    elif response_in_json.get('ver') != API_VERSION:
        logger.warning("Validation Failed due to api version issue")
        return SESSION_FAILED
    elif not validate_given_time(response_in_json.get('timestamp')):
        logger.warning("Validation Failed due to invalid timestamp")
        return SESSION_FAILED
    elif txn_id != response_in_json.get('txnid'):
        logger.warning("Validation Failed due to invalid consnet/txn id")
        return SESSION_FAILED
    elif consent_id != response_in_json.get('consentId'):
        logger.warning("Validation Failed due to invalid consent id")
        return SESSION_FAILED

    jsw_valid_response = JWSMiddleware().process_response(response)
    if jsw_valid_response is not None:
        logger.warning("due to invalid sign")
        return SESSION_FAILED

    return SESSION_ACTIVE


def save_fi_details_in_db(json_data, session_status, consent_id, txn_id):
    try:
        logger.warning("Started Putting entry in DB")
        your_model_instance = SessionDetails(session_id=json_data['sessionId'],
                                             consent_id=consent_id,
                                             session_status=session_status,
                                             txnid=txn_id)
        your_model_instance.save()
        logger.warning("Data Stored")
    except Exception as e:
        logger.warning(e)


def fi_request_service(data, fiu: FIUEntity):
    client_api_key = generate_token(fiu.FIU_CLIENT_ID, fiu.FIU_CLIENT_SECRET, fiu.FIU_TOKEN_URL)

    data['ver'] = API_VERSION
    data['timestamp'] = create_timestamp()
    consent_id = data['Consent']['id']
    txn_id = data['txnid']

    payload = payload_changing_based_on_client(data, fiu.aa.aa_name)

    jws_token = generate_jws_detached(payload)

    headers = {
        'x-jws-signature': jws_token,
        'client_api_key': client_api_key,
        'Content-Type': 'application/json'
    }

    external_api_url = f'{fiu.aa.aa_base_path}/FI/request'

    # print ("Payload for FI Request Service: ", payload)

    # print (payload)

    response = requests.request("POST", external_api_url, headers=headers, data=payload)
    print (payload)
    # print (response.json())
    if response.status_code == 200:
        session_status = error_handling_fi_request(response, txn_id, consent_id)
        save_fi_details_in_db(response.json(), session_status, consent_id, txn_id)
        save_fi_data_request_in_db(response.json(), session_status, consent_id, txn_id)

    return response


def save_fi_data_request_in_db(json_data, session_status, consent_id, txn_id):
    try:
        logger.warning("Started Putting entry in DB")
        fi_data_request = FIDataRequest.objects.get(txnid=txn_id)
        fi_data_request.session_id = json_data['sessionId']
        fi_data_request.save()
    except Exception as e:
        logger.warning(e)
