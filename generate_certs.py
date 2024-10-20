from portal.settings import DEBUG

from pathlib import Path
from OpenSSL import crypto, SSL
import os


# To be used for development purposes only
def generate_self_signed_certificate():
    if DEBUG:
        CURRENT_DIR = Path(__file__).resolve().parent
        certificate_directory = CURRENT_DIR / "certs"
        certificate_file = "cert.pem"
        key_file = "key.pem"
        
        if not os.path.exists(certificate_directory):
            os.makedirs(certificate_directory)
        
        certificate_path = os.path.join(certificate_directory, certificate_file)
        key_path = os.path.join(certificate_directory, key_file)

        if not os.path.exists(certificate_path) or not os.path.exists(key_path):
            # Create a key pair
            key_pair = crypto.PKey()
            key_pair.generate_key(crypto.TYPE_RSA, 4096)
            
            # Create self-signed certificate
            certificate = crypto.X509()
            certificate.get_subject().C = "US"
            
            certificate.get_subject().ST = "State"
            certificate.get_subject().L = "Locality"
            certificate.get_subject().O = "Organization"
            certificate.get_subject().OU = "Organization Unit"
            certificate.get_subject().CN = "localhost"
            certificate.set_serial_number(1000)
            certificate.gmtime_adj_notBefore(0)
            certificate.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
            certificate.set_issuer(certificate.get_subject())
            certificate.set_pubkey(key_pair)
            certificate.sign(key_pair, "sha256")

            with open(certificate_path, "wb") as certificate_file:
                certificate_file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, certificate))

            with open(key_path, "wb") as key_file:
                key_file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key_pair))
                
            
generate_self_signed_certificate()