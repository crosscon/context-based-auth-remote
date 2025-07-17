from lib.single_command_buffer import SingleCommandBuffer
from lib.cert_funcs import sign_csr_with_ecc_ca, import_certificate, import_ecc_key, get_csr_cn, sign_nonce_with_key
from lib.authenticator import enroll_device, authenticate_device

from dotenv import load_dotenv

import logging
import socket
import ssl
import os


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


CONN_ONLY_MODE = len(os.environ.get("CONN_ONLY_MODE", default="")) > 0
PERMIT_RE_ENROLLMENT = CONN_ONLY_MODE or len(os.environ.get("PERMIT_RE_ENROLLMENT", default="")) > 0
ALLOW_GUEST_NO_CERT = CONN_ONLY_MODE or len(os.environ.get("ALLOW_GUEST_NO_CERT", default="")) > 0
DUMP_INCOMING = CONN_ONLY_MODE or len(os.environ.get("DUMP_INCOMING", default="")) > 0

if CONN_ONLY_MODE or PERMIT_RE_ENROLLMENT or ALLOW_GUEST_NO_CERT:
    print("!WARNING!")
    if CONN_ONLY_MODE:
        print("CONNECTION ONLY MODE ENABLED")
        print("All prove requests will be granted!")
    if PERMIT_RE_ENROLLMENT:
        print("RE-ENROLLMENT ALLOWED")
        print("A device with a given ID can enroll multiple times")
    if ALLOW_GUEST_NO_CERT:
        print("GUESTS WITHOUT CLIENT CERT ALLOWED")
        print("A device can connect and enroll/prove without a valid client certificate")
    if DUMP_INCOMING:
        print("DUMPING INCOMING COMMANDS")
        print("All incoming commands are logged to a file")
    print("Only use when you know what to do!")
    print()


if DUMP_INCOMING and not os.path.exists("./dump"):
    with open("./dump", "w") as f:
        f.write("")


def command_from_parts(parts: list[bytes | str]) -> bytes:
    command = b""
    for part in parts:
        if type(part) == bytes:
            command += part
        else:
            command += str(part).encode()
        command += b"\n"
    return command + b"\n"


def sign_csr(csr: bytes) -> bytes:
    return sign_csr_with_ecc_ca(
        csr,
        CA_KEY,
        CA_CERT
    )

def sign_nonce(nonce: bytes) -> bytes:
    return sign_nonce_with_key(nonce, SIGN_KEY)


enrolled = []



def command_enroll_certificate(cmd: list[str]) -> bytes:
    try:
        raw_csr = "\n".join([l for l in cmd[1:] if len(l) > 0]).encode()
        common_name = get_csr_cn(raw_csr)

        if common_name in enrolled:
            print("Already enrolled.")
            return command_from_parts(["ERR", "ALREADY_ENROLLED"])
        else:
            signed = sign_csr(raw_csr)
            if not PERMIT_RE_ENROLLMENT:
                enrolled.append(common_name)
            return command_from_parts(["SUCC", signed])
    except Exception as e:
        print("EXCEPTION while enrolling device certificate:")
        print(e)

        return command_from_parts(["ERR", "INTERNAL"])


def command_enroll_device_csi(client_id: str | None, cmd: list[str]) -> bytes:
    if client_id == None:
        return command_from_parts(["ERR", "NO_AUTH"])

    csi_data = cmd[1:]

    print(f"Client {client_id} wants to enroll CSI data with {len(csi_data)} samples")

    if CONN_ONLY_MODE:
        print("!CONNECTION ONLY MODE!")
        print("Accepting enrollment request")

        return command_from_parts(["SUCC", "?"])
    else:
        try:
            csi_data = cmd[1:]

            macs = enroll_device(client_id, csi_data)
            if macs == None:
                print("Not enough or invalid CSI data supplied")
                return command_from_parts(["ERR", "INVALID_DATA"])

            print("CSI data enrolled successfully")
            return command_from_parts(["SUCC", macs])
        except Exception as e:
            print("EXCEPTION while enrolling device CSI data:")
            print(e)

            return command_from_parts(["ERR", "INTERNAL"])


def command_prove_device(client_id: str | None, cmd: list[str]) -> bytes:
    if client_id == None:
        print("Unauthorized prove command!")
        return command_from_parts(["ERR", "NO_AUTH"])

    nonce = cmd[1]
    csi_data = cmd[2:]
    print(f"Client {client_id} requested prove with {len(csi_data)} CSI samples")

    if CONN_ONLY_MODE:
        print("!CONNECTION ONLY MODE!")
        print("Return signed nonce")

        signed_nonce = sign_nonce(nonce)
        return command_from_parts(["SUCC", signed_nonce])
    else:
        try:
            auth_result = authenticate_device(client_id, csi_data)

            if auth_result:
                print("Prove valid, return signed nonce")
                signed_nonce = sign_nonce(nonce)
                return command_from_parts(["SUCC", signed_nonce])
            else:
                print("Prove invalid, rejecting attempt")
                return command_from_parts(["ERR", "AUTH_FAILED"])
        except Exception as e:
            print("EXCEPTION while proving device:")
            print(e)

            return command_from_parts(["ERR", "INTERNAL"])


def command_test(client_id: str | None, cmd: list[str]) -> bytes:
    if client_id == None:
        print("Unauthorized test command!")
        return command_from_parts(["ERR", "NO_AUTH"])

    print(f"Test command from '{client_id}'.")
    return command_from_parts(["SUCC", "0"])



def handle_client(client: socket.socket | ssl.SSLSocket, remote_id: str | None):
    print("ID:", remote_id)
    buf = SingleCommandBuffer()

    while True:
        try:
            if not (rcv := client.recv(128)):
                print("Client disconnected.")
                break
            buf.update(rcv)
            if DUMP_INCOMING:
                with open("./dump", "ab") as f:
                    f.write(rcv)

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
                        client.send(command_from_parts(["ERR", "INV_CMD"]))
                    except Exception as e:
                        print("E INV CMD:", e)
                        pass
        except Exception as e:
            print("General EXCEPTION while handling client:")
            print(e)

            try:
                client.send(command_from_parts(["ERR", "INTERNAL"]))
            except:
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

            if remote_id == None and ALLOW_GUEST_NO_CERT:
                print("!GUESTS ALLOWED!")
                print("Set ID to default value")

                remote_id = "DEF"

            handle_client(wrapped_client, remote_id)
        except ssl.SSLError as e:
            print("SSL Error:")
            print(e)
        except Exception as e:
            print("General EXCEPTION accepting client:")
            print(e)
        finally:
            try:
                wrapped_client.shutdown(socket.SHUT_RDWR)
            except:
                pass
            client.close()


def main():
    start_server()


if __name__ == "__main__":
    main()
