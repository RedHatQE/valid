import random
import os
import string
import argparse

argparser = argparse.ArgumentParser(description='Create certificates set for client/server usage')
argparser.add_argument('--capassword', help='use specified ca password')
argparser.add_argument('--outputdir', help='output directory', default=".")
argparser.add_argument('--servername', help='server hostname', required=True)

args = argparser.parse_args()
outdir = args.outputdir + "/"

if args.capassword:
    capassword = args.capassword
else:
    capassword = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
    sys.stdout.write("CA password: %s\n" % capassword)

os.system("echo " + capassword + " > ca.pwd")
os.system("echo 10 > " + outdir + "ca.srl")
os.system("openssl req  -new -x509 -extensions v3_ca -keyout " + outdir + "ca.key -subj \"/C=CZ/L=Brno/CN=localhost CA\" -out " + outdir + "ca.crt -days 365 -passout \"pass:" + capassword + "\"")
os.system("openssl genrsa -out " + outdir + "server.key 2048")
os.system("openssl req -new -key " + outdir + "server.key -subj \"/C=CZ/L=Brno/CN=" + args.servername + "\" -out " + outdir + "server.csr")
os.system("openssl x509 -req -days 365 -CA " + outdir + "ca.crt -CAkey " + outdir + "ca.key -passin \"pass:" + capassword + "\" -in " + outdir + "server.csr -out " + outdir + "server.crt")
os.system("openssl genrsa -out " + outdir + "client.key 2048")
os.system("openssl req -new -key " + outdir + "client.key -subj \"/C=CZ/L=Brno/CN=client\" -out " + outdir + "client.csr")
os.system("openssl x509 -req -days 365 -CA " + outdir + "ca.crt -CAkey " + outdir + "ca.key -passin \"pass:" + capassword + "\" -in " + outdir + "client.csr -out " + outdir + "client.crt")
