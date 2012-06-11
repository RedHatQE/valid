from valigator.factories import RetValueTestFactory, SimpleCommandTestFactory

class GetEnforceTestFactory(SimpleCommandTestFactory):
	test_name = "selinux_getenforce_test"
	expected_result = "Enforcing"
	command = "/usr/sbin/getenforce"


class SysconfigSelinuxTestFactory(SimpleCommandTestFactory):
	test_name = "selinux_sysconfig_selinux_test"
	expected_result = "enforcing"
	command = "grep ^SELINUX= /etc/sysconfig/selinux | cut -d\= -f2"


class SysconfigSelinuxTypeTestFactory(SimpleCommandTestFactory):
	test_name = "selinux_sysconfig_selinux_type_test"
	expected_result = "targeted"
	command = "grep ^SELINUXTYPE= /etc/sysconfig/selinux | cut -d\= -f2"


class FlipPermissiveSelinuxTestFactory(SimpleCommandTestFactory):
	test_name = "selinux_flip_permissive"
	expected_result = "Permissive"
	command = "/usr/sbin/setenforce Permissive && /usr/sbin/getenforce"

class FlipEnforcingSelinuxTestFactory(SimpleCommandTestFactory):
	test_name = "selinux_flip_enforcing"
	expected_result = "Enforcing"
	command = "/usr/sbin/setenforce Enforcing && /usr/sbin/getenforce"
