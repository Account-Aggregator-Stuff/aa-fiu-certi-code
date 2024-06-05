import json
from datetime import datetime, timedelta
import uuid

import requests
from aggregator.auth.jws import generate_jws_detached, generate_token
from aggregator.globals.config import API_VERSION
from aggregator.globals.constants import CONSENT_ERROR_CODES
from aggregator.globals.consent_constant import *

from aggregator.middlewares.JWSMiddleware import JWSMiddleware
from aggregator.models import AccountAggregator, ConsentDetail, ConsentLog
from django.utils.timezone import now


def validate_given_time(given_time_str, time_range_check_in_min=15):
    try:
        # Parse the given time string into a datetime object
        given_time = datetime.strptime(given_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")

        # Get the current time
        current_time = datetime.utcnow()  # Use utcnow() to handle the "Z" (Zulu time) in the input format

        # Define the time range
        time_range = timedelta(minutes=time_range_check_in_min)

        # Calculate the lower and upper bounds
        lower_bound = current_time - time_range
        upper_bound = current_time + time_range

        # Print information for demonstration purposes
        # print(f"Current Time: {current_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}")
        # print(f"Given Time: {given_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}")
        # print(f"Valid Range: {lower_bound.strftime('%Y-%m-%dT%H:%M:%S.%fZ')} to {upper_bound.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}")

        # Check if the given time is within the valid range
        if lower_bound <= given_time <= upper_bound:
            return True
        else:
            return False
    except:
        return False
    
def validate_consent_payload(data):
    # Check for required top-level fields
    missing_fields = [key for key in ['aa_name', 'customer_id', 'ConsentDetail'] if key not in data]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    consent_detail = data['ConsentDetail']

    # Check for required ConsentDetail fields
    missing_consent_fields = [field for field in [
        'consentStart', 'consentExpiry', 'consentMode', 'fetchType', 'consentTypes',
        'fiTypes', 'Purpose', 'FIDataRange', 'DataLife', 'Frequency', 'DataFilter'
    ] if field not in consent_detail]
    if missing_consent_fields:
        return False, f"Missing required ConsentDetail fields: {', '.join(missing_consent_fields)}"

    # Validate datetime fields
    for field in ['consentStart', 'consentExpiry']:
        if not validate_datetime(consent_detail[field]):
            return False, f"Invalid datetime format for {field}"

    # Validate enumerated fields
    if consent_detail['consentMode'] not in ['VIEW', 'STORE', 'QUERY', 'STREAM']:
        return False, "Invalid consentMode value"
    if consent_detail['fetchType'] not in ['ONETIME', 'PERIODIC']:
        return False, "Invalid fetchType value"

    # Validate arrays with enumerated values
    if not validate_array_with_enum(consent_detail['consentTypes'], ['PROFILE', 'SUMMARY', 'TRANSACTIONS']):
        return False, "Invalid consentTypes value"
    if not validate_array_with_enum(consent_detail['fiTypes'], [
        'DEPOSIT', 'TERM_DEPOSIT', 'RECURRING_DEPOSIT', 'SIP', 'CP', 'GOVT_SECURITIES',
        'EQUITIES', 'BONDS', 'DEBENTURES', 'MUTUAL_FUNDS', 'ETF', 'IDR', 'CIS', 'AIF',
        'INSURANCE_POLICIES', 'NPS', 'INVIT', 'REIT', 'OTHER'
    ]):
        return False, "Invalid fiTypes value"

    # Validate Purpose
    if not validate_purpose(consent_detail['Purpose']):
        return False, "Invalid Purpose structure"

    # Validate FIDataRange
    data_range = consent_detail['FIDataRange']
    if not all(key in data_range for key in ['from', 'to']):
        return False, "Missing required fields in FIDataRange"
    if not validate_datetime(data_range['from']) or not validate_datetime(data_range['to']):
        return False, "Invalid datetime format in FIDataRange"

    # Validate DataLife and Frequency
    if not validate_data_life_or_frequency(consent_detail['DataLife']):
        return False, "Invalid DataLife structure"
    if not validate_data_life_or_frequency(consent_detail['Frequency']):
        return False, "Invalid Frequency structure"

    # Validate DataFilter
    if not all(validate_data_filter(filter_item) for filter_item in consent_detail.get('DataFilter', [])):
        return False, "Invalid DataFilter structure"

    return True, "Validation successful"


def validate_datetime(date_string):
    try:
        datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        return True
    except ValueError:
        return False

def validate_array_with_enum(arr, enum_values):
    return all(item in enum_values for item in arr)

def validate_purpose(purpose):
    # Validate the structure and content of the 'Purpose' object
    # Implement specific validation based on your requirements
    return True

def validate_data_life_or_frequency(obj):
    required_fields = ['unit', 'value']
    if not all(field in obj for field in required_fields):
        return False
    if obj['unit'] not in ['MONTH', 'YEAR', 'DAY', 'INF', 'HOUR']:
        return False
    if not isinstance(obj['value'], int) or obj['value'] < 0:
        return False
    return True

def validate_data_filter(filter_item):
    required_fields = ['type', 'operator', 'value']
    if not all(field in filter_item for field in required_fields):
        return False
    if filter_item['type'] not in ['TRANSACTIONTYPE', 'TRANSACTIONAMOUNT']:
        return False
    if filter_item['operator'] not in ['=', '!=', '>', '<', '>=', '<=']:
        return False
    # Validate 'value' based on the expected type, format, or range
    return True



def send_consent_to_aa(data, aa, fiu, customer, tsp=False):

    # Headers with X-JWS-TOKEN and CLIENT_API_KEY
    print (aa, fiu)
    
    request_body = {
        "ver": API_VERSION,  # Constant version
        "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',  # Current timestamp in the specified format
        "txnid": str(uuid.uuid4()),  # Generate a new UUID for txnid
        "ConsentDetail": data['ConsentDetail']  # Use the 'ConsentDetail' from the provided data
    }
    
    headers = {
        'x-jws-signature': generate_jws_detached(json.dumps(request_body), fiu),
        'client_api_key': generate_token(fiu),
        'Content-Type': 'application/json'
    }

    # The AA_BASE_PATH should contain the endpoint to which the request is sent
    url = aa.aa_base_path + '/Consent'  # Adjust the URL path as needed

    try:
        log_consent_activity(customer, fiu, aa, None, None, message="A new consent request was raised to AA")
        # print (headers, request_body)
        response = requests.post(url, headers=headers, data=json.dumps(request_body))
        response_data = response.json()

        print ("Headers from AA for /Consent: ", response.headers)
        print ("Response Data from AA for /Consent: ", response_data)
        if tsp:
            return response

        if response.status_code == 200:
            # Validate the success response
            is_valid, error_message = validate_aa_consent_success_response(response_data)
            is_valid = True, ""
            if is_valid and request_body['txnid'] != response_data.get('txnid'):
                is_valid = False
                error_message = "Transaction ID mismatch in response"
            elif request_body['ConsentDetail']['Customer']['id'] != response_data.get('Customer').get('id'):
                is_valid = False
                error_message = "Customer ID mismatch in response"
            else:
                print ("gg")
                # jsw_valid_response = JWSMiddleware().process_response(response)
                # if jsw_valid_response is not None:
                #     is_valid = False
                #     error_message = "JWS Signature mismatch in response"
                
            if not is_valid:
                # Log the invalid success response
                # store_consent_detail(fiu, aa, customer, data, False, error_message)
                log_consent_activity(customer, fiu, aa, None, None, message=error_message)
                return {"success": False, "data": {"error": error_message}}
            
            # Store the successful ConsentDetail in the database
            consent_detail = store_consent_detail(fiu, aa, customer, request_body, True, response_data)
            log_consent_activity(customer, fiu, aa, response_data.get("ConsentHandle"), None, message="New Consent Handle Received.")

            consent_response = {
                "consent_handle": response_data.get("ConsentHandle"),
                "customer": consent_detail["customer"]
            }
            return {"success": True, "data": consent_response}

        else:
            # Handle error response and log it
            error_message = response_data.get("errorMsg", "An error occurred")
            log_consent_activity(customer, fiu, aa, None, None, message=error_message)
            return {"success": False, "data": {"error": error_message}}

    except requests.exceptions.RequestException as e:
        # Log the exception and return error
        log_consent_activity(customer, fiu, aa, None, None, message=str(e))
        return {"success": False, "data": {"error": str(e)}}
    

def store_consent_detail(fiu, aa, customer, data, success, response_data, status = CONSENT_PENDING):
    consent_handle = response_data.get("ConsentHandle") if success else None
    message = response_data if isinstance(response_data, str) else json.dumps(response_data)

    consent_detail, created = ConsentDetail.objects.update_or_create(
        consent_handle=consent_handle,
        defaults={
            'fiu': fiu,
            'aa': aa,
            'customer': customer,
            'consent_payload': json.dumps(data),
            'status': status,
            'message': message,
            'txnid': data.get('txnid', None),
            'updated_at': now()
        }
    )
    
    if created:
        consent_detail.created_at = now()  # Set created_at only if the record is newly created
        consent_detail.save()

    return consent_detail.to_dict()


def validate_aa_consent_success_response(response_data):
    required_fields = ['ver', 'txnid', 'timestamp', 'Customer', 'ConsentHandle']
    missing_fields = [field for field in required_fields if field not in response_data]
    if missing_fields:
        return False, f"Missing required fields in success response: {', '.join(missing_fields)}"

    # the response data should not have any other fields apart from required fields

    if len(response_data) != len(required_fields):
        return False, "Invalid fields in success response"
    
    # if ver is not API_VERSION, then return False
    if response_data['ver'] != API_VERSION:
        return False, "Invalid API version in response"
    
    # validate if timestamp is right format
    if not validate_given_time(response_data['timestamp']):
        return False, "Invalid timestamp range in response"

    return True, ""


def log_consent_activity(customer, fiu, aa, consent_handle, consent_id, message):
    """
    Logs an activity related to consent operations.

    :param customer: The FIUCustomer instance related to the log.
    :param fiu: The FIUEntity instance related to the log.
    :param aa: The AccountAggregator instance related to the log.
    :param consent_handle: The consent handle (UUID) associated with the log, if applicable.
    :param consent_id: The consent ID (UUID) associated with the log, if applicable.
    :param message: The message or description of the log entry.
    """
    ConsentLog.objects.create(
        customer=customer,
        fiu=fiu,
        aa=aa,
        consent_handle=consent_handle,
        consent_id=consent_id,
        message=message
    )