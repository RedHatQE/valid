Name:		valid
Version:	0.6
Release:	1%{?dist}
Summary:	Image validation (threaded) server

Group:		Development/Python
License:	GPLv3+
URL:		https://github.com/RedHatQE/valid
Source0:	%{name}-%{version}.tar.gz
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:  noarch

BuildRequires:	python-devel
Requires:	python-patchwork >= 0.3 
Requires:       python-paramiko PyYAML python-boto

%if 0%{?fedora} >= 18
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
BuildRequires: systemd
%endif

%description
Cloud image validation suite

%package client
Group:		Development/Python
Summary:	Image validation (threaded) client
Requires: PyYAML

%description client
Cloud image validation suite

%prep
%setup -q

%build

%install
%{__python} setup.py install -O1 --root $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT%{_sharedstatedir}/valid
%if 0%{?fedora} >= 15
install -p -D -m 644 systemd/valid.service %{buildroot}/lib/systemd/system/valid.service
install -p -D -m 644 systemd/valid-tmpfile %{buildroot}%{_libdir}/../lib/tmpfiles.d/valid.conf
%endif

%clean
rm -rf $RPM_BUILD_ROOT

%pre
getent group valid >/dev/null || groupadd -r valid
getent passwd valid >/dev/null || \
useradd -r -g valid -d /var/lib/valid -s /sbin/nologin \
        -c "Validation user" valid
        exit 0

%if 0%{?fedora} >= 18
%post
%systemd_post %{name}.service

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart %{name}.service
%endif

%files
%defattr(-,root,root,-)
%doc LICENSE README.md
%attr(0755, root, root) %{_bindir}/valid_runner.py
%attr(0755, root, root) %{_bindir}/valid_cert_creator.py
%attr(0755, root, root) %{_bindir}/valid_debug_run.py
%dir %{_sysconfdir}/valid
%config(noreplace) %attr(0640, root, valid) %{_sysconfdir}/validation.yaml
%config(noreplace) %attr(0640, root, valid) %{_sysconfdir}/sysconfig/valid
%config(noreplace) %attr(0644, root, valid) %{_sysconfdir}/valid/setup_script.sh
%{python_sitelib}/*.egg-info
%{python_sitelib}/valid/*
%{_datadir}/%name
%if 0%{?fedora} >= 15
/lib/systemd/system/*.service
%{_libdir}/../lib/tmpfiles.d/valid.conf
%endif
%attr(0775, valid, valid) %{_sharedstatedir}/valid

%files client
%attr(0755, root, root) %{_bindir}/valid_client.py
%attr(0755, root, root) %{_bindir}/valid_bugzilla_reporter.py

%changelog
* Tue May 14 2013 Vitaly Kuznetsov <vitty@redhat.com> 0.6-1
- new version (vitty@redhat.com)

* Tue Feb 19 2013 Vitaly Kuznetsov <vitty@redhat.com> 0.5-1
- new version

* Thu Jan 03 2013 milan <mkovacik@redhat.com> 0.4-1
- pep8 (mkovacik@redhat.com)
- fixes for testcase_14_host_details (mkovacik@redhat.com)
- fixed key error handling (mkovacik@redhat.com)
- testcase_31_subscription_management.py: pep8 (vitty@redhat.com)
- fix for systemd-enabled systems (vitty@redhat.com)
- testcase_08_memory.py: fix for colorful output (vitty@redhat.com)
- merge hwp into params bugfixes (vitty@redhat.com)
- applicable/not_applicable lists for tests (vitty@redhat.com)
- systemd unit (vitty@redhat.com)
- add special user for server, separate client subpackage (vitty@redhat.com)
- subscription manager test enhancements (mkovacik@redhat.com)
- Merge remote branch 'origin/threaded' into threaded (mkovacik@redhat.com)
- enhanced version handling in testcase 27, region attribute added to debug
  runner (mkovacik@redhat.com)
- scripts/valid_runner.py: KeyError -> bad test (vitty@redhat.com)
- avoiding name resolution in iptables dump (mkovacik@redhat.com)
- introduce 'skipped' testing result (vitty@redhat.com)
- testcase_29_swap_file.py: no swap for x86_64 (vitty@redhat.com)
- valid_runner.py: pep8 (vitty@redhat.com)
- valid_debug_run.py: dump yaml (vitty@redhat.com)
- testcase_30_rhn_certificates.py: protect against failures (vitty@redhat.com)
- Merge remote branch 'origin/threaded' into threaded (mkovacik@redhat.com)
- support list of commands (mkovacik@redhat.com)
- testcase_11_package_set: insreace timeout for rpm (vitty@redhat.com)
- valid_debug_run.py: typo (vitty@redhat.com)
- testcase_21_disk_size_format.py: fix for multiple disks (vitty@redhat.com)
- debug runner (vitty@redhat.com)
- Merge remote branch 'origin/threaded' into threaded (mkovacik@redhat.com)
- fixed the reading (mkovacik@redhat.com)
- tiny fix (mkovacik@redhat.com)
- fixes (mkovacik@redhat.com)
- refactoring repos test (mkovacik@redhat.com)
- valid_runner.py: stress test bugfixes and optimizations (vitty@redhat.com)
- valid_client.py: add stdin support (vitty@redhat.com)
- providing timeout to rpm queries (mkovacik@redhat.com)
- bugfixes for cloud-init-enabled instances and numbers in data
  (vitty@redhat.com)
- pretify bugzilla output (vitty@redhat.com)
- remove 'Request succeeded' output (vitty@redhat.com)
- HTTPS (vitty@redhat.com)
- certs setup (vitty@redhat.com)
- introducing 64 packages (mkovacik@redhat.com)
- example_f17_m1small.yaml (vitty@redhat.com)
- valid_cert_creator.py introduced (vitty@redhat.com)
- sort tests in bugzilla (vitty@redhat.com)
- fix 'fail' bug in bugzilla reporter (vitty@redhat.com)
- run setup commands in a different way (vitty@redhat.com)
- s,hwm,hvm,g (vitty@redhat.com)
- Migrate public_dns_name/private_ip_address logic to patchwork
  (vitty@redhat.com)
- implement ami-specific setup scripts (vitty@redhat.com)
- check 'ntry' for setup stage (vitty@redhat.com)
- separate "setup" stage (vitty@redhat.com)
- Merge remote-tracking branch 'origin/threaded' into threaded
  (vitty@redhat.com)
- Implement CTRL-C feature (vitty@redhat.com)
- Merge remote branch 'origin/threaded' into threaded (mkovacik@redhat.com)
- merge (mkovacik@redhat.com)
- add shebang (vitty@redhat.com)
- introducing custom setup script and subnet_id handling (mkovacik@redhat.com)

* Mon Dec 17 2012 Vitaly Kuznetsov <vitty@redhat.com> 0.3-1
- new version
* Wed Dec 05 2012 Vitaly Kuznetsov <vitty@redhat.com> 0.2-1
- new package built with tito

