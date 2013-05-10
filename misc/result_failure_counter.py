#! /usr/bin/python -tt

import yaml
import argparse


argparser = argparse.ArgumentParser(
    description='Gather some numbers out of a validation result'
)

argparser.add_argument(
    'data',
    help='yaml file with validation result',
    type=argparse.FileType('r')
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


# count the data
for ami in data:
    if type(ami) is not dict:
        continue
    ami_result = ami['result']
    region = ami['region']
    for itype in ami['result'].keys():
        itype_result = ami_result[itype]
        if type(itype_result) is not dict:
            continue
        for stage in sorted(itype_result.keys()):
            test_result = itype_result[stage]
            if itype_result[stage] in failure_messages:
                if stage not in by_stage:
                    by_stage[stage] = []
                by_stage[stage].append(ami['ami'])
                continue
            for command in test_result:
                if type(command) is not dict:
                    continue
                total += 1
                if 'actual' not in command:
                    continue
                if command['actual'] in counted_actual_results:
                    command_line = command['command']

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


# dump the stats
stats = {
    'by_command': by_command,
    'by_region': by_region,
    'by_itype': by_itype,
    'by_stage': by_stage,
    'total': total
}

print dump(stats, default_flow_style=False, Dumper=Dumper)
