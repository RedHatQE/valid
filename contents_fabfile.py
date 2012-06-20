from fabric.api import run, local, task, env
from pprint import pprint
import urllib, json

def manifest_cdn_package_set(manifest):
	"""return a set of packages a CDN manifest mentions"""
	packages = []
	for product in manifest['cdn']['products'].keys():
		for path in manifest['cdn']['products'][product]['Repo Paths'].keys():
			packages += manifest['cdn']['products'][product]['Repo Paths'][path]
	return set(packages)

@task
def contents_check(manifest):
	"""print packages not provided by given CDN manifest URL"""
	manifest_j = json.load(urllib.urlopen(manifest))
	packages = manifest_cdn_package_set(manifest_j)
	installed_packages = set(run("/bin/rpm -qa | sed -e 's/$/.rpm/'").split('\r\n'))
	print "# --\n# %s" % (env.host_string,)
	pprint (installed_packages - packages)
