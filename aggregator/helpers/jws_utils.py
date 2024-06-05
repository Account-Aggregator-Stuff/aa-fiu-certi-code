from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from jose import jwk, jws

# Replace these variables with your actual key and payload values
key = {
    "keys": [
        {
            "p": "_a0iOHrbZ2hW13Kd3gkdcXQzKW4FV5u2i41gqfTS8ByIbhDJGpygEegsZCyJ5yd5eAy8mr8RBHnGipi8aXBJ96kESxoSTmcc0L_Mge5sw_JMmcoT8Ww71ltN3eU6AcLEnygW08So6HLlLBhCxSiK3TmSU84rB-uWo6yGNDli2ak",
            "kty": "RSA",
            "q": "lKEjAgXfTxZLVu9aZVMXUXygihru_v-yIeQpCX_20RzhuLtmBWer4V69ruSe4Uy8rTdQet8ki8LMdXYK7LCy1-W79EZVFgyu1uzM2pBoidk4mZ107VOAwnZZfgU4RO6sNr-_QLlnh8b1xY5at4seHLdy8Hwe2OiQel0a97mQ9q0",
            "d": "bP24N0yLfQdHOzhHEW2-FUQRByO7H7XwSDu0r06QW2GLoej2I9AponYODfi4-WvtUols96ineXI3lhDGkPQgIpl3YxumpDrJpp2pYZVSXEQDpawfFejji32S2I61qDH45esGYVicyyr77aY5c9f34PhkJZAEpO6R9KuK9C9a6lGc2llYyL00cR5sfyiZd2OPVBKsIKZYB2wVWjztpxvGghDX6blQhVCpaDVssJPWYE32jS8f1dh-V-ndtFi0FTlaYUeNHtV3v1F4lxf7FWvVHJx9En_8hBjNPkG7cr0O8lLsLYp0u3TQ1sNxI50GpwhnC0BT331LdQbEfO3KEfEIoQ",
            "e": "AQAB",
            "use": "sig",
            "kid": "8648e6b5-9030-42a2-a99f-773388ea7318",
            "qi": "Mdif2FoWrljXpbmfiu1Ps974DLdNe4lSC4g3iVzgzQEUbSrklakhSjH9ccfRRR1-bsdGLTsvqGyZB9RPTphCwhKZIff8PkhbFslIKvv-iVw_g5AB053-XjygHWunLx5tQWwSADJ0UVQLWYt4LG8eUwd-O4AA6pYcT2zSfkQ_0OI",
            "dp": "Wnt2yU6JE8lTsGVhieEWb3FTDmP_48_WvNAgun5o_twujZPPJ37WWYzGyLRaO-kImplwbIHaQA5vkuAH1FQJDh1rOp6CCRUeYhcHixDQGtRCHljF5EcG0N6gV5V7q0UdfOd_vOlYlhDlTWUZ69kaLu5qExpmntyZTqgq9lXBvIE",
            "alg": "RS256",
            "dq": "iipdO9UvqPqFoNQyiTy70ZF0P84X3E7gTicmiuE9FVmu76atiVq9am1DEaEPnUtTngZstzxWYeH9ZTgNocgFCTRUDBmRoUS7B6rsKEXUGEkpF4xLFQ_qA1w3hzHdBB-HUgHgDZANEShAcp0J8dPOc02J-Mq5dlSDcmy41A7aFqU",
            "n": "k0fEW9llwtu-Xsm5HopIUfmq2rDJnPM100qYQdmfsxI7W9JqXXORpt3FnB1SUX5dbmG-b8u3sjm9wb9tOcl1STG9JWSPAN4w2rGJIrsOyGS2aU3VuvJyg01jpxkMI9QGkNngETk8LbXVN1W7t9yMZA9VpIvZPXFBCCnC3QraYPP_B__VVMEjQPWULPK6tMH2zLY00m2E_Nbb3-FawdWyqlq7qegvEamm7GSme9270BMG997ki0Q-atinGzN2cXW_rZZdd0CNIINdsb5I-lKEXFvv-jJrakJOsaETfL3XRat19iTrqcBrIqW4gawP9eevUW2mIXidCgakRcNkVQV9NQ"
        }
    ]
}

payload = ""
# Load the private key
private_key = serialization.load_pem_private_key(key.encode(), password=None)

# Create a JsonWebSignature object for the signing
signer_jws = jws.JWS(payload)

# Set the signature algorithm on the JWS
signer_jws.add_signature(private_key, alg="RS256", use="sig")

# Produce the compact serialization with an empty/detached payload,
# which is the encoded header + ".." + the encoded signature
compact_serialization = signer_jws.serialize()

print(compact_serialization)