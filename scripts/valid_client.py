import urllib
import urllib2
import argparse
import sys

argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--add', help='add data file for validation')
argparser.add_argument('--debug', action='store_const', const=True,
                       default=False, help='debug mode')
argparser.add_argument('--get',
                       default="", help='get transaction result')
argparser.add_argument('--url',
                       default="http://localhost:8080", help='run HTTP server')

args = argparser.parse_args()

if args.add:
    fd = open(args.add, "r")
    data = fd.read()
    fd.close()

    params = urllib.urlencode({"data": data})
    post_req = urllib2.Request(args.url)
    post_req.add_data(params)

    response = urllib2.urlopen(post_req)
    response_data = response.read()
    response.close()
    sys.stdout.write(response_data)
elif args.get:
    get_req = urllib2.Request(args.url)
    response = urllib2.urlopen(args.url + "/result?transaction_id=" + args.get)
    response_data = response.read()
    response.close()
    sys.stdout.write(response_data)
else:
    sys.stderr.write("You should specify either '--get' or '--add' option!\n")
    sys.exit(1)

