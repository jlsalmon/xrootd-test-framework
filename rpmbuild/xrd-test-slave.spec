%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
# 
Name:           XrdTestSlave
Version:        0.0.1
Release:        1%{?dist}
License:	GNU/GPL
Summary:        XrdTestSlave daemon is client part of a xrootd testing framework.
Group:          Development/Tools
Packager:	Lukasz Trzaska \<ltrzaska@cern.ch\> 
URL:            http://xrootd.org
Source0:        http://xrootd.org/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
Requires: 	python >= 2.4

%description
XRootD testing framework, client's daemon application.

%prep
%setup -q
 
%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
%define libs_path %{buildroot}%{python_sitelib}/XrdTest

mkdir -p %{libs_path}
install -m 755 lib/Utils.py %{libs_path}
install -m 755 lib/SocketUtils.py %{libs_path}
install -m 755 lib/Daemon.py %{libs_path}
install -m 755 lib/TestUtils.py %{libs_path}

mkdir -p %{buildroot}/etc/XrdTest
mkdir -p %{buildroot}/etc/XrdTest/certs/slave
install -m 755 XrdTestSlave.conf %{buildroot}/etc/XrdTest
install -m 755 slavecert.pem %{buildroot}/etc/XrdTest/certs/slave
install -m 755 slavekey.pem %{buildroot}/etc/XrdTest/certs/slave

mkdir -p %{buildroot}/usr/sbin
install -m 755 XrdTestSlave.py %{buildroot}/usr/sbin

%clean
[ "%{buildroot}" != "/" fa] && rm -rf %{buildroot}
 
%files
%defattr(-,root,root,-)
%{_sysconfdir}/*
%{_sbindir}/*
%{python_sitelib}/XrdTest

%changelog
* Wed Feb 15 2012 Lukasz Trzaska <ltrzaska@cern.ch>
- initial package
