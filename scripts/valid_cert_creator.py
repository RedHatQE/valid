#! /usr/bin/python -tt

"""
Create SSL certs for Valid
"""

import random
import os
import sys
import string
import argparse
import yaml
import subprocess

def main():
    """ Main """

    argparser = argparse.ArgumentParser(description='Create certificates set for client/server usage')
    argparser.add_argument('--capassword', help='use specified ca password')
    argparser.add_argument('--config',
                           default="/etc/validation.yaml", help='use supplied yaml config file')
    argparser.add_argument('--force', action='store_const', const=True,
                           default=False, help='overwrite existing files')
    argparser.add_argument('--outputdir', help='create all certs in specified directory')
    argparser.add_argument('--servername', help='server hostname', required=True)

    args = argparser.parse_args()

    with open(args.config, 'r') as confd:
        yamlconfig = yaml.load(confd)

    if not args.outputdir:
        capwd = "/etc/pki/CA/private/valid_ca.pwd"
        casrl = "/etc/pki/CA/private/valid_ca.srl"
        cakey = "/etc/pki/CA/private/valid_ca.key"
        if "server_ssl_ca" in yamlconfig.keys():
            cacrt = yamlconfig["server_ssl_ca"]
        else:
            cacrt = "/etc/pki/CA/certs/valid_ca.crt"

        servercsr = "/etc/pki/tls/certs/valid_server.csr"
        if "server_ssl_key" in yamlconfig.keys():
            serverkey = yamlconfig["server_ssl_key"]
        else:
            serverkey = "/etc/pki/tls/private/valid_server.key"
        if "server_ssl_cert" in yamlconfig.keys():
            servercrt = yamlconfig["server_ssl_cert"]
        else:
            servercrt = "/etc/pki/tls/certs/valid_server.crt"

        clientcsr = "/etc/valid/valid_client.csr"
        clientcrt = "/etc/valid/valid_client.crt"
        clientkey = "/etc/valid/valid_client.key"

    else:
        outdir = args.outputdir
        capwd = outdir + "/valid_ca.pwd"
        casrl = outdir + "/valid_ca.srl"
        cacrt = outdir + "/valid_ca.crt"
        cakey = outdir + "/valid_ca.key"

        servercsr = outdir + "/valid_server.csr"
        servercrt = outdir + "/valid_server.crt"
        serverkey = outdir + "/valid_server.key"

        clientcsr = outdir + "/valid_client.csr"
        clientcrt = outdir + "/valid_client.crt"
        clientkey = outdir + "/valid_client.key"

    if not args.force:
        for fname in [capwd, cakey, cacrt, serverkey, servercrt, clientkey, clientcrt]:
            if os.path.exists(fname):
                sys.stderr.write(fname + " exists! Use --force key to overwrite it\n")
                sys.exit(1)

    if args.capassword:
        capassword = args.capassword
    else:
        capassword = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        sys.stdout.write("CA password: %s\n" % capassword)

    with open(capwd, "w") as capwdfd:
        capwdfd.write(capassword + "\n")
    with open(casrl, "w") as casrlfd:
        casrlfd.write("10\n")

    # pylint: disable=C0301
    subprocess.check_output(["openssl", "req", "-new", "-x509", "-extensions", "v3_ca", "-keyout", cakey, "-subj", "/C=CZ/L=Brno/CN=CA", "-out", cacrt, "-days", "365", "-passout", "pass:" + capassword])

    subprocess.check_output(["openssl", "genrsa", "-out", serverkey, "2048"])
    subprocess.check_output(["openssl", "req", "-new", "-key", serverkey, "-subj", "/C=CZ/L=Brno/CN=" + args.servername, "-out", servercsr])
    subprocess.check_output(["openssl", "x509", "-req", "-days", "365", "-CA", cacrt, "-CAkey", cakey, "-CAserial", casrl, "-passin", "pass:" + capassword, "-in", servercsr, "-out", servercrt])

    subprocess.check_output(["openssl", "genrsa", "-out", clientkey, "2048"])
    subprocess.check_output(["openssl", "req", "-new", "-key", clientkey, "-subj", "/C=CZ/L=Brno/CN=client", "-out", clientcsr])
    subprocess.check_output(["openssl", "x509", "-req", "-days", "365", "-CA", cacrt, "-CAkey", cakey, "-CAserial", casrl, "-passin", "pass:" + capassword, "-in", clientcsr, "-out", clientcrt])

if __name__ == "__main__":
    main()
