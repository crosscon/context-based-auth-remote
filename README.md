# Context-based Authentication (CBA): Remote Server

**DISCLAIMER:** This code base is still very much work in progress! Actual verification using the Machine Learning model isn't possible yet, and the server returns a signed nonce (resembling a positive response) by default.

This is the remote side for the CBA TA. A `Dockerfile` is provided for easy deployment and configuration

## Build

Building the Docker image is as easy as executing `docker build -t <name>:<tag> .` (with an adequate name & tag).


## Configuration

For running the image, using a `docker-compose.yml` is advised. An example is provided.

This container requires two certificates (with private key) and a binary file to run. The path is flexible and must be specified using an environment variable:

- `CA_CERT_PATH`: path to the certificate used for signing the mTLS client certificates
- `CA_KEY_PATH` path to the key used for signing the mTLS client certs
- `SSL_CERT_PATH`: path to the TLS certificate used for the server
- `SSL_KEY_PATH`: path to the key for the TLS server certificate
- `SIGN_KEY_PATH`: path to the key for signing nonces upon successful authentication
- `SIGN_CERT_PATH`: path to the certificate used to verify the signature of the nonces

How the volumes are mounted can be arbitrary as long as the environment variables are adjusted. You are advised to load them from a `.env` file.

The required certificates and keys can be created using the provided `create_keys.py` script. Alternatively, OpenSSL can be used.

Sample keys **for testing purposes only** are provided in the `keys` directory.


## Using together with the CBA Demo Application

The demo application has a test function to verify if a provided signature was signed using the configured certificate. For this, the nonce `0` is used. The script `demo_signature.py` produces an output that can be copied directly to the C file.

