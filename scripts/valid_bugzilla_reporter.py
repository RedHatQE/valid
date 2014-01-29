#! /usr/bin/python -tt
"""
Report testing results to Bugzilla
"""

import argparse
import yaml
import bugzilla
import tempfile
import sys
from valid import valid_result


class Summary(object):
    """ Testing summary """

    # pylint: disable=W0102
    def __init__(self, contents=[], verbose=False):
        self.contents = contents
        self.verbose = verbose

    def add(self, ami, status=None, bug=None):
        """ Add info """
        print "# %s: %s" % (ami, bug)
        self.contents.append({'id': str(ami), 'bug': str(bug), 'status': str(status)})

    def __str__(self):
        return "## total: %d records\n" % len(self.contents) + (self.verbose and yaml.dump(self.contents) or "")

def main():
    """ Main """

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

    resultd = open(args.result, 'r')
    result = yaml.load(resultd)
    resultd.close()

    summary = Summary(verbose=args.verbose)

    if not args.test:
        confd = open(args.config, 'r')
        yamlconfig = yaml.load(confd)
        confd.close()

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
        bugnr = None

        if not args.test:
            bzobject = bzid.createbug(product=args.bugzilla_product,
                                       component=args.bugzilla_component,
                                       version="RHEL" + ami["version"],
                                       rep_platform=ami["arch"],
                                       summary=bug_summary,
                                       op_sys="Linux",
                                       keywords=["TestOnly"])
            if not bzobject:
                print "Failed to create bug in bugzilla!"
                sys.exit(1)

            bugid = str(bzobject.bug_id)
            attach_name = ami["ami"] + ".yaml"
            bzid.attachfile(bugid, ami_fd, attach_name, filename=attach_name, contenttype="text/yaml", ispatch=False)
            # FIXME: check previous call result
            bug = bzid.getbug(bugid)
            if bug:
                bugnr = bug.id
                bug.addcomment(bug_description)
                bug.setstatus("VERIFIED" if overall_result == "succeeded" else "ON_QA")
        else:
            print bug_description

        summary.add(ami['ami'], bug=bugnr, status='pass' if overall_result == "succeeded" else 'fail')
        ami_fd.close()
    print summary

if __name__ == "__main__":
    main()
