


import json

from django.http import JsonResponse
import requests
from aggregator.decorators import fiu_token_required
from aggregator.helpers.consent_utils import send_consent_to_aa
from aggregator.helpers.utils import create_response
from aggregator.models import AccountAggregator, FIUCustomer, FIUEntity
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status

from aggregator.service.get_consent_id_service import get_from_consent_id
from aggregator.service.handle_consent_service import handle_consent_service

@csrf_exempt
def consent(request, aa_name = "suma", fiu=None, customer=None):
    try:
        aa = AccountAggregator.objects.get(aa_name=aa_name)
    except AccountAggregator.DoesNotExist:
        return create_response(status_code=400, error='AA not found.')
    if not customer:
        customer = FIUCustomer.objects.first()
    if not fiu:
        fiu = FIUEntity.objects.get(id=1)
    try:
        response = send_consent_to_aa(json.loads(request.body), aa, fiu, customer, tsp=True)
        return JsonResponse(response.json(), status=response.status_code)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@csrf_exempt
def handle_consent(request, consent_handle):
    if request.method == 'GET':
        try:
            aa = AccountAggregator.objects.get(aa_name="suma")
            response = handle_consent_service(consent_handle, fiu=FIUEntity.objects.get(id=4), aa=aa)
            return JsonResponse(response.json(), status=response.status_code)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@csrf_exempt
def fetch_consent_details(request, consent_id):
    if request.method == 'GET':
        try:
            aa = AccountAggregator.objects.get(aa_name="suma")
            fiu= FIUEntity.objects.get(id=4)
            response = get_from_consent_id(consent_id, fiu, aa)
            return JsonResponse(response.json(), status=response.status_code)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)