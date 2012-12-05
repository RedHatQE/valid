Name:		valid
Version:	0.1
Release:	0%{?dist}
Summary:	Image validation (threaded)

Group:		Development/Python
License:	GPLv3+
URL:		https://github.com/RedHatQE/valid
Source0:	%{name}-%{version}.tar.gz
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:  noarch

BuildRequires:	python-devel
Requires:	python-patchwork python-paramiko PyYAML

%description

%prep
%setup -q

%build

%install
%{__python} setup.py install -O1 --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc LICENSE README.md
%attr(0755, root, root) %{_bindir}/*.py
%config(noreplace) %attr(0600, root, root) %{_sysconfdir}/valid.yaml
%{python_sitelib}/*.egg-info
%{python_sitelib}/valid/*
%{_datadir}/%name/hwp

%changelog
