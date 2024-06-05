from rest_framework import status

from aggregator.globals.config import API_VERSION
from aggregator.globals.session_status import SESSION_FAILED
from aggregator.helpers.json_schema_checker import validate_json, json_schema_for_fi_notification_handle
from aggregator.helpers.time_utils import validate_given_time
from aggregator.helpers.valid_uuid_check import is_valid_uuid
from aggregator.models import FIDataRequest, SessionDetails
from filelogging import logger


def fi_notification_service(request_data):
    try:
        request_timestamp = request_data['timestamp']
        fip_id_name = request_data['Notifier']['id']

        session_id = request_data['FIStatusNotification']['sessionId']
        session_status = request_data['FIStatusNotification']['sessionStatus']
        value = FIDataRequest.objects.filter(session_id=session_id).first()
        value.status = session_status
        value.save()

    except Exception as e:
        logger.warning(e)
    
    # print ("Session ID:", session_id)
    return error_handling_fi_notification(request_data, value, fip_id_name, session_status)


def error_handling_fi_notification(request_data, value, fip_id_name, session_status):
    if not validate_json(request_data, json_schema_for_fi_notification_handle):
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
    elif not fip_id_name == 'SUMASOFTAA-1':  # check this and put in constant
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("Valid aa id name failed")
        return response_data, status_code
    elif not request_data['Notifier']['type'] == 'AA':
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("Valid notifier failed")
        return response_data, status_code
    elif not validate_given_time(request_data['timestamp']):
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidRequest"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("NOT Valid Timestamp failed")
        return response_data, status_code
    elif not is_valid_uuid(request_data['txnid']):
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidConsentId"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("not valid txnid")
        return response_data, status_code
    elif value is None or value.status == SESSION_FAILED:
        response_data = {
            "errorMsg": "Error code specific error message",
            "errorCode": "InvalidSessionId"
        }
        status_code = status.HTTP_400_BAD_REQUEST
        logger.warning("not able to find in db - failed")
        return response_data, status_code
    else:
        updated_session_status(session_status, value)
        response_data = {
            "response": "OK"
        }
        status_code = status.HTTP_200_OK
        logger.warning("Success")
        # print ("Success")
        return response_data, status_code


def updated_session_status(consent_status, value):
    try:
        value.status = consent_status
        value.save()
    except Exception as e:
        logger.warning(f"Unable to save due to {e}")
