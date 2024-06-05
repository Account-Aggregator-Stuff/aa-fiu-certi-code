from rest_framework import status

from aggregator.globals.config import API_VERSION
from aggregator.globals.consent_constant import CONSENT_FAILED, CONSENT_ACTIVE, CONSENT_PAUSED
from aggregator.helpers.json_schema_checker import validate_json, json_schema_for_notification_request
from aggregator.helpers.time_utils import validate_given_time
from aggregator.helpers.valid_uuid_check import is_valid_uuid
from aggregator.models import ConsentDetail
from filelogging import logger


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


def error_handling_consent_notification(request_data, aa_id_name, notifier,
                                        request_timestamp, value, consent_id, consnet_status):
    if not validate_json(request_data, json_schema_for_notification_request):
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("Valid response failed")
        return response_data, status_code
    elif not request_data.get('ver') == API_VERSION:
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "NoSuchVersion"
        }
        status_code = status.HTTP_404_NOT_FOUND
        logger.warning("Valid version failed")
        return response_data, status_code
    elif not aa_id_name == 'SUMASOFTAA-1':
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("Valid aa id name failed")
        return response_data, status_code
    elif not notifier == 'AA':
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("Valid notifier failed")
        return response_data, status_code
    elif not validate_given_time(request_timestamp):
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("NOT Valid Timestamp failed")
        return response_data, status_code
    elif not is_valid_uuid(consent_id):
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidConsentId"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("not valid consent id")
        return response_data, status_code
    elif value is None or value.status == CONSENT_FAILED:
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("not able to find in db - failed")
        updated_consent_status(consnet_status, value)
        return response_data, status_code
    else:
        updated_consent_status(consnet_status, value)
        response_data = {
            "response": "OK"
        }
        status_code = status.HTTP_200_OK
        logger.warning("Success")
        return response_data, status_code
