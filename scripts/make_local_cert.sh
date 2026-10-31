#!/usr/bin/env bash
# Self-signed cert for the LOCAL mock only (valid for localhost / 127.0.0.1). Never use for anything real.
set -e; mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -keyout certs/localhost.key -out certs/localhost.pem \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
echo "wrote certs/localhost.pem and certs/localhost.key"
