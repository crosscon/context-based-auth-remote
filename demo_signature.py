from lib.cert_funcs import sign_nonce_with_key, import_ecc_key

from dotenv import load_dotenv
from base64 import b64encode, b64decode

import os

load_dotenv()

SIGN_KEY_PATH = os.environ.get("SIGN_KEY_PATH")

SIGN_KEY = import_ecc_key(
    SIGN_KEY_PATH
)

nonce = b64encode(bytes([0 for _ in range(16)]))
signed_nonce = b64decode(sign_nonce_with_key(nonce, SIGN_KEY))
size = len(signed_nonce)
num_string = ", ".join([str(int(b)) for b in signed_nonce])
print(f"char SERVER_TEST_SIGNATURE[{size}] = {{ {num_string} }};")

