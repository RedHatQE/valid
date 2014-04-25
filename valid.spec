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
Requires:       python-rpyc python-paramiko PyYAML python-boto
Requires:	valid-client = %{version}-%{release}

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
%{python_sitelib}/valid/*.py*
%exclude %{python_sitelib}/valid/__init__.py*
%exclude %{python_sitelib}/valid/valid_result.py*
%{python_sitelib}/valid/testing_modules
%{python_sitelib}/valid/cloud
%{_datadir}/%name
%if 0%{?fedora} >= 15
/lib/systemd/system/*.service
%{_libdir}/../lib/tmpfiles.d/valid.conf
%endif
%attr(0775, valid, valid) %{_sharedstatedir}/valid

%files client
%attr(0755, root, root) %{_bindir}/valid_client.py
%attr(0755, root, root) %{_bindir}/valid_bugzilla_reporter.py
%{python_sitelib}/*.egg-info
%{python_sitelib}/valid/__init__.py*
%{python_sitelib}/valid/valid_result.py*

%changelog
* Tue May 14 2013 Vitaly Kuznetsov <vitty@redhat.com> 0.6-1
- new version

* Tue Feb 19 2013 Vitaly Kuznetsov <vitty@redhat.com> 0.5-1
- new version

* Thu Jan 03 2013 milan <mkovacik@redhat.com> 0.4-1
- new version

* Mon Dec 17 2012 Vitaly Kuznetsov <vitty@redhat.com> 0.3-1
- new version

* Wed Dec 05 2012 Vitaly Kuznetsov <vitty@redhat.com> 0.2-1
- new package built with tito

