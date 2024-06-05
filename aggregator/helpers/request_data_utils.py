import json
import uuid
import requests
from datetime import datetime
from django.http import JsonResponse

from aggregator.auth.jws import generate_jws_detached, generate_token
from aggregator.globals.config import API_VERSION
from aggregator.globals.session_status import SESSION_ACTIVE, SESSION_FAILED
from aggregator.models import ConsentDetail, FIDataRequest
from aggregator.service.fi_request_service import error_handling_fi_request

def send_fi_request_to_aa(request_body, aa, fiu, customer, tsp=False):
    # Directly using the request_body data for the payload    
    payload = {
        "ver": API_VERSION,  # Constant version
        "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',  # Current timestamp in the specified format
        "txnid": str(uuid.uuid4()),
        "FIDataRange": request_body.get("FIDataRange"),
        "Consent": request_body.get("Consent"),
        "KeyMaterial": request_body.get("KeyMaterial")
    }

    # Specify the URL of the AA endpoint for FI requests
    aa_url = f"{aa.aa_base_path}/FI/request"

    headers = {
        'x-jws-signature': generate_jws_detached(json.dumps(payload), fiu),
        'client_api_key': generate_token(fiu),
        'Content-Type': 'application/json'
    }

    try:
        # Send the FI request to the AA
        print ("FI Request Payload:", payload)
        response = requests.post(aa_url, data=json.dumps(payload), headers=headers)
        print ("FI Request Response:", response.text)        
        # Return the response from the AA, handling response status codes as needed
        if response.status_code == 200:
            session_status = error_handling_fi_request(response, payload["txnid"], payload["Consent"]["id"])
            session_status = SESSION_ACTIVE
            if session_status != SESSION_FAILED:
                fi_data_request = FIDataRequest(
                    consent_id=ConsentDetail.objects.get(consent_id=payload["Consent"]["id"]),
                    session_id=response.json().get("sessionId"),
                    key_material=payload["KeyMaterial"],
                    customer_id=customer.id,
                    status=SESSION_ACTIVE,
                    private_key="",
                    txnid=payload["txnid"]
                )
                fi_data_request.save()
                return JsonResponse(response.json(), safe=False, status=response.status_code)
            else:
                return JsonResponse({"error": "Bad Response Received from AA", "details": "Session failed"}, status=400)
        else:
            # Handle non-successful responses
            return JsonResponse({"error": "Failed to send FI request", "details": response.text}, status=response.status_code)

    except requests.exceptions.RequestException as e:
        # Handle request exceptions
        return JsonResponse({"error": "Failed to send FI request", "details": str(e)}, status=503)
