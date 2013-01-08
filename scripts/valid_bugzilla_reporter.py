#! /usr/bin/python -tt

import logging
import argparse
import yaml
import bugzilla
import tempfile
import sys


class Output(object):
    def __init__(self, contents = [], verbose=False):
        self.contents = contents
        self.verbose = verbose
    def add(self, ami, bug, status):
        self.contents.append({'ami': ami, 'bug': bug, 'status': status})
    def __str__(self):
        if self.verbose:
            return yaml.dump(self.contents)
        return "\n".join(map(lambda x: "%(ami)s: #%(bug)s" % x, self.contents))


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

output = Output(verbose=args.verbose)

bugzilla_user = yamlconfig["bugzilla"]["user"]
bugzilla_password = yamlconfig["bugzilla"]["password"]
bzid = bugzilla.RHBugzilla(url=args.bugzilla_url, user=bugzilla_user, password=bugzilla_password)
if not bzid:
    print "Failed to connect to bugzilla!"
    sys.exit(1)

for ami in result:
    arch = ami["arch"]
    product = ami["product"]
    region = ami["region"]
    version = ami["version"]
    ami_result = ami["result"]
    overall_result = "succeeded"
    bug_summary = ami["ami"] + " " + product + " " + version + " " + arch + " " + region
    bug_description = ""

    ami_fd = tempfile.NamedTemporaryFile()
    ami_fd.write(yaml.safe_dump(ami))
    ami_fd.seek(0)

    for itype in ami_result.keys():
        bug_description += itype + "\n"
        itype_result = ami_result[itype]
        if type(itype_result) == dict:
            for stage in itype_result.keys():
                bug_description += stage + ":\n"
                stage_result = itype_result[stage]
                if type(stage_result) == dict:
                    for test in sorted(stage_result.keys()):
                        test_result = stage_result[test]
                        if type(test_result) == list:
                            is_failed = "succeeded"
                            for command in test_result:
                                if command["result"] in ["fail", "failed", "failure"]:
                                    is_failed = "failed"
                                    if overall_result == "succeeded":
                                        overall_result = "failed"
                                if command["result"] in ["skip", "skipped"]:
                                    is_failed = "skipped"
                            bug_description += "test %s %s\n" % (test, is_failed)
                            if is_failed != "succeeded":
                                for command in test_result:
                                    bug_description += "--->\n"
                                    for key in sorted(command.keys()):
                                        bug_description += "\t%s: %s\n" % (key, command[key])
                                    bug_description += "<---\n"
                else:
                    bug_description += "stage testing failed!\n"
                    overall_result = "failure"
        else:
            bug_description += "instance testing failed!\n"
            overall_result = "failure"
    bug_description = "Validation " + overall_result + " for " + ami["ami"] + " in " + region + " product: " + product + ", version: " + version + ", arch: " + arch + "\n\n" + bug_description

    if args.test:
        print bug_description
    else:
        BZ_Object = bzid.createbug(product=args.bugzilla_product, component=args.bugzilla_component, version="RHEL" + version, rep_platform=arch, summary=bug_summary, op_sys="Linux")
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
                output.add(ami['ami'], bug.id, 'ON_QA')
            else:
                bug.setstatus("VERIFIED")
                output.add(ami['ami'], bug.id, 'VERIFIED')
    ami_fd.close()
    print output
