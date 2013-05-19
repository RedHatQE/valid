#! /usr/bin/python -tt

import yaml
import argparse
import re


argparser = argparse.ArgumentParser(
    description='Gather some numbers out of a validation result'
)

argparser.add_argument(
    'data',
    help='yaml file with validation result',
    type=argparse.FileType('r')
)

argparser.add_argument(
    '-m', '--match-console',
    help='Regexp to compile with re.DOTALL | re.IGNORECASE to match the console',
)


args = argparser.parse_args()

# parse data
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
data = load(args.data, Loader=Loader)



# will count the failures by region and itype
failure_messages = ('fail', 'failure', 'failed')
counted_actual_results = ('', None, 'None')
by_region = {}
by_itype = {}
by_command = {}
by_stage = {}
total = 0

empty_consoles = []
console_errors = {}


# count the data
for ami in data:
    if type(ami) is not dict:
        continue
    ami_result = ami['result']
    region = ami['region']
    # results
    for itype in ami['result'].keys():
        itype_result = ami_result[itype]
        for stage in sorted(itype_result.keys()):
            test_result = itype_result[stage]
            if itype_result[stage] in failure_messages:
                if stage not in by_stage:
                    by_stage[stage] = {}
                if not ami['ami'] in by_stage[stage]:
                    by_stage[stage][ami['ami']] = 0
                by_stage[stage][ami['ami']] += 1
            for command in test_result:
                if type(command) is not dict or \
                    'command' not in command or \
                    'result' not in command:
                    continue
                total += 1
                command_line = command['command']
                result = command['result']
                if 'actual' in command:
                    actual = command['actual']
                else:
                    actual = "__NOT_IN_COUNTED_ACUTAL_RESULTS__"

                # check result to decide whether to count or not
                if result not in failure_messages and actual not in counted_actual_results:
                    continue

                # region
                # init counters if no previous records
                if region not in by_region:
                    by_region[region] = {}
                if command_line not in by_region[region]:
                    by_region[region][command_line] = 0
                # increase the number of failures
                by_region[region][command_line] += 1

                # itype
                if itype not in by_itype:
                    by_itype[itype] = {}
                if command_line not in by_itype[itype]:
                    by_itype[itype][command_line] = 0
                by_itype[itype][command_line] += 1

                # command
                if command_line not in by_command:
                    by_command[command_line] = 0
                by_command[command_line] += 1
    # console
    if args.match_console:
        errors = re.compile(args.match_console, re.IGNORECASE | re.DOTALL)
        for itype_console in ami['console_output'].keys():
            if not ami['console_output']:
                empty_consoles.append(ami['ami'])
            if errors.match(ami['console_output'][itype_console]):
                if ami['ami'] not in console_errors:
                    console_errors[ami['ami']] = 0
                console_errors[ami['ami']] += 1

        


# dump the stats
stats = {
    'by_command': by_command,
    'by_region': by_region,
    'by_itype': by_itype,
    'by_stage': by_stage,
    'total': total,
    'console errors': console_errors,
    'empty consoles': empty_consoles
}

print dump(stats, default_flow_style=False, Dumper=Dumper)
