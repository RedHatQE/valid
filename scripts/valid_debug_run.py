#! /usr/bin/python -tt
"""
Debug particular test
"""

import argparse
import patchwork
import sys
import yaml
import re


RUNTIME_ERR = 2


class LoadError(Exception):
    """ LoadError expection """
    pass


class ParamsError(Exception):
    """ ParamsError expection """
    pass


def load_yaml(filename=None, index=0):
    """ Load a yaml file in the format of a list of records """
    data = None
    record = {}
    if filename is not None:
        try:
            data = yaml.load(filename)
        except Exception as err:
            raise LoadError("Error loading file %s: %s" % (filename, err))

    if data is not None:
        if type(data) is not list:
            raise LoadError("can't read data; data not a list of records")
        record = data[index]
        if type(record) is not dict:
            raise ParamsError("can't read data; record not a dict")
    return record


def get_params(args):
    """
    Merge cmdline parameters with data & hwp parameters cmdline overrides
    """

    params = {}

    if args.data_file is not None:
        params.update(load_yaml(args.data_file, args.data_index).items())
        args.data_file.close()

    if args.hwp_file is not None:
        params.update(load_yaml(args.hwp_file, args.hwp_index).items())
        args.hwp_file.close()

    for param_name in [
        'product',
        'version',
        'region',
        'ami',
        'arch',
        'itype',
        'ec2name',
        'virtualization',
        'memory'
    ]:
        param = getattr(args, param_name)
        if param is not None:
            params[param_name] = param

    return params

def main():
    """ Main """

    argparser = argparse.ArgumentParser(description='Run cloud image validation')

    argparser.add_argument('host', help='hostname')
    argparser.add_argument('key', help='keyfile')
    argparser.add_argument('test', help='test name')

    argparser.add_argument('--user', help='e.g. root', default='root')

    argparser.add_argument('--product', help='product name')
    argparser.add_argument('--version', help='version')
    argparser.add_argument('--region', help='aws region')
    argparser.add_argument('--ami', help='e.g. ami-12345678')
    argparser.add_argument('--ec2name', help='ec2 instance type')
    argparser.add_argument('--itype', help='access/hourly')
    argparser.add_argument('--arch', help='i386/x86_64')
    argparser.add_argument('--memory', help='required memory')
    argparser.add_argument('--virtualization', help='virtualization type')
    argparser.add_argument('--test-file', help="python file to load test from")

    data_parser = argparser.add_argument_group(
        'data',
        description='''
            Load data-params from a yaml file.
            The format is list of records(dictionaries).
            Items expected are the same as for valid_runner.py.
            If no list index is given, first record is used by default.
        '''
    )
    data_parser.add_argument(
        '--data-file',
        help='data YAML file',
        type=argparse.FileType('r')
    )
    data_parser.add_argument(
        '--data-index',
        help='index into the YAML file',
        type=int,
        default=0
    )

    hwp_parser = argparser.add_argument_group(
        'hwp',
        description='''
            Load hwp-params from a yaml file.
            The format is list of records(dictionaries).
            Items expected are the same as for valid_runner.py.
            If no list index is given, first record is used by default.
        '''
    )
    hwp_parser.add_argument(
        '--hwp-file',
        help='hwp YAML file',
        type=argparse.FileType('r')
    )
    hwp_parser.add_argument(
        '--hwp-index',
        help='index into the YAML file',
        type=int,
        default=0
    )

    args = argparser.parse_args()


    params = get_params(args)
    print "# using params:"
    print "#  host: %s" % args.host
    print "#  key:  %s" % args.key
    print "#  user: %s" % args.user

    mod = "valid.testing_modules." + args.test
    if args.test_file is not None:
        # try loading a module from a path
        import imp
        test_module = imp.load_source(
            'valid.testing_modules.test',
            args.test_file
        )
    elif args.test in sys.modules:
        test_module = sys.modules[args.test]
    elif mod in sys.modules:
        test_module = sys.modules[mod]
    else:
        print >> sys.stderr, "Can't locate test: %s" % args.test
        exit(RUNTIME_ERR)

    print "#  test: %s: %s" % (test_module, args.test)
    testcase = getattr(test_module, args.test)()

    if hasattr(testcase, 'not_applicable'):
        na_flag = True
        for key in testcase.not_applicable.keys():
            rexp = re.compile(testcase.not_applicable[key])
            if key in params and rexp.match(str(params[key])) is None:
                #na_exit(key, params[key])
                na_flag = False
        if na_flag:
            test_result = {
                "result": "skipped",
                "comment": "'not applicable' matched"
            }
            sys.stdout.write(yaml.safe_dump(test_result))
            sys.exit(0)

    if hasattr(testcase, 'applicable'):
        for key in testcase.applicable.keys():
            rexp = re.compile(testcase.applicable[key])
            if key in params and not rexp.match(str(params[key])):
                # to exit with a skip result containing the N/A statement
                test_result = {
                    "result": "skipped",
                    "comment": "'applicable' doesn't match for %s = %s" % (key, params[key])
                }
                sys.stdout.write(yaml.safe_dump(test_result))
                sys.exit(0)

    try:
        con = patchwork.connection.Connection(
            {
                "public_hostname": args.host,
                "private_hostname": args.host
            },
            username=args.user,
            key_filename=args.key
        )
    except Exception as err:
        print >> sys.stderr, "Error opening connection: %s" % err
        exit(RUNTIME_ERR)


    test_result = testcase.test(con, params)

    sys.stdout.write(yaml.safe_dump([params, {args.test: test_result}]))

if __name__ == "__main__":
    main()
