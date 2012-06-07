
from interfaces import IOSVersionSwitch, IHWProfileSwitch
import osversion
import ec2
import factories


TESTS=[]
#VERSION = osversion.OSVersion()
#VERSION.major = 6
#VERSION.minor = 2


# get all the tests
from factories import FACTORIES
for name, aFactoryType in FACTORIES:
	# call the switch hooks
	factory = aFactoryType()
	if IOSVersionSwitch.implementedBy(aFactoryType):
		factory.os_version_switch(VERSION)
	#if IHWProfileSwitch.implementedBy(aFactoryType):
	#	factory.os_profile_switch(VERSION)
	aTest= factory.get_test()
	TESTS.append(aTest)


