
from factories import FACTORIES
from interfaces import IOSVersionSwitch, IHWProfileSwitch
import osversion
import factories

TESTS=[]
VERSION = osversion.OSVersion()
VERSION.major = 6
VERSION.minor = 2


# get all the tests
for name, aFactoryType in FACTORIES:
	# call the switch hooks
	factory = aFactoryType()
	if IOSVersionSwitch.implementedBy(aFactoryType):
		factory.os_version_switch(VERSION)
	TESTS.append(factory.get_test())
