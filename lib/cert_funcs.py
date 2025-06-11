from os import path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta, UTC
from base64 import b64encode, b64decode


def generate_ecc_key():
    key = ec.generate_private_key(
        ec.SECP256R1(),
        backend=default_backend()
    )

    return key


def export_ecc_key(path: str, key: ec.EllipticCurvePrivateKey):
    with open(path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )


def import_ecc_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )


def export_certificate(path: str, cert: x509.Certificate):
    with open(path, "wb") as f:
        f.write(
            cert.public_bytes(
                encoding=serialization.Encoding.PEM
            )
        )


def import_certificate(path: str):
    with open(path, "rb") as f:
        return x509.load_pem_x509_certificate(
            f.read(),
            backend=default_backend()
        )


def generate_ecc_ca(key: ec.EllipticCurvePrivateKey):
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"remote-ca")
    ])

    now = datetime.now(UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(
            x509.BasicConstraints(
                ca=True, path_length=None
            ), critical=True
        )
        .sign(
            private_key=key,
            algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )


def generate_ecc_self_signed_certificate(key: ec.EllipticCurvePrivateKey):
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"remote-verifier")
    ])

    now = datetime.now(UTC)

    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=3650))
        .sign(
            private_key=key,
            algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )


def generate_ecc_prover_verifier_certificate(key: ec.EllipticCurvePrivateKey):
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"remote-signature")
    ])

    now = datetime.now(UTC)

    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=3650))
        .sign(
            private_key = key,
            algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )


def sign_csr_with_ecc_ca(csr_pem_bytes: bytes, ca_key: ec.EllipticCurvePrivateKey, ca_cert: x509.Certificate) -> bytes:
    csr = x509.load_pem_x509_csr(
        csr_pem_bytes,
        backend=default_backend()
    )

    now = datetime.now(UTC)
    cert = (x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(
                ca=False,
                path_length=None
            ),
            critical=True
        )
        .sign(
            private_key=ca_key,
            algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )

    return cert.public_bytes(
        serialization.Encoding.PEM
    )


def sign_nonce_with_key(nonce: str, key: ec.EllipticCurvePrivateKey) -> bytes:
    nonce_bytes = b64decode(nonce)
    signature = key.sign(
        nonce_bytes, ec.ECDSA(hashes.SHA512())
    )
    return b64encode(signature)


def get_csr_cn(csr_pem_bytes: bytes) -> bytes | None:
    try:
        csr = x509.load_pem_x509_csr(csr_pem_bytes, default_backend())
        for attribute in csr.subject:
            if attribute.oid == x509.NameOID.COMMON_NAME:
                return attribute.value
    except:
        pass

    return None

