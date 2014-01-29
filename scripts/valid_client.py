#! /usr/bin/python -tt

""" Client for Valid server """

import urllib
import httplib
import argparse
import sys

def main():
    """ Main """

    argparser = argparse.ArgumentParser(description='Run cloud image validation')
    argparser.add_argument('--add', help='add data file for validation')
    argparser.add_argument('--get',
                           default="", help='get transaction result')

    argparser.add_argument('--emails', help='report result to emails (comma-separated list, for --add only)')

    argparser.add_argument('--subject', help='email subject')

    argparser.add_argument('--cert',
                           default="/etc/valid/valid_client.crt", help='certificate file')
    argparser.add_argument('--key',
                           default="/etc/valid/valid_client.key", help='key file')

    argparser.add_argument('--host',
                           default="localhost", help='host to connect to')
    argparser.add_argument('--port',
                           default=8080, help='port to connect to')

    args = argparser.parse_args()

    http = httplib.HTTPSConnection(args.host, args.port, key_file=args.key, cert_file=args.cert)

    if args.add:
        if args.add != "-":
            with open(args.add, "r") as datafile:
                data = datafile.read()
        else:
            data = sys.stdin.read()
        data_dic = {"data": data}
        if args.emails:
            data_dic["emails"] = args.emails
        if args.subject:
            data_dic["subject"] = args.subject
        params = urllib.urlencode(data_dic)
        http.request("POST", "", params, {"Content-type": "text/yaml"})
    elif args.get:
        http.request("GET", "/result?transaction_id=" + args.get)
    else:
        sys.stderr.write("You should specify either '--get' or '--add' option!\n")
        sys.exit(1)

    response = http.getresponse()
    if response.status == 200:
        sys.stdout.write(response.read() + "\n")
    else:
        sys.stdout.write("Request failed: " + response.read() + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
