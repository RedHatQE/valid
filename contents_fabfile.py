from fabric.api import run, local, task, env, execute
from fabric.operations import reboot
from pprint import pprint
import urllib, json

def manifest_cdn_package_set(manifest):
	"""return a set of packages a CDN manifest mentions"""
	packages = []
	for product in manifest['cdn']['products'].keys():
		for path in manifest['cdn']['products'][product]['Repo Paths'].keys():
			packages += manifest['cdn']['products'][product]['Repo Paths'][path]
	return set(packages)

def to_bool(value):
	ret = False
	ret |= value == 'y'
	ret |= value == 'Y'
	ret |= value == 'Yes'
	ret |= value == 'yes'
	ret |= value == 'True'
	ret |= value == 'true'
	ret |= value == '1'
	return ret

def failed_to_update_or_missing(before, after, manifest):
	return before.intersection(after) - manifest

def updated_over(before, after, manifest):
	return (after - before) - manifest

@task
def prepare_staging():
	"""modify system to work with stage RHUI"""
	run('echo "10.3.94.100 rhui2-cds01-stage.us-east-1.aws.ce.redhat.com" >> /etc/hosts')
	run("sed -i 's/rhui2-cds01.us-east-1.aws.ce.redhat.com/rhui2-cds01-stage.us-east-1.aws.ce.redhat.com/' /etc/yum.repos.d/redhat-rhui.repo")
	run('echo rhui2-cds01-stage.us-east-1.aws.ce.redhat.com > /etc/yum.repos.d/rhui-load-balancers.conf')

@task
def update(stage=False):
	"""perform system update"""
	if stage:
		execute(prepare_staging)
	run('/usr/bin/yum update -y --disablerepo="*" --enablerepo="*rhel-server-releases*"')
	reboot(wait=180)
	run('/usr/bin/package-cleanup -y --oldkernels --count=1')

def remote_packages(filter_pass='.*', filter_block='gpg-pubkey-.*|rh-amazon-rhui-client-.*'):
	return set(run("/bin/rpm -qa | egrep '%s' | egrep -v '%s' | sed -e 's/$/.rpm/'" % (filter_pass, filter_block)).split('\r\n'))


@task
def contents_check(manifest, stage='False'):
	"""print packages not provided by given CDN manifest URL"""
	manifest_j = json.load(urllib.urlopen(manifest))
	manifest_packages = manifest_cdn_package_set(manifest_j)
	before_packages = remote_packages()
	execute(update, stage=to_bool(stage))
	after_packages = remote_packages()
	print "# --\n# %s" % (env.host_string,)
	print "failed_or_missing= ",
	pprint(failed_to_update_or_missing(before_packages, after_packages, manifest_packages))
	print "\nupdated_over= ",
	pprint (updated_over(before_packages, after_packages, manifest_packages))
	print "\ndiff= ",
	pprint (after_packages - manifest_packages)
