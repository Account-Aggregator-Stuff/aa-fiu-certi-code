from django.urls import path
from aggregator.controllers import FIUController, AggregatorController, FIDataController, CustomerController, CoreTSPController

# Customer-related endpoints
urlpatterns = [
    # Customer registration
    path('fiu/customer/register', CustomerController.register, name='customer_register'),
    
    # Retrieve customer details by ID
    path('fiu/customer/<uuid:id>/', CustomerController.get_customer_details, name='get-customer-details'),
    
    # List customers with pagination
    path('fiu/customer/', CustomerController.list_customers, name='list-customers'),
]

# Consent-related endpoints
urlpatterns += [
    # Receive notifications about consent status
    path('Consent/Notification', FIUController.consent_notification, name='consent_notification'),

    # Manage consents
    path('fiu/consent/handle/<str:consent_handle>', AggregatorController.fetch_consent_handle_details, name='fiu_consent-handle'),
    path('fiu/consent/<str:consent_id>', AggregatorController.fetch_consent_id_details, name='fiu_fetch-consent-details'),
    path('fiu/consent', AggregatorController.consent, name='fiu_consent'),
]

# Financial Information (FI) related endpoints
urlpatterns += [
    # Receive notifications about FI data
    path('FI/Notification', FIUController.fi_notification, name='fi_notification'),

    # FI data requests and fetching
    path('fiu/fi/request', FIDataController.fi_data_request, name='fi_data_request'),
    path('fiu/fi/fetch/<str:session_id>', FIDataController.fi_data_fetch, name='fi_data_fetch'),
    path('fiu/fi/customer_data', FIDataController.customer_data_fetch, name='customer_data_fetch'),
]

# Miscellaneous or utility endpoints
urlpatterns += [
    # Heartbeat or health check endpoint for the Aggregator
    path('consent/handle/<str:consent_handle>', CoreTSPController.handle_consent, name='consent-handle'),
    path('consent/<str:consent_id>', CoreTSPController.fetch_consent_details, name='consent-handle'),
    path('consent', CoreTSPController.consent, name='consent'),
    path('fi/request', FIDataController.fi_data_request, name='fi_data_request'),
    path('fi/fetch/<str:session_id>', FIDataController.fi_data_fetch, name='fi_data_fetch'),
    path('heartbeat', AggregatorController.heartbeat, name='AA_heartbeat'),
]
