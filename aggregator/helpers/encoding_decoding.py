import base64


def base64url_decode(encoded_str):
    # Add padding characters '=' if needed
    padding = (4 - len(encoded_str) % 4) % 4
    encoded_str += "=" * padding

    # Replace URL-safe characters and decode
    decoded_bytes = base64.urlsafe_b64decode(encoded_str)

    # Convert bytes to string
    decoded_str = decoded_bytes.decode('utf-8')

    return decoded_str