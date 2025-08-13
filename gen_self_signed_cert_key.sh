#!/bin/bash
# This script generates a self-signed SSL certificate and key for MyOral server testing purposes.
# It creates a key.pem and cert.pem in the current directory.   
# Make sure to run this script in the directory where you want the certificate files to be created.
# HOSTNAME is set to the current hostname of the machine.
# You can change it to a specific domain name if needed.
# Ensure you have openssl installed on your system to run this script. 
HOSTNAME=10.10.11.254 # for test via wifi BFHAP01_?G
HOSTNAME=183.179.200.58 # public IP

echo "[Generating self-signed SSL certificate and key]"
if [[ -f "key.pem" && -f "cert.pem" ]]; then
    echo "Certificate and key already exist. Skipping generation."
    exit 0
fi
# Generate a self-signed certificate and key
echo "Generating key.pem and cert.pem..."
if ! command -v openssl &> /dev/null; then
    echo "openssl is not installed. Please install it to generate the certificate."
    exit 1
fi
# Generate a 2048-bit RSA key and a self-signed certificate valid for 365 days  
openssl genrsa -out key.pem 2048
if [[ $? -ne 0 ]]; then
    echo "Failed to generate key.pem."
    exit 1
fi
echo "Key generated successfully: key.pem"
# Create a self-signed certificate using the generated key  
openssl req -x509 -new -nodes -key key.pem -sha256 -days 365 -out cert.pem -subj "/CN=$HOSTNAME"
if [[ $? -ne 0 ]]; then
    echo "Failed to generate cert.pem."
    exit 1
fi
echo "Certificate generated successfully: cert.pem"
echo "Self-signed SSL certificate and key have been generated successfully."
echo "You can now use key.pem and cert.pem for testing purposes."
echo "Remember that self-signed certificates are not trusted by browsers and should only be used for development and testing."
echo "For production use, consider obtaining a certificate from a trusted Certificate Authority (CA)."
exit 0
# End of script 