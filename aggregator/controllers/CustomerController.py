import json
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from aggregator.models import FIUCustomer
from aggregator.decorators import fiu_token_required
from aggregator.helpers.utils import create_response  # Import the utility function
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@require_http_methods(["POST"])
@fiu_token_required
@csrf_exempt
def register(request):
    # Assuming the request content type is JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return create_response(status_code=400, error='Invalid JSON')


    name = data.get('name')
    phone_number = data.get('phone_number')
    email = data.get('email', '')
    pan = data.get('pan', '')

    if not name or not phone_number:
        return create_response(status_code=400, error='Name and phone number are required.')

    try:
        existing_customer = FIUCustomer.objects.get(phone_number=phone_number, fiu=request.fiu)
        return create_response(message='Customer already registered by FIU', data={'id': str(existing_customer.id)})
    except FIUCustomer.DoesNotExist:
        # Proceed with registration
        pass

    try:
        new_customer = FIUCustomer.objects.create(
            name=name,
            phone_number=phone_number,
            email=email,
            pan=pan,
            fiu=request.fiu
        )
    except ValidationError as e:
        return create_response(status_code=400, error=str(e.messages))

    return create_response(status_code=201, message='Customer registered successfully.', data={'id': str(new_customer.id)})


@require_http_methods(["GET"])
@fiu_token_required
@csrf_exempt
def get_customer_details(request, id):
    # Attempt to fetch the customer who belongs to the FIU provided in the token
    try:
        customer = FIUCustomer.objects.get(pk=id, fiu=request.fiu)
    except FIUCustomer.DoesNotExist:
        # If no such customer exists, return a "Not Found" response
        return create_response(status_code=404, error='Customer not found or does not belong to this FIU.')

    # Prepare the customer data to return
    customer_data = {
        'id': str(customer.id),
        'name': customer.name,
        'phone_number': customer.phone_number,
        'email': customer.email,
        'pan': customer.pan,
        # Add any other fields you need to return
    }

    return create_response(message='Customer details fetched successfully.', data={'customer': customer_data})


@require_http_methods(["GET"])
@fiu_token_required
@csrf_exempt
def list_customers(request):
    # Retrieve customers associated with the FIU from the request
    customers = FIUCustomer.objects.filter(fiu=request.fiu).order_by('created_at')

    # Set up pagination
    paginator = Paginator(customers, 10)  # Show 10 customers per page
    page = request.GET.get('page', 1)

    try:
        customers = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        customers = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results
        customers = paginator.page(paginator.num_pages)

    # Format the customer data for the response
    customers_data = [
        {
            'id': str(customer.id),
            'name': customer.name,
            'phone_number': customer.phone_number,
            'email': customer.email,
            'pan': customer.pan
            # Add other fields as needed
        } for customer in customers
    ]

    return create_response(message='Customers fetched successfully.', data={'customers': customers_data, 'page': page, 'total_pages': paginator.num_pages})
