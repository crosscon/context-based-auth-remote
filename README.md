# Context-based Authentication (CBA): Remote Server

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
- `CSI_DATABASE_PATH`: path to where the CSI enrollment data is stored (e.g. `/db`)
- `ML_MODEL_SAMPLES_PER_RECORDING`: number of samples the machine learning model uses for authentication (currently 64)
- `ML_MODEL_CHECKPOINT_PATH`: path to the checkpoint data of the trained machine learning model (must be mounted as a Docker volume); `e2e.pt` is provided in this repo
- `ACCEPTANCE_THRESHOLD`: threshold for number of device to match between current environment and enrollment (e.g. 5 devices in enrollment, 3 matches found in current environment --> 0.6); float between 0 and 1

How the volumes are mounted can be arbitrary as long as the environment variables are adjusted. You are advised to load them from a `.env` file.

The required certificates and keys can be created using the provided `create_keys.py` script. Alternatively, OpenSSL can be used.

Sample keys **for testing purposes only** are provided in the `keys` directory.


## Testing

For testing, it's advised to use the `development` branch as it always returns a successful authentication attempt and, thus, is more predictable than the ML version.


## Using together with the CBA Demo Application

The demo application has a test function to verify if a provided signature was signed using the configured certificate. For this, the nonce `0` is used. The script `demo_signature.py` produces an output that can be copied directly to the C file.

