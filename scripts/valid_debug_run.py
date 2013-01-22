#! /usr/bin/python -tt

import argparse
import patchwork
import valid
import sys
import yaml
import re


def na_exit(key, value):
    # to exit with a skip result containing the N/A statement
    test_result = {
        "result": "skipped",
        "comment": "not applicable for %s = %s" % (key, value)
    }
    sys.stdout.write(yaml.safe_dump(test_result))
    sys.exit(0)


argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--host', help='hostname', required=True)
argparser.add_argument('--user', help='e.g. root', default='root')
argparser.add_argument('--key', help='keyfile', required=True)
argparser.add_argument('--test', help='test name', required=True)
argparser.add_argument('--product', help='product name', default="RHEL")
argparser.add_argument('--version', help='version', default="6.0")
argparser.add_argument('--region', help='aws region', default="us-east-1")
argparser.add_argument('--ami', help='e.g. ami-12345678',
                       default="ami-12345678")
argparser.add_argument('--ec2name', help='ec2 instance type',
                       default="m1.small")
argparser.add_argument('--itype', help='access/hourly', default="hourly")
argparser.add_argument('--arch', help='i386/x86_64', default="i386")
argparser.add_argument('--memory', help='required memory', default=1000000)
argparser.add_argument('--virtualization', help='virtualization type',
                       default="paravirtualization")

args = argparser.parse_args()

params = {
    "product": args.product,
    "version": args.version,
    "region": args.region,
    "ami": args.ami,
    "arch": args.arch,
    "itype": args.itype,
    "ec2name": args.ec2name,
    "virtualization": args.virtualization,
    "memory": args.memory
}

con = patchwork.connection.Connection(
    {
        "public_hostname": args.host,
        "private_hostname": args.host
    },
    username=args.user,
    key_filename=args.key
)

m = "valid.testing_modules." + args.test
testcase = getattr(sys.modules[m], args.test)()
if hasattr(testcase, 'not_applicable'):
    for key in testcase.not_applicable.keys():
        r = re.compile(testcase.not_applicable[key])
        if r.match(params[key]):
            na_exit(key, params[key])

if hasattr(testcase, 'applicable'):
    for key in testcase.applicable.keys():
        r = re.compile(testcase.applicable[key])
        if not r.match(params[key]):
            na_exit(key, params[key])

test_result = testcase.test(con, params)
sys.stdout.write(yaml.safe_dump(test_result))
