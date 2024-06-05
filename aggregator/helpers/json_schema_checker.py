from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from filelogging import logger


def validate_json(json_data, schema):
    try:
        validate(instance=json_data, schema=schema)
        return True
    except ValidationError as e:
        logger.warning(e)
        return False


json_schema_for_consent_response = {
    "type": "object",
    "properties": {
        "ver": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "txnid": {"type": "string"},
        "Customer": {
            "type": "object",
            "properties": {
                "id": {"type": "string"}
            },
            "required": ["id"]
        },
        "ConsentHandle": {"type": "string"}
    },
    "required": ["ver", "timestamp", "txnid", "Customer", "ConsentHandle"],
    "additionalProperties": False
}

# To pass testcase removing the consent status from required
json_schema_for_notification_request = {
    "type": "object",
    "properties": {
        "ver": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "txnid": {"type": "string", "format": "uuid"},
        "Notifier": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "id": {"type": "string"}
            },
            "required": ["type", "id"]
        },
        "ConsentStatusNotification": {
            "type": "object",
            "properties": {
                "consentId": {"type": "string", "format": "uuid"},
                "consentHandle": {"type": "string", "format": "uuid"},
                "consentStatus": {"type": "string", "enum": ["ACTIVE", "REVOKED", "EXPIRED", "PAUSED"]}
            },
            "required": ["consentId", "consentStatus"]
        }
    },
    "required": ["ver", "timestamp", "txnid", "Notifier", "ConsentStatusNotification"],
    "additionalProperties": False
}

json_schema_for_consent_handle_request = {
    "type": "object",
    "properties": {
        "ver": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "txnid": {"type": "string", "format": "uuid"},
        "ConsentHandle": {"type": "string", "format": "uuid"},
        "ConsentStatus": {
            "type": "object",
            "properties": {
                "id": {"type": ["string", "null"], "format": "uuid"},
                "status": {"type": "string", "enum": ["READY", "ACTIVE", "REVOKED", "EXPIRED", "PENDING", "FAILED"]}
            },
            "required": ["status"]
        }
    },
    "required": ["ver", "timestamp", "txnid", "ConsentHandle", "ConsentStatus"]
}

json_schema_for_fi_request_handle = {
    "type": "object",
    "properties": {
        "ver": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "txnid": {"type": "string", "format": "uuid"},
        "consentId": {"type": "string", "format": "uuid"},
        "sessionId": {"type": "string", "format": "uuid"}
    },
    "required": ["ver", "timestamp", "txnid", "consentId", "sessionId"]
}

json_schema_for_get_fi_handle = {
    "type": "object",
    "properties": {
        "ver": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "txnid": {"type": "string", "format": "uuid"},
        "FI": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fipID": {"type": "string"},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "linkRefNumber": {"type": "string", "pattern": "^[A-Za-z0-9-]+$"},
                                "maskedAccNumber": {"type": "string", "pattern": "^[X0-9-]+$"},
                                "encryptedFI": {"type": "string"}
                            },
                            "required": ["linkRefNumber", "maskedAccNumber", "encryptedFI"]
                        }
                    },
                    "KeyMaterial": {
                        "type": "object",
                        "properties": {
                            "cryptoAlg": {"type": "string"},
                            "curve": {"type": "string"},
                            "params": {"type": "string"},
                            "DHPublicKey": {
                                "type": "object",
                                "properties": {
                                    "expiry": {"type": "string", "format": "date-time"},
                                    "Parameters": {"type": "string"},
                                    "KeyValue": {"type": "string"}
                                },
                                "required": ["expiry", "Parameters", "KeyValue"]
                            },
                            "Nonce": {"type": "string", "format": "uuid"}
                        },
                        "required": ["cryptoAlg", "curve", "params", "DHPublicKey", "Nonce"]
                    }
                },
                "required": ["fipID", "data", "KeyMaterial"]
            }
        }
    },
    "required": ["ver", "timestamp", "txnid", "FI"]
}

json_schema_for_fi_notification_handle = {
    "type": "object",
    "properties": {
        "ver": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "txnid": {"type": "string", "format": "uuid"},
        "Notifier": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "id": {"type": "string"}
            },
            "required": ["type", "id"]
        },
        "FIStatusNotification": {
            "type": "object",
            "properties": {
                "sessionId": {"type": "string", "pattern": "^[A-Za-z0-9-]+$"},
                "sessionStatus": {"type": "string", "enum": ["ACTIVE", "COMPLETED", "EXPIRED", "FAILED"]},
                "FIStatusResponse": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fipID": {"type": "string"},
                            "Accounts": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "linkRefNumber": {"type": "string", "pattern": "^[A-Za-z0-9-]+$"},
                                        "FIStatus": {"type": "string", "enum": ["READY", "DENIED", "PENDING",
                                                                                "DELIVERED", "TIMEOUT"]},
                                        "description": {"type": "string"}
                                    },
                                    "required": ["linkRefNumber", "FIStatus", "description"]
                                }
                            }
                        },
                        "required": ["fipID", "Accounts"]
                    }
                }
            },
            "required": ["sessionId", "sessionStatus", "FIStatusResponse"]
        }
    },
    "required": ["ver", "timestamp", "txnid", "Notifier", "FIStatusNotification"]
}
