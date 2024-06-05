import json
import requests

from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from rest_framework import status
from aggregator.auth.jws import generate_token
from aggregator.globals.config import API_VERSION
from aggregator.helpers.redirect_utils import generate_redirect_url
from aggregator.models import FIUAARegistration, FIUCustomer, FIUEntity, ConsentDetail, AccountAggregator

from aggregator.service.consent_service import post_consent_service
from aggregator.service.get_consent_id_service import get_from_consent_id
from aggregator.service.handle_consent_service import handle_consent_service

from aggregator.decorators import fiu_token_required
from aggregator.helpers.utils import create_response
from aggregator.helpers.consent_utils import validate_consent_payload, send_consent_to_aa


def check_auth(token):
    try:
        # print (token)
        # Attempt to find an FIUEntity with the given ID and token
        fiu_entity = FIUEntity.objects.get(token=token)
        # If found, return the FIUEntity's ID
        return fiu_entity
    except ObjectDoesNotExist:
        # If no matching FIUEntity is found, return -1
        return -1
    

def heartbeat(request):
    if request.method == 'GET':
        try:
            fiu = check_auth(request.headers.get('Auth-Token', ""))
            if fiu == -1:
                return JsonResponse({"error": "Failed to Authenticate, FIU_ID or token mismatch"}, status=status.HTTP_401_UNAUTHORIZED)
            external_api_url = fiu.aa.aa_base_path + "/Heartbeat"
            headers = {
                "client_api_key": generate_token(fiu.FIU_CLIENT_ID, fiu.FIU_CLIENT_SECRET, fiu.FIU_TOKEN_URL)
            }
            response = requests.request("GET", external_api_url, headers=headers)
            print (response)
            return JsonResponse(response.json(), status=response.status_code)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    else:   
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@require_http_methods(["GET", "POST"])
@fiu_token_required
@csrf_exempt
def consent(request):
    if request.method == 'POST':
        return handle_consent_post(request)
    else:  # GET request
        return handle_consent_get(request)

@fiu_token_required
def handle_consent_post(request):
    try:
        data = json.loads(request.body)
        
        # Validate the consent payload
        is_valid, validation_message = validate_consent_payload(data)
        if not is_valid:
            return create_response(status_code=400, error=validation_message)

        # Check if the AA specified in the payload exists
        try:
            aa = AccountAggregator.objects.get(aa_name=data['aa_name'])
        except AccountAggregator.DoesNotExist:
            return create_response(status_code=400, error='AA not found.')

        # Ensure the FIU is registered with the specified AA
        if not request.fiu.is_registered_with(aa):
            return create_response(status_code=403, error='FIU is not registered with the specified AA.')

        # Check if the customer exists
        try:
            customer_id = data['customer_id']  # Assuming 'customer_id' is provided directly in the data payload
            customer = FIUCustomer.objects.get(id=customer_id)
        except FIUCustomer.DoesNotExist:
            return create_response(status_code=404, error='Customer ID not found.')
    
        # Add DataConsumer id and Customer id
        data['ConsentDetail']['DataConsumer'] = {"id": request.fiu.fiu_client_id}
        data['ConsentDetail']['Customer'] = {"id": "8698596991@finvu"}

        aa_response = send_consent_to_aa(data, aa, request.fiu, customer)

        if aa_response['success']:
            # Handle successful response from AA, possibly storing consent details in the DB
            customer_vua = data['ConsentDetail']['Customer']['id']
            fiu_aa = FIUAARegistration.objects.get(fiu=request.fiu, account_aggregator=aa)
            redirection_url = generate_redirect_url(request.fiu.fiu_client_id,
                                                    "FIU",
                                                    customer_vua, 
                                                    request.fiu.consent_redirection_url,
                                                    aa_response['data']['consent_handle'],
                                                    fiu_aa.fiu_aa_aes_token,
                                                    aa.aa_webview_url)
            aa_response['data']['redirect_url'] = redirection_url
            return create_response(status_code=200, data=aa_response['data'])

        # Handle failure response from AA
        return create_response(status_code=400, data=aa_response['data'])

    except json.JSONDecodeError:
        return create_response(status_code=400, error='Invalid JSON format.')
    except Exception as e:
        return create_response(status_code=500, error=str(e))

@fiu_token_required
def handle_consent_get(request):
    try:
        customer_id = request.GET.get('customer', '')
        page = request.GET.get('page', 1)
        page_size = 10  # Set the number of items per page

        if customer_id:
            # Verify the customer belongs to the FIU
            try:
                customer = FIUCustomer.objects.get(id=customer_id, fiu=request.fiu)
            except FIUCustomer.DoesNotExist:
                return create_response(status_code=404, error="Customer not found or does not belong to this FIU")

            consents_queryset = ConsentDetail.objects.filter(fiu=request.fiu, customer=customer)
        else:
            consents_queryset = ConsentDetail.objects.filter(fiu=request.fiu)

        # Paginate the consents queryset
        paginator = Paginator(consents_queryset, page_size)
        try:
            consents = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            consents = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page of results.
            consents = paginator.page(paginator.num_pages)

        consents_list = [
            {
                "consent_handle": consent.consent_handle,
                "customer_id": str(consent.customer.id),
                "status": consent.status
            } for consent in consents
        ]

        return create_response(data={"consents": consents_list})

    except Exception as e:
        return create_response(status_code=500, error=str(e))


@require_http_methods(["GET"])  # This decorator ensures that only GET requests are allowed
@fiu_token_required
def fetch_consent_handle_details(request, consent_handle):
    try:
        # Fetch the consent detail along with related FIU and AA using select_related for efficiency
        consent_detail = ConsentDetail.objects.select_related('fiu', 'aa').get(consent_handle=consent_handle)
    except ConsentDetail.DoesNotExist:
        return JsonResponse({"error": "Consent detail not found"}, status=status.HTTP_404_NOT_FOUND)

    # Use the associated FIU and AA directly from the consent_detail
    fiu = consent_detail.fiu
    aa = consent_detail.aa

    try:
        # Call the service function with the consent detail, and its associated FIU and AA
        response = handle_consent_service(consent_handle, fiu=fiu, aa=aa)
        # Assuming response from handle_consent_service is a dictionary that can be directly passed to JsonResponse
        return JsonResponse(response.json(), status=status.HTTP_200_OK)
    except requests.exceptions.RequestException as e:
        # Handle any exceptions during the service call
        return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    

@require_http_methods(["GET"])  # This decorator ensures that only GET requests are allowed
@fiu_token_required
def fetch_consent_id_details(request, consent_id):
    try:
        # Fetch the consent detail along with related FIU and AA using select_related for efficiency
        consent_detail = ConsentDetail.objects.select_related('fiu', 'aa').get(consent_id=consent_id)
    except ConsentDetail.DoesNotExist:
        return JsonResponse({"error": "Consent detail not found"}, status=status.HTTP_404_NOT_FOUND)

    # Use the associated FIU and AA directly from the consent_detail
    fiu = consent_detail.fiu
    aa = consent_detail.aa

    try:
        # Call the service function with the consent detail, and its associated FIU and AA
        response = get_from_consent_id(consent_id, fiu=fiu, aa=aa)
        # Assuming response from handle_consent_service is a dictionary that can be directly passed to JsonResponse
        return JsonResponse(response.json(), status=status.HTTP_200_OK)
    except requests.exceptions.RequestException as e:
        # Handle any exceptions during the service call
        return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    