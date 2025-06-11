from lib.single_command_buffer import SingleCommandBuffer
from lib.cert_funcs import sign_csr_with_ecc_ca, import_certificate, import_ecc_key, get_csr_cn, sign_nonce_with_key

from dotenv import load_dotenv
from base64 import b64encode, b64decode

import logging
import socket
import ssl
import os
import time


load_dotenv()

CA_KEY_PATH = os.environ.get("CA_KEY_PATH", "")
CA_CERT_PATH = os.environ.get("CA_CERT_PATH", "")
SSL_KEY_PATH = os.environ.get("SSL_KEY_PATH", "")
SSL_CERT_PATH = os.environ.get("SSL_CERT_PATH", "")
SIGN_KEY_PATH = os.environ.get("SIGN_KEY_PATH", "")
SIGN_CERT_PATH = os.environ.get("SIGN_CERT_PATH", "")

CA_KEY = import_ecc_key(
    CA_KEY_PATH
)
CA_CERT = import_certificate(
    CA_CERT_PATH
)
SSL_KEY = import_ecc_key(
    SSL_KEY_PATH
)
SSL_CERT = import_certificate(
    SSL_CERT_PATH
)
SIGN_KEY = import_ecc_key(
    SIGN_KEY_PATH
)
SIGN_CERT = import_certificate(
    SIGN_CERT_PATH
)



def sign_csr(csr: bytes) -> bytes:
    return sign_csr_with_ecc_ca(
        csr,
        CA_KEY,
        CA_CERT
    )

def sign_nonce(nonce: bytes) -> bytes:
    return sign_nonce_with_key(nonce, SIGN_KEY)

def demo_nonce() -> str:
    nonce = b64encode(bytes([0 for _ in range(16)]))
    signed_nonce = b64decode(sign_nonce(nonce))
    size = len(signed_nonce)
    num_string = ", ".join([str(int(b)) for b in signed_nonce])
    return f"char SERVER_TEST_SIGNATURE[{size}] = {{ {num_string} }};"

enrolled = []



def command_enroll_certificate(cmd: list[bytes]) -> bytes:
    try:
        raw_csr = "\n".join([l for l in cmd[1:] if len(l) > 0]).encode()
        common_name = get_csr_cn(raw_csr)

        if common_name in enrolled:
            print("Already enrolled.")
            return b"ERR\nALREADY_ENROLLED\n\n"
        else:
            signed = sign_csr(raw_csr)
            #enrolled.append(common_name)
            return b"SUCC\n" + signed + b"\n\n"
    except:
        print("Error.")
        return b"ERR\n\n"


def command_enroll_device_csi(client_id: str | None, cmd: list[bytes]) -> bytes:
    raw_csi = []
    try:
        raw_csi = [base64.b64decode(s) for s in cmd[1:]]
    except:
        pass
    print(f"Client {client_id} wants to enroll {len(cmd) - 1} samples")
    return b"SUCC\n3u6tvu7v3u6tvu7v3u6tvu7v3u6tvu7v\n\n"


def command_prove_device(client_id: str | None, cmd: list[bytes]) -> bytes:
    if client_id == None:
        print("Unauthorized prove command!")
        return b"ERR\nNO_AUTH\n\n"

    nonce = cmd[1]
    csi_data = cmd[2:]
    print(f"Client {client_id} requested prove with {len(csi) - 2)} CSI samples")

    signed_nonce = sign_nonce(nonce).decode()

    return f"SUCC\n{signed_nonce}\n\n".encode()


def command_test(client_id: str | None, cmd: list[bytes]) -> bytes:
    if remote_id != None:
        print(f"Test command from '{remote_id}'.")
        return b"SUCC\n0\n\n"
    else:
        print("Unauthorized test command!")
        return b"ERR\nNO_AUTH\n\n"



def handle_client(client: socket.socket | ssl.SSLSocket, remote_id: str | None):
    c = 0
    print("ID:", remote_id)
    buf = SingleCommandBuffer()

    while True:
        try:
            if not (rcv := client.recv(128)):
                print("Client disconnected.")
                break
            buf.update(rcv)

            while (cmd := buf.get_next_command()):
                cmd = [c.decode() for c in cmd]
                if cmd[0] == "ENROLL":
                    client.send(command_enroll_certificate(cmd))
                elif cmd[0] == "ENROLL_CSI":
                    client.send(command_enroll_device_csi(remote_id, cmd))
                elif cmd[0] == "TEST":
                    client.send(command_test(remote_id, cmd))
                elif cmd[0] == "PROVE":
                    client.send(command_prove_device(remote_id, cmd))
                else:
                    print(f"Invalid command from client ({cmd[0]}).")
                    print(cmd)
                    try:
                        client.send(b"ERR\nINV_CMD\n\n")
                    except Exception as e:
                        print("E INV CMD:", e)
                        pass
        except Exception as e:
            print("E GENERAL:", e)
            try:
                client.send(b"ERR\nINT\n\n")
            except:
                pass
            pass


def start_server():
    logging.basicConfig(level=logging.DEBUG)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.set_ciphers('ALL')

    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers('ECDHE+AESGCM:!aNULL:!MD5:!DSS')

    context.load_cert_chain(
        certfile=SSL_CERT_PATH,
        keyfile=SSL_KEY_PATH
    )
    context.load_verify_locations(
        cafile=CA_CERT_PATH
    )
    context.verify_mode = ssl.CERT_OPTIONAL

    sock.bind(("0.0.0.0", 5432))
    sock.listen()

    print("Listening...")

    while True:
        client, _ = sock.accept()
        print("Client connected.")
        try:
            wrapped_client = context.wrap_socket(
                client,
                server_side=True
            )

            client_cert = wrapped_client.getpeercert()
            if client_cert:
                subject = dict(x[0] for x in client_cert["subject"])
                common_name = subject.get("commonName")
                remote_id = common_name or None
            else:
                print("Client didn't use Certificate")
                remote_id = None

            handle_client(wrapped_client, remote_id)
        except ssl.SSLError as e:
            print("SSL Error:")
            print(e)
            #import traceback
            #traceback.print_exc()
        except Exception as e:
            print("General error accepting client")
        finally:
            try:
                wrapped_client.shutdown(socket.SHUT_RDWR)
            except:
                pass
            client.close()


def main():
    print("Use the following line as configuration for the demo host application to validate that the public key is enrolled correctly:")
    print(demo_nonce())
    print()

    start_server()


if __name__ == "__main__":
    main()
