ERROR_CODES = {
    "InvalidRequest": 400,
    "InvalidURI": 400,
    "InvalidSecurity": 400,
    "SignatureDoesNotMatch": 400,
    "InvalidNotifier": 400,
    "InvalidConsentId": 400,
    "InvalidConsentStatus": 400,
    "Unauthorized": 401,
    "NotFound": 404,
    "IdempotencyError": 409,
    "PreconditionFailed": 412,
    "InternalError": 500,
    "NotImplemented": 501,
    "ServiceUnavailable": 503
}

CONSENT_ERROR_CODES = {
    "InvalidRequest": 400,
    "InvalidURI": 400,
    "InvalidSecurity": 400,
    "SignatureDoesNotMatch": 400,
    "InvalidNotifier": 400,
    "InvalidConsentId": 400,
    "InvalidConsentStatus": 400,
    "Unauthorized": 401,
    "NotFound": 404,
    "IdempotencyError": 409,
    "PreconditionFailed": 412,
    "InternalError": 500,
    "NotImplemented": 501,
    "ServiceUnavailable": 503
}

ERROR_MESSAGES = {
    "InvalidRequest": "Invalid request. Details: {}",
    "InvalidURI": "Invalid URI. Details: {}",
    "InvalidSecurity": "Invalid security parameters. Details: {}",
    "SignatureDoesNotMatch": "Signature does not match. Details: {}",
    "InvalidNotifier": "Invalid notifier details. Details: {}",
    "InvalidConsentId": "Invalid consent ID provided. Details: {}",
    "InvalidConsentStatus": "Invalid consent status. Details: {}",
    "Unauthorized": "Unauthorized access. Details: {}",
    "NotFound": "Resource not found. Details: {}",
    "IdempotencyError": "Idempotency error. The provided UUID/ID is not unique. Details: {}",
    "PreconditionFailed": "Precondition failed. Details: {}",
    "InternalError": "Internal server error. Details: {}",
    "NotImplemented": "Feature/API not implemented. Details: {}",
    "ServiceUnavailable": "Service is currently unavailable. Please try again later. Details: {}"
}
