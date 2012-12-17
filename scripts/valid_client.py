import urllib
import urllib2
import argparse

argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--data', help='data file for validation', required=True)
argparser.add_argument('--debug', action='store_const', const=True,
                       default=False, help='debug mode')
argparser.add_argument('--url', action='store_const', const=True,
                       default="http://localhost:8080", help='run HTTP server')

args = argparser.parse_args()

fd = open(args.data, "r")
data = fd.read()
fd.close()

params = urllib.urlencode({"data": data})
post_req = urllib2.Request(args.url)
post_req.add_data(params)

response = urllib2.urlopen(post_req)
response_data = response.read()
response.close()
print response_data
