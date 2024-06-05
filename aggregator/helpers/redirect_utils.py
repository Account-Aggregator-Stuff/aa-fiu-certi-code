from datetime import datetime
import uuid
from cryptography.hazmat.primitives import hashes, kdf, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from base64 import urlsafe_b64encode, urlsafe_b64decode
import base64
from datetime import datetime, timezone

# Constants
AES_ALGO = algorithms.AES
KEY_ALGO = hashes.SHA256
AES_CBC_PKCS5 = modes.CBC
SECRET_KEY = ""  # You should replace this with your actual secret key
IV = b'\x00' * 16  # 16 bytes IV set to zero

def get_cipher(key, iv=IV):
    backend = default_backend()
    return Cipher(AES_ALGO(key), AES_CBC_PKCS5(iv), backend=backend)

def encrypt_payload(payload, salt):
    kdf = PBKDF2HMAC(
        algorithm=KEY_ALGO(),
        length=32,
        salt=salt.encode(),
        iterations=65536,
        backend=default_backend()
    )
    print (SECRET_KEY)
    key = kdf.derive(SECRET_KEY.encode())
    cipher = get_cipher(key)
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(AES_ALGO.block_size).padder()
    padded_data = padder.update(payload.encode()) + padder.finalize()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return base64.urlsafe_b64encode(encrypted).decode()

def construct_payload(txnid, sessionid, userid, redirect, srcref, fipid=None, email=None, pan=None):
    payload = "txnid=" + str(txnid) + "&sessionid=" + str(sessionid) + "&userid=" + str(userid) + "&redirect=" + str(redirect) + "&srcref=" + str(srcref)
    if fipid:
        payload += "&fipid=" + str(fipid)
    if email:
        payload += "&email=" + str(email)
    if pan:
        payload += "&pan=" + str(pan)
    return payload

def xor_and_base64_encode(data, key):
    # Ensure the key is long enough to cover the data by repeating it
    extended_key = (key * (len(data) // len(key) + 1))[:len(data)]
    # Perform XOR operation
    xored = bytes(a ^ b for a, b in zip(data.encode(), extended_key.encode()))
    # Base64 encode
    return base64.b64encode(xored).decode()


def generate_redirect_url(fi, requestor_type, userid, redirect, srcref, aes_token, base_url):
    txnid = str(uuid.uuid4())
    sessionid = str(uuid.uuid4())
    global SECRET_KEY
    SECRET_KEY=aes_token

    print (SECRET_KEY)
    print (txnid, sessionid, userid, redirect, srcref)
    now_utc = datetime.now(timezone.utc)
    salt = now_utc.strftime("%d%m%Y%H%M%S") + now_utc.strftime("%f")[:1]  # Use reqdate as salt
    
    fi_encrypted = xor_and_base64_encode(fi, salt)
    requestor_type_encrypted = xor_and_base64_encode(requestor_type, salt)
    
    payload = construct_payload(txnid, sessionid, userid, redirect, srcref)
    
    encrypted_payload = encrypt_payload(payload, salt)
    redirect_url = f"{base_url}?fi={fi_encrypted}&reqdate={salt}&ecreq={encrypted_payload}"
    
    print("Redirect URL:", redirect_url)

    return redirect_url
# Example usage