#! /usr/bin/python -tt

import argparse
import patchwork
import valid
import sys
import yaml

argparser = argparse.ArgumentParser(description='Run cloud image validation')
argparser.add_argument('--host', help='hostname', required=True)
argparser.add_argument('--key', help='keyfile', required=True)
argparser.add_argument('--test', help='test name', required=True)
argparser.add_argument('--product', help='product name', default="RHEL")
argparser.add_argument('--version', help='version', default="6.0")
argparser.add_argument('--hwpname', help='hwp name', default="m1.small")
argparser.add_argument('--hwpmemory', help='hwp memory', default=1000000)
argparser.add_argument('--hwpvirtualization', help='hwp virtualization', default="paravirtualization")

args = argparser.parse_args()

params = {"product": args.product, "version": args.version, "hwp": {"name": args.hwpname, "virtualization": args.hwpvirtualization, "memory": args.hwpmemory}}

con = patchwork.connection.Connection({"public_hostname": args.host, "private_hostname": args.host}, key_filename=args.key)

m = "valid.testing_modules." + args.test
testcase = getattr(sys.modules[m], args.test)()
test_result = testcase.test(con, params)
sys.stdout.write(yaml.safe_dump(test_result))
