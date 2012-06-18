#!/bin/bash
# set -x

function filter() {
	local PASS_FILTER=$1
	local BLOCK_FILTER=$2
	# a filtering pipe
	grep "${PASS_FILTER:-.*}" | grep -v -e "${BLOCK_FILTER:----___---}"
}

function csv_translate () {
	# translates relengo csv to valid csv
	awk -F, '{printf "%s,%s,%s,%s,%s,%s\n", $2,$3,$4,$7,$5,$8}'
}

function random_sleep() {
	# sleep for an random amount of up to $1 seconds
	# default: up to 300 seconds
	local amount=$RANDOM
	let "amount %= ${1:-300}"
	echo sleeping for $amount seconds
	sleep $amount
}

function valid_file () {
	# wrap all pos params into a single-lined valid csv file
	cat << __VALID_FILE
arch,region,type,bug,version,ami
$@
__VALID_FILE
}


function releng_candidates() {
	# relengo wrapper
	# ~/src/utility-scripts/relengo/relengo-tool.py candidate list -c
	cat -
}

function validate() {
	# another wrapper
	local work_dir=$1/src
	local ami=$2
	pushd $work_dir  || exit $?
	rm -f test1.csv || exit $?
	valid_file $ami > test1.csv || exit $?
	echo "VALIDATING: $line"
	./getAmiDetails_withCSV.py --skip-tests="IPv6" > v.log 2> v.log.err || {
		echo "VALIDATING failed: $ami; see: $work_dir/v.log $work_dir/v.log.err" >&2 ;
		return 1 ;
	}
	popd
}

# main
#
pass_amis=$1
# by default, don't test passed images
if [ -z "$pass_amis" ] ; then
	# security break
	cat - << __MESSAGE
		You didn't provide a filter for the amis.
		If you're sure to test __ALL__ the amis,
		please provide the '.*' pattern.
		Usage:
			$0 <pass_filter> [<block_filter>]
		default block filter is 'pass' string
		to avoid testing already 'passed' amis.
__MESSAGE
	exit 1
fi

block_amis=${2-pass}
src_valid=${VALID:-.}
releng_candidates | filter "${pass_amis}" "${block_amis}" | csv_translate | \
	while read line ; do
		if [ -z "$DRYRUN" ] ; then
			dst_valid=$( mktemp -d /tmp/valid_XXXXXX ) || exit $?
			cp -fr $src_valid/* $dst_valid || exit $?
			if [ -n "${PARALLEL}" ] ; then
				( random_sleep ; validate $dst_valid $line && rm -rf $dst_valid ) &
			else
				( validate $dst_valid $line && rm -rf $dst_valid )
			fi
		else
			echo "DRYRUN: $line"
		fi
	done



