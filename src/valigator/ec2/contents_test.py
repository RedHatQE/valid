from valigator.factories import RetValueCheckFactory

class RepolistFactory(RetValueCheckFactory):
	command = '/usr/bin/yum repolist'
	test_name = 'ec2.repolist_test'


class ZshSearch(RetValueCheckFactory):
	command = '/usr/bin/yum search zsh'
	test_name = 'ec2.yum_search_zsh'


class ZshInstall(RetValueCheckFactory):
	command = '/usr/bin/yum -y install zsh'
	test_name = 'ec2.yum_install_zsh'


class RpmQueryZsh(RetValueCheckFactory):
	command = "/bin/rpm -q --queryformat '%{NAME}\n' zsh"
	test_name = 'ec2.yum_rpm_querry_zsh'


class GroupList(RetValueCheckFactory):
	command = '/usr/bin/yum grouplist'
	test_name = 'ec2.yum_grouplist'

class DevelopmentTools(RetValueCheckFactory):
	command = "/usr/bin/yum -y groupinstall 'Development tools'"
	test_name = 'ec2.yum_install_development_tools'

