#! /usr/bin/python -tt

import logging
import argparse
import yaml
import bugzilla
import tempfile
import sys
from valid import valid_result


class Summary(object):
    def __init__(self, contents=[], verbose=False):
        self.contents = contents
        self.verbose = verbose

    def add(self, ami, status=None, bug=None):
        print "# %s: %s" % (ami, bug)
        self.contents.append({'id': str(ami), 'bug': str(bug), 'status': str(status)})

    def __str__(self):
        return "## total: %d records\n" % len(self.contents) + (self.verbose and
                                                                yaml.dump(self.contents) or "")


argparser = argparse.ArgumentParser(description='Report validation result to bugzilla')
argparser.add_argument('--bugzilla-component',
                       default="images", help='use specified bugzilla component')
argparser.add_argument('--bugzilla-product',
                       default="Cloud Image Validation", help='use specified bugzilla product')
argparser.add_argument('--bugzilla-url',
                       default="https://bugzilla.redhat.com/xmlrpc.cgi", help='use specified bugzilla xmlrpc url')
argparser.add_argument('--config',
                       default="/etc/validation.yaml", help='use supplied yaml config file')
argparser.add_argument('--debug', action='store_const', const=True,
                       default=False, help='debug mode')
argparser.add_argument('--result', help='yaml file with validation result', required=True)
argparser.add_argument('--test', action='store_const', const=True,
                       default=False, help='report to stdout instead of bugzilla')
argparser.add_argument('-v', '--verbose', help='provide info in yaml',
                       action='store_const', default=False, const=True)

args = argparser.parse_args()

confd = open(args.config, 'r')
yamlconfig = yaml.load(confd)
confd.close()

resultd = open(args.result, 'r')
result = yaml.load(resultd)
resultd.close()

summary = Summary(verbose=args.verbose)

bugzilla_user = yamlconfig["bugzilla"]["user"]
bugzilla_password = yamlconfig["bugzilla"]["password"]
bzid = bugzilla.RHBugzilla(url=args.bugzilla_url, user=bugzilla_user, password=bugzilla_password)
if not bzid:
    print "Failed to connect to bugzilla!"
    sys.exit(1)

for ami in result:
    ami_fd = tempfile.NamedTemporaryFile()
    ami_fd.write(yaml.safe_dump(ami))
    ami_fd.seek(0)
    overall_result, bug_summary, bug_description = valid_result.get_overall_result(ami)

    if args.test:
        summary.add(ami['ami'], status='fail')
        print bug_description
    else:
        BZ_Object = bzid.createbug(product=args.bugzilla_product, component=args.bugzilla_component, version="RHEL" + ami["version"], rep_platform=ami["arch"], summary=bug_summary, op_sys="Linux")
        if not BZ_Object:
            print "Failed to create bug in bugzilla!"
            sys.exit(1)

        bugid = str(BZ_Object.bug_id)
        attach_name = ami["ami"] + ".yaml"
        res = bzid.attachfile(bugid, ami_fd, attach_name, filename=attach_name, contenttype="text/yaml", ispatch=False)
        bug = bzid.getbug(bugid)
        if bug:
            bug.addcomment(bug_description)
            if overall_result != "succeeded":
                bug.setstatus("ON_QA")
                ami_result = 'fail'
                summary.add(ami['ami'], bug=bug.id, status='fail')
            else:
                bug.setstatus("VERIFIED")
                summary.add(ami['ami'], bug=bug.id, status='pass')
    ami_fd.close()
print summary
