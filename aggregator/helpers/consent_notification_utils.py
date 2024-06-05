from rest_framework import status

from aggregator.globals.config import API_VERSION
from aggregator.globals.consent_constant import CONSENT_FAILED, CONSENT_ACTIVE, CONSENT_PAUSED
from aggregator.helpers.json_schema_checker import validate_json, json_schema_for_notification_request
from aggregator.helpers.time_utils import validate_given_time
from aggregator.helpers.valid_uuid_check import is_valid_uuid
from aggregator.models import ConsentDetail
from filelogging import logger

import jsonschema
from jsonschema import validate
from jsonschema.exceptions import ValidationError

def consent_notification_service(request_data):
    try:
        aa_id_name = request_data['Notifier']['id']
        notifier = request_data['Notifier']['type']
        request_timestamp = request_data['timestamp']

        consent_id = request_data['ConsentStatusNotification']['consentId']
        consent_status = request_data.get('ConsentStatusNotification', {}).get('consentStatus')
        consent_handle = request_data.get('ConsentStatusNotification', {}).get('consentHandle')
        # find with consent id if not present then search with consent handle and mapped the consent handle with consent id
        value = ConsentDetail.objects.filter(consent_id=consent_id).first()
        if value is None:
            value = ConsentDetail.objects.filter(consent_handle=consent_handle).first()
            value.consent_id = consent_id
            value.status = consent_status
    except Exception as e:
        logger.warning(e)
    return error_handling_consent_notification(request_data, aa_id_name, notifier,
                                               request_timestamp, value, consent_id, consent_status)


def updated_consent_status(consent_status, value):
    try:
        value.status = consent_status
        value.save()
    except Exception as e:
        logger.warning(f"Unable to save due to {e}")

json_schema_for_notification_request = {
    "type": "object",
    "properties": {
        "ver": {"type": "string"},
        "timestamp": {"type": "string"},  # Adjust the type or add a format if needed
        "txnid": {"type": "string"},
        "Notifier": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "id": {"type": "string"}
            },
            "required": ["type", "id"]
        },
        "ConsentStatusNotification": {
            "type": "object",
            "properties": {
                "consentId": {"type": "string"},
                "consentHandle": {"type": "string"},
                "consentStatus": {"type": "string"}
            },
            "required": ["consentId", "consentHandle", "consentStatus"]
        }
    },
    "required": ["ver", "timestamp", "txnid", "Notifier", "ConsentStatusNotification"]
}

def validate_notification_request(request_data):
    try:
        validate(instance=request_data, schema=json_schema_for_notification_request)
        return True, ""
    except ValidationError as e:
        return False, str(e)


def error_handling_consent_notification(request_data, aa_id_name, notifier, request_timestamp, consent_detail, consent_id, consent_status):
    is_valid, error = validate_notification_request(request_data)
    if not is_valid:
        logger.warning("Invalid request: " + error)
        return {"errorMsg": "Invalid request format", "errorCode": "InvalidRequest"}, status.HTTP_400_BAD_REQUEST

    if request_data.get('ver') != API_VERSION:
        logger.warning("Invalid API version")
        return {"errorMsg": "Unsupported API version", "errorCode": "NoSuchVersion"}, status.HTTP_404_NOT_FOUND

    if not validate_given_time(request_timestamp):
        logger.warning("Invalid timestamp")
        return {"errorMsg": "Invalid timestamp", "errorCode": "InvalidRequest"}, status.HTTP_400_BAD_REQUEST
    
    if notifier != 'AA':
        logger.warning("Invalid notifier")
        return {"errorMsg": "Invalid notifier type", "errorCode": "InvalidRequest"}, status.HTTP_400_BAD_REQUEST
    
    if aa_id_name != 'SUMASOFTAA-1':
        logger.warning("Invalid AA ID")
        return {"errorMsg": "Invalid AA ID", "errorCode": "InvalidRequest"}, status.HTTP_400_BAD_REQUEST

    # if not validate_given_time(request_timestamp):
    #     logger.warning("Invalid timestamp", request_timestamp)
    #     return {"errorMsg": "Invalid timestamp", "errorCode": "InvalidRequest"}, status.HTTP_400_BAD_REQUEST

    if not is_valid_uuid(consent_id):
        logger.warning("Invalid consent ID")
        return {"errorMsg": "Invalid consent ID", "errorCode": "InvalidConsentId"}, status.HTTP_400_BAD_REQUEST

    # Assuming value represents a ConsentDetail instance fetched based on consent_handle or consent_id
    value = consent_detail

    if value is None or value.status == CONSENT_FAILED:
        logger.warning("Consent not found or failed")
        if value is not None and value.status == 'EXPIRED':
            return {"errorMsg": "Consent expired", "errorCode": "ExpiredConsent"}, status.HTTP_400_BAD_REQUEST
        if value is not None and value.status != 'EXPIRED':
            value.status = consent_status
            value.save()
        return {"errorMsg": "Consent not found or failed", "errorCode": "InvalidRequest"}, status.HTTP_400_BAD_REQUEST

    if value is not None and value.status == 'EXPIRED':
            return {"errorMsg": "Consent expired", "errorCode": "ExpiredConsent"}, status.HTTP_400_BAD_REQUEST
    
    logger.info("Consent status updated successfully")
    return {"response": "OK"}, status.HTTP_200_OK


def get_aa_id_name_and_notifier(request_data):
    # request_data = request.data  # Access the JSON body of the request
    notifier_info = request_data.get("Notifier", {})  # Safely get the "Notifier" object
    
    # Extract "id" and "type" from the "Notifier" object
    aa_id_name = notifier_info.get("id")
    notifier_type = notifier_info.get("type")

    return aa_id_name, notifier_type