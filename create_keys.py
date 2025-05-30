from lib.cert_funcs import *

from dotenv import load_dotenv

import os


load_dotenv()


CA_KEY_PATH = os.environ.get("CA_KEY_PATH")
CA_CERT_PATH = os.environ.get("CA_CERT_PATH")
SSL_KEY_PATH = os.environ.get("SSL_KEY_PATH")
SSL_CERT_PATH = os.environ.get("SSL_CERT_PATH")
SIGN_KEY_PATH = os.environ.get("SIGN_KEY_PATH")
SIGN_CERT_PATH = os.environ.get("SIGN_CERT_PATH")

if None in [
    CA_KEY_PATH,
    CA_CERT_PATH,
    SSL_KEY_PATH,
    SSL_CERT_PATH,
    SIGN_KEY_PATH,
    SIGN_CERT_PATH
]:
    print("ERROR: Missing path variables.")
    exit()
 

def create_self_signed_certificate():
    key = generate_ecc_key()
    cert = generate_ecc_self_signed_certificate(key)

    export_ecc_key(SSL_KEY_PATH, key)
    export_certificate(SSL_CERT_PATH, cert)


def create_client_ca():
    key = generate_ecc_key()
    ca = generate_ecc_ca(key)

    export_ecc_key(CA_KEY_PATH, key)
    export_certificate(CA_CERT_PATH, ca)


def create_signature_certificate():
    key = generate_ecc_key()
    cert = generate_ecc_prover_verifier_certificate(key)

    export_ecc_key(SIGN_KEY_PATH, key)
    export_certificate(SIGN_CERT_PATH, cert)


def main():
    create_self_signed_certificate()
    create_client_ca()
    create_signature_certificate()


if __name__ == "__main__":
    main()
