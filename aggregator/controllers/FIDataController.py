import datetime
import json
import os

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from aggregator.decorators import fiu_token_required
from rest_framework import status

from aggregator.controllers.AggregatorController import check_auth
from aggregator.helpers.consent_utils import send_consent_to_aa
from aggregator.helpers.request_data_utils import send_fi_request_to_aa
from aggregator.helpers.utils import create_response
from aggregator.helpers.uuid_utils import create_new_txn_id
from aggregator.models import AccountAggregator, ConsentDetail, FIDataRequest, FIUCustomer, FIUEntity
from aggregator.service.fi_request_service import fi_request_service
from aggregator.service.handle_fi_service import handle_fi_handle_service

def generate_fi_data_request_payload(consent_id):
    # Calculate FIDataRange

    # Fetch digital signature from ConsentDetails model
    try:
        consent_detail = ConsentDetail.objects.get(consent_id=consent_id)
        current_time = consent_detail.created_at - datetime.timedelta(days=1)
        start_time = current_time - datetime.timedelta(days=consent_detail.fiu.data_days_range - 200)
        fi_data_range = {
            "from": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "to": current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        jwt_token = consent_detail.signedConsent  # Assuming signedConsent contains the JWT
        digital_signature = jwt_token.split('.')[-1] # Assuming there's a digital_signature field
    except ConsentDetail.DoesNotExist:
        print ("Consent Not Found!")
        return None

    # Fetch KeyMaterial from external API
    response = requests.get("https://rahasya.setu.co/ecc/v1/generateKey")
    if response.status_code != 200:
        print ("Rahasya is down!")
        return None

    key_material = response.json().get('KeyMaterial', {})
    private_key = response.json().get('privateKey', "")
    # Construct the JSON payload
    payload = {
        "FIDataRange": fi_data_range,
        "Consent": {
            "id": consent_id,
            "digitalSignature": digital_signature
        },
        "KeyMaterial": key_material
    }

    txn_id = create_new_txn_id()
    payload['txnid'] = txn_id
    
    fi_data_request = FIDataRequest(
        consent_id=consent_detail,
        customer_id=consent_detail.customer_id,  # Assuming you have a way to determine the customer_id
        status='INITIATED',  # Or another status if appropriate
        private_key=private_key,
        key_material=key_material,
        txnid = txn_id
    )

    fi_data_request.save()

    return payload

@csrf_exempt
@fiu_token_required
def fi_data_request(request, aa = "finvu", fiu=None, customer=None):
        try:
            aa = AccountAggregator.objects.get(aa_name=aa)
        except AccountAggregator.DoesNotExist:
            return create_response(status_code=400, error='AA not found.')
        if not customer:
            customer = FIUCustomer.objects.first()
        if not fiu:
            fiu = FIUEntity.objects.get(id=1)
        try:
            print ("FIU:", fiu)
            response = send_fi_request_to_aa(json.loads(request.body), aa, fiu, customer, tsp=True)
            return response
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

@csrf_exempt
@fiu_token_required
def fi_data_fetch(request, session_id):
    try:
        fi_data_request = FIDataRequest.objects.get(session_id=session_id)
    except FIDataRequest.DoesNotExist:
        return JsonResponse({"error": "FI Data Request not found"}, status=status.HTTP_404_NOT_FOUND)

    # Use the associated FIU and AA directly from the consent_detail
    fiu = FIUEntity.objects.get(id=1)
    aa = AccountAggregator.objects.get(aa_name="finvu")

    if not fiu or not aa:
        return JsonResponse({"error": "FIU or AA not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Call the service function with the consent detail, and its associated FIU and AA
        response = handle_fi_handle_service(session_id, fiu=fiu, aa=aa)
        # Assuming response from handle_consent_service is a dictionary that can be directly passed to JsonResponse
        return JsonResponse(response.json(), status=status.HTTP_200_OK)
    except requests.exceptions.RequestException as e:
        # Handle any exceptions during the service call
        return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@csrf_exempt
def customer_data_fetch(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        fiu = check_auth(request.headers.get('Auth-Token', ""))
        if fiu == -1:
            return JsonResponse({"error": "Failed to Authenticate, FIU_ID or token mismatch"}, status=status.HTTP_401_UNAUTHORIZED)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    # Extract parameters from the request
    phone_number = request.GET.get('phone_number')
    consent_id = request.GET.get('consent_id')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # Basic validation
    if not phone_number:
        return JsonResponse({"error": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        customer_id = phone_number + fiu.aa.aa_suffix
    # Build the query based on the parameters
    # print (customer_id)
    queryset = FIDataRequest.objects.filter(consent_id__customer_id=customer_id)

    if consent_id:
        queryset = queryset.filter(consent_id__consent_id=consent_id)

    if from_date and to_date:
        queryset = queryset.filter(created_at__range=[from_date, to_date])

    # Serialize the data and return the response
    data = list(queryset.values())  # Simplified for illustration; consider using a serializer for complex data
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)