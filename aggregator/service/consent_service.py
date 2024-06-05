import json
import os
import uuid
from datetime import datetime
from django.http import JsonResponse

import pytz
import requests

from aggregator.auth.jws import generate_token, generate_jws_detached
from aggregator.globals.config import API_VERSION
from aggregator.globals.consent_constant import CONSENT_FAILED, CONSENT_PENDING
from aggregator.helpers.aes_utils import generate_redirect_url
from aggregator.helpers.json_schema_checker import validate_json, json_schema_for_consent_response
from aggregator.helpers.time_utils import validate_given_time, create_timestamp
from aggregator.helpers.uuid_utils import create_new_txn_id
from aggregator.middlewares.JWSMiddleware import JWSMiddleware
from aggregator.models import ConsentDetail, AccountAggregator, FIUEntity
from filelogging import logger


def post_consent_service(data, fiu: FIUEntity, aa_client: AccountAggregator):
    txn_id = create_new_txn_id()
    session_id = create_new_txn_id()

    data['txnid'] = txn_id
    data['timestamp'] = create_timestamp()

    customer_id = data['ConsentDetail']['Customer']['id']

    payload = payload_changing_based_on_client(data, aa_client.aa_name)

    client_api_key = generate_token(fiu.FIU_CLIENT_ID, fiu.FIU_CLIENT_SECRET, fiu.FIU_TOKEN_URL)

    # print (payload)
    jws_token = generate_jws_detached(payload)

    headers = {
        'x-jws-signature': jws_token,
        'client_api_key': client_api_key,
        'Content-Type': 'application/json'
    }

    external_api_url = f'{aa_client.aa_base_path}/Consent'

    response = requests.request("POST", external_api_url, headers=headers, data=payload)

    consent_status = error_handling_consent(response, txn_id, customer_id)
    save_details_in_db(response.json(), consent_status, fiu.id)
    redirect_url = "https://jusfin.in"

    if response.status_code == 200:
        response_data = response.json()
        redirection_url = generate_redirect_url(fiu.FIU_CLIENT_ID, "FIU", txn_id, session_id, customer_id, redirect_url, response.json()['ConsentHandle'], fiu.aes_token)
        response_data['redirection_url'] = redirection_url
    else:
        response_data = response.json()

    return JsonResponse(response_data, status=response.status_code)

def save_details_in_db(json_data, consent_status, fiu_id):
    try:
        logger.warning("Started Putting entry in DB")
        your_model_instance = ConsentDetail(
                                            customer_id=json_data['Customer']['id'],
                                            consent_handle=json_data['ConsentHandle'], status=consent_status,
                                            fiu_id = fiu_id)
        your_model_instance.save()
        logger.warning("Data Stored")
    except Exception as e:
        logger.warning(e)


def error_handling_consent(response, txn_id, customer_id):
    response_in_json = response.json()
    if not validate_json(response_in_json, json_schema_for_consent_response):
        logger.warning("Validation Failed in JSON schema")
        return CONSENT_FAILED
    elif response_in_json.get('ver') != API_VERSION:
        logger.warning("Validation Failed due to api version issue")
        return CONSENT_FAILED
    elif not validate_given_time(response_in_json.get('timestamp')):
        logger.warning("Validation Failed due to invalid timestamp")
        return CONSENT_FAILED
    elif txn_id != response_in_json.get('txnid'):
        logger.warning("Validation Failed due to invalid consnet/txn id")
        return CONSENT_FAILED
    elif customer_id != response_in_json.get('Customer').get('id'):
        logger.warning("Validation Failed due to invalid customer id")
        return CONSENT_FAILED

    jsw_valid_response = JWSMiddleware().process_response(response)
    if jsw_valid_response is not None:
        logger.warning("due to invalid sign")
        return CONSENT_FAILED

    return CONSENT_PENDING



def payload_changing_based_on_client(data, client):
    if client == 'SUMA-SOFT':
        return json.dumps(data, separators=(',', ':'))
    else:
        return json.dumps(data, indent=4)
    

