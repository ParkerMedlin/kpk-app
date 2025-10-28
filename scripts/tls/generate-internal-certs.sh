#!/usr/bin/env bash
set -euo pipefail

# Generates/renews the internal Kinpak HTTPS certificates.
# - Creates (or reuses) an internal root CA under nginx/ssl
# - Issues a server certificate for kpkapp.lan and subdomains
#
# Usage:
#   scripts/tls/generate-internal-certs.sh
#
# Optional environment overrides:
#   CA_SUBJECT="/C=US/ST=AL/L=Mobile/O=Kinpak/OU=IT/CN=Kinpak Internal Root CA"
#   SERVER_HOSTS="kpkapp.lan,*.kpkapp.lan,jrd.kpkapp.lan,rpm.kpkapp.lan"
#   SERVER_IPS="192.168.178.168,192.168.178.169"
#   SERVER_VALID_DAYS=825

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SSL_DIR="${ROOT_DIR}/nginx/ssl"

mkdir -p "${SSL_DIR}"

CA_KEY="${SSL_DIR}/kpkapp-rootCA.key"
CA_CERT="${SSL_DIR}/kpkapp-rootCA.crt"
CA_SUBJECT="${CA_SUBJECT:-/C=US/ST=Alabama/L=Mobile/O=Kinpak Inc/OU=IT/CN=Kinpak Internal Root CA}"
CA_VALID_DAYS="${CA_VALID_DAYS:-3650}"

SERVER_KEY="${SSL_DIR}/kpkapp.lan.key"
SERVER_CSR="${SSL_DIR}/kpkapp.lan.csr"
SERVER_CERT="${SSL_DIR}/kpkapp.lan.crt"
SERVER_CHAIN="${SSL_DIR}/kpkapp.lan-chain.crt"
SERVER_PEM="${SSL_DIR}/kpkapp.lan.pem"
SERVER_SUBJECT="${SERVER_SUBJECT:-/C=US/ST=Alabama/L=Mobile/O=Kinpak Inc/OU=Applications/CN=kpkapp.lan}"
SERVER_VALID_DAYS="${SERVER_VALID_DAYS:-825}"

CONFIG_FILE="${SSL_DIR}/kpkapp.lan.cnf"

SERVER_HOSTS="${SERVER_HOSTS:-kpkapp.lan,*.kpkapp.lan,jrd.kpkapp.lan,rpm.kpkapp.lan}"
SERVER_IPS="${SERVER_IPS:-192.168.178.168,192.168.178.169}"

generate_config() {
    local dns_index=1
    local ip_index=1

cat > "${CONFIG_FILE}" <<'EOF'
[ req ]
default_bits = 2048
default_md = sha256
prompt = no
encrypt_key = no
distinguished_name = req_distinguished_name
req_extensions = v3_req

[ req_distinguished_name ]
C = US
ST = Alabama
L = Mobile
O = Kinpak Inc
OU = Applications
CN = kpkapp.lan

[ v3_req ]
subjectAltName = @alt_names

[ alt_names ]
EOF

    IFS=',' read -ra hosts <<< "${SERVER_HOSTS}"
    for host in "${hosts[@]}"; do
        host_trimmed="$(echo "${host}" | xargs)"
        echo "DNS.${dns_index} = ${host_trimmed}" >> "${CONFIG_FILE}"
        dns_index=$((dns_index + 1))
    done

    IFS=',' read -ra ips <<< "${SERVER_IPS}"
    for ip in "${ips[@]}"; do
        ip_trimmed="$(echo "${ip}" | xargs)"
        echo "IP.${ip_index} = ${ip_trimmed}" >> "${CONFIG_FILE}"
        ip_index=$((ip_index + 1))
    done
}

echo ">>> Using SSL directory: ${SSL_DIR}"

if [[ ! -f "${CA_KEY}" ]]; then
    echo ">>> Generating new root CA key..."
    openssl genrsa -out "${CA_KEY}" 4096
    chmod 600 "${CA_KEY}"
fi

if [[ ! -f "${CA_CERT}" ]]; then
    echo ">>> Generating new root CA certificate..."
    openssl req \
        -x509 \
        -new \
        -key "${CA_KEY}" \
        -sha256 \
        -days "${CA_VALID_DAYS}" \
        -out "${CA_CERT}" \
        -subj "${CA_SUBJECT}"
fi

echo ">>> Preparing server certificate request..."
generate_config

openssl genrsa -out "${SERVER_KEY}" 2048
chmod 600 "${SERVER_KEY}"

openssl req \
    -new \
    -key "${SERVER_KEY}" \
    -out "${SERVER_CSR}" \
    -subj "${SERVER_SUBJECT}" \
    -config "${CONFIG_FILE}"

echo ">>> Signing server certificate with internal CA..."
openssl x509 \
    -req \
    -in "${SERVER_CSR}" \
    -CA "${CA_CERT}" \
    -CAkey "${CA_KEY}" \
    -CAcreateserial \
    -out "${SERVER_CERT}" \
    -days "${SERVER_VALID_DAYS}" \
    -sha256 \
    -extensions v3_req \
    -extfile "${CONFIG_FILE}"

cat "${SERVER_CERT}" "${CA_CERT}" > "${SERVER_CHAIN}"
cat "${SERVER_KEY}" "${SERVER_CERT}" "${CA_CERT}" > "${SERVER_PEM}"

echo ">>> Done"
echo "-> Root CA : ${CA_CERT}"
echo "-> Server  : ${SERVER_CERT}"
echo "-> Chain   : ${SERVER_CHAIN}"
echo "-> PEM     : ${SERVER_PEM}"
echo
echo "Distribute ${CA_CERT} to client trust stores, then rebuild the nginx image."
