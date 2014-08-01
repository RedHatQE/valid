#! /usr/bin/python -tt
"""
Report testing results to Bugzilla
"""

import argparse
import yaml
import bugzilla
import tempfile
import sys
import time
from valid import valid_result


class Summary(object):
    """ Testing summary """

    # pylint: disable=W0102
    def __init__(self, contents=[], yaml_summary=False):
        self.contents = contents
        self.yaml_summary = yaml_summary

    def add(self, ami, status=None, bug=None):
        """ Add info """
        print "# %s: %s" % (ami, bug)
        self.contents.append({'id': str(ami), 'bug': str(bug), 'status': str(status)})

    def __str__(self):
        ret = "## total: %d records\n" % len(self.contents)
        if self.yaml_summary:
            try:
                from yaml import CDumper as Dumper
            except ImportError:
                from yaml import Dumper
            ret += yaml.dump(self.contents, Dumper=Dumper)
        return ret

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
    argparser.add_argument('-y', '--yaml-summary', help='provide info in yaml',
                           action='store_const', default=False, const=True)
    argparser.add_argument('-a', '--all-commands', help='show all commands in bugzillas not just failed',
                           action='store_true')

    args = argparser.parse_args()

    resultd = open(args.result, 'r')
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    result = yaml.load(resultd, Loader=Loader)
    resultd.close()

    summary = Summary(yaml_summary=args.yaml_summary)

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
        overall_result, bug_summary, info, bug_description = valid_result.get_overall_result(ami, verbose=args.all_commands)
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
            bug = None
            for ntry in xrange(10):
                try:
                    bug = bzid.getbug(bugid)
                    break
                except:
                    # bug not found, retry
                    time.sleep(10)
            if bug:
                bugnr = bug.id
                for comment in bug_description:
                    bug.addcomment(comment)
                bug.setstatus("VERIFIED" if overall_result == "succeeded" else "ON_QA")
        else:
            print info
            print '\n'.join(bug_description)

        summary.add(ami['ami'], bug=bugnr, status='pass' if overall_result == "succeeded" else 'fail')
        ami_fd.close()
    print summary

if __name__ == "__main__":
    main()
