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

@task
def prepare_staging():
	"""modify system to work with stage RHUI"""
	run('echo "10.3.94.100 rhui2-cds01-stage.us-east-1.aws.ce.redhat.com" >> /etc/hosts')
	run("sed -i 's/rhui2-cds01.us-east-1.aws.ce.redhat.com/rhui2-cds01-stage.us-east-1.aws.ce.redhat.com/' /etc/yum.repos.d/redhat-rhui.repo")
	run('echo rhui2-cds01-stage.us-east-1.aws.ce.redhat.com > /etc/yum.repos.d/rhui-load-balancers.conf')

@task
def update(stage=False,reboot=False):
	"""perform system update"""
	if stage:
		execute(prepare_staging)
	run('/usr/bin/yum update -y --disablerepo="*" --enablerepo="*rhel-server-releases*"')
	if reboot:
		reboot(wait=180)

@task
def contents_check(manifest, stage='False', reboot='False'):
	"""print packages not provided by given CDN manifest URL"""
	manifest_j = json.load(urllib.urlopen(manifest))
	packages = manifest_cdn_package_set(manifest_j)
	execute(update, stage=to_bool(stage), reboot=to_bool(reboot))
	installed_packages = set(run("/bin/rpm -qa | sed -e 's/$/.rpm/'").split('\r\n'))
	print "# --\n# %s" % (env.host_string,)
	pprint (installed_packages - packages)
