from valigator.factories import RetValueTestFactory

class RepolistFactory(RetValueTestFactory):
	command = '/usr/bin/yum repolist'
	test_name = 'ec2.repolist_test'


class ZshSearch(RetValueTestFactory):
	command = '/usr/bin/yum search zsh'
	test_name = 'ec2.yum_search_zsh'


class ZshInstall(RetValueTestFactory):
	command = '/usr/bin/yum -y install zsh'
	test_name = 'ec2.yum_install_zsh'


class RpmQueryZsh(RetValueTestFactory):
	command = "/bin/rpm -q --queryformat '%{NAME}\n' zsh"
	test_name = 'ec2.yum_rpm_querry_zsh'


class GroupList(RetValueTestFactory):
	command = '/usr/bin/yum grouplist'
	test_name = 'ec2.yum_grouplist'

class DevelopmentTools(RetValueTestFactory):
	command = "/usr/bin/yum -y groupinstall 'Development tools'"
	test_name = 'ec2.yum_install_development_tools'



