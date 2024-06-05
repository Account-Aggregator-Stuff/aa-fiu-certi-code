import json
import uuid
from datetime import datetime

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from django.utils.timezone import now

from aggregator.auth.jws import generate_jws_detached
from aggregator.decorators import jws_required, access_token
from aggregator.globals.config import API_VERSION
from aggregator.globals.constants import ERROR_CODES, ERROR_MESSAGES
from aggregator.helpers.consent_notification_utils import error_handling_consent_notification, get_aa_id_name_and_notifier
from aggregator.models import ConsentDetail, ConsentLog
from aggregator.service.fi_notification_service import fi_notification_service
from filelogging import logger


@api_view(['POST'])
@parser_classes([JSONParser])
@jws_required  # Ensure the JWS signature is valid
@access_token  # Ensure the AA API key is valid
def consent_notification(request):
    request_data = json.loads(request.data)
    print (request_data)
    # if(request_data.get("ver") != API_VERSION):
    #     return Response("No such Version", status=404)
    
    consent_status_data = request_data.get("ConsentStatusNotification", {})
    consent_handle = consent_status_data.get("consentHandle")
    consent_id = consent_status_data.get("consentId")
    consent_status = consent_status_data.get("consentStatus")
    
    # Assuming the existence of a function to get aa_id_name and notifier from the request
    aa_id_name, notifier = get_aa_id_name_and_notifier(request_data)  # Implement this function based on your app's logic
    request_timestamp = request_data.get("timestamp")

    # Use the consent handle to fetch the corresponding ConsentDetail and FIU
    # print (consent_handle)
    consent_detail = ConsentDetail.objects.filter(consent_handle=consent_handle).select_related('fiu').first()
    
    if consent_detail:
        fiu = consent_detail.fiu
    else:
        fiu = None

    # print (consent_detail)
    # Call the error handling function early to handle potential errors
    error_response, status_code = error_handling_consent_notification(
        request_data, aa_id_name, notifier, request_timestamp, 
        consent_detail, consent_id=consent_status_data.get("consentId"), 
        consent_status=consent_status
    )
    if status_code != 200:
        # If there's an error, generate a JWS signature for the error response and return
        jws_signature = generate_jws_detached(json.dumps(error_response), fiu) if fiu else None
        headers = {"x-jws-signature": jws_signature} if jws_signature else {}
        print ("Response to Consent Notification:",error_response, status_code, headers)
        return Response(error_response, status=status_code, headers=headers)

    # If there are no errors, proceed with updating the consent status and logging
    consent_detail.status = consent_status
    consent_detail.consent_id = consent_id
    consent_detail.save()
    ConsentLog.objects.create(
        customer=consent_detail.customer,
        fiu=consent_detail.fiu,
        aa=consent_detail.aa,
        consent_handle=consent_handle,
        consent_id=consent_detail.consent_id,
        message=f"Consent status updated to {consent_status}"
    )

    # Prepare the success response
    response_data = {
        "ver": API_VERSION,
        "timestamp": now().isoformat(),
        "txnid": str(uuid.uuid4()),
        "response": "OK"
    }
    jws_signature = generate_jws_detached(json.dumps(response_data), fiu)
    headers = {"x-jws-signature": jws_signature}
    print ("Response to Consent Notification:",response_data, 200, headers)
    return Response(response_data, status=200, headers=headers)



@api_view(['POST'])
@parser_classes([JSONParser])
@jws_required
@access_token
def fi_notification(request):
    if request.method == 'POST':
        request_data = json.loads(request.data)
        response_data = {
            "ver": API_VERSION,
            "timestamp": now().isoformat(),
            "txnid": str(uuid.uuid4()),
        }

        try:
            response_message, status_code = fi_notification_service(request_data)
            print ("Response Message: ", response_message, status_code)
            response_data = response_data | response_message
            payload = json.dumps(response_data, separators=(',', ':'))
            # print (payload)
            jws = generate_jws_detached(payload)
            logger.warning("Notification Received Successfully")
            logger.warning(response_data)
            print ("Response to FI Notification: ",response_data, status_code)
            return Response(response_data, status=status_code, headers={"x-jws-signature": jws})
        except Exception as e:
            logger.warning(e)


def handle_errors(serializer):
    error_data = {
        "ver": API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "txnid": str(uuid.uuid4())
    }

    if "Notifier" in serializer.errors:
        error_data.update({
            "errorCode": ERROR_CODES.get("InvalidNotifier"),
            "errorMsg": ERROR_MESSAGES["InvalidNotifier"].format(serializer.errors["Notifier"][0])
        })
    elif "ConsentId" in serializer.errors:
        error_data.update({
            "errorCode": ERROR_CODES.get("InvalidConsentId"),
            "errorMsg": ERROR_MESSAGES["InvalidConsentId"].format(serializer.errors["ConsentId"][0])
        })
    elif "ConsentStatus" in serializer.errors:
        error_data.update({
            "errorCode": ERROR_CODES.get("InvalidConsentStatus"),
            "errorMsg": ERROR_MESSAGES["InvalidConsentStatus"].format(serializer.errors["ConsentStatus"][0])
        })
    elif "sessionId" in serializer.errors:
        error_data.update({
            "errorCode": ERROR_CODES.get("InvalidSessionId"),
            "errorMsg": ERROR_MESSAGES["InvalidSessionId"].format(serializer.errors["sessionId"][0])
        })
    elif "sessionStatus" in serializer.errors:
        error_data.update({
            "errorCode": ERROR_CODES.get("InvalidSessionStatus"),
            "errorMsg": ERROR_MESSAGES["InvalidSessionStatus"].format(serializer.errors["sessionStatus"][0])
        })
    elif "FIStatus" in serializer.errors:
        error_data.update({
            "errorCode": ERROR_CODES.get("InvalidFIStatus"),
            "errorMsg": ERROR_MESSAGES["InvalidFIStatus"].format(serializer.errors["FIStatus"][0])
        })
    else:
        error_data.update({
            "errorCode": ERROR_CODES.get("GeneralError"),
            "errorMsg": ERROR_MESSAGES["GeneralError"]
        })

    return Response(error_data, status=status.HTTP_400_BAD_REQUEST,
                    headers={"x-jws-signature": "Your JWS Signature Here"})
