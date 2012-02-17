%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
 
Name:           XrdTestFramework
Version:        0.0.1
Release:        1%{?dist}
License:	GNU/GPL
Summary:        Xrootd Testing Framework consists of 3 components: Master, Slave and Hypervisor.
Group:          Development/Tools
Packager:	Lukasz Trzaska <ltrzaska@cern.ch>
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

mkdir -p %{buildroot}%{_sysconfdir}/XrdTest
mkdir -p %{buildroot}%{_sysconfdir}/XrdTest/certs
mkdir -p %{buildroot}%{_sbindir}

install -m 755 XrdTestSlave.py %{buildroot}%{_sbindir}
install -m 755 XrdTestSlave.conf %{buildroot}%{_sysconfdir}/XrdTest
install -m 755 certs/slavecert.pem %{buildroot}%{_sysconfdir}/XrdTest/certs
install -m 755 certs/slavekey.pem %{buildroot}%{_sysconfdir}/XrdTest/certs

install -m 755 XrdTestMaster.py %{buildroot}%{_sbindir}
install -m 755 XrdTestMaster.conf %{buildroot}%{_sysconfdir}/XrdTest
install -m 755 certs/mastercert.pem %{buildroot}%{_sysconfdir}/XrdTest/certs
install -m 755 certs/masterkey.pem %{buildroot}%{_sysconfdir}/XrdTest/certs

install -m 755 XrdTestHypervisor.py %{buildroot}%{_sbindir}
install -m 755 XrdTestHypervisor.conf %{buildroot}%{_sysconfdir}/XrdTest
install -m 755 certs/hypervisorcert.pem %{buildroot}%{_sysconfdir}/XrdTest/certs
install -m 755 certs/hypervisorkey.pem %{buildroot}%{_sysconfdir}/XrdTest/certs
install -m 755 lib/ClusterManager.py %{libs_path}

%package -n XrdTestMaster
Summary: Xrd Test Master is component of XrdTestFramework.
Group:   Development/Tools
%description -n XrdTestMaster
Xrd Test Master is component of XrdTestFramework.
%files -n XrdTestMaster
%defattr(-,root,root,-)
%{python_sitelib}/XrdTest
%{_sysconfdir}/XrdTest/certs/mastercert.pem
%{_sysconfdir}/XrdTest/certs/masterkey.pem
%{_sysconfdir}/XrdTest/XrdTestMaster.conf
%{_sbindir}/XrdTestMaster.py

%package -n XrdTestSlave
Summary: Xrd Test Slave is component of XrdTestFramework.
Group:   Development/Tools
%description -n XrdTestSlave
Xrd Test Slave is component of XrdTestFramework.
%files -n XrdTestSlave
%defattr(-,root,root,-)
%{python_sitelib}/XrdTest
%{_sysconfdir}/XrdTest/certs/slavecert.pem
%{_sysconfdir}/XrdTest/certs/slavekey.pem
%{_sysconfdir}/XrdTest/XrdTestSlave.conf
%{_sbindir}/XrdTestSlave.py

%package -n XrdTestHypervisor
Summary: Xrd Test Hypervisor is component of XrdTestFramework.
Group:	 Development/Tools
%description -n XrdTestHypervisor
Xrd Test Hypervisor is component of XrdTestFramework.
%files -n XrdTestHypervisor
%defattr(-,root,root,-)
%{python_sitelib}/XrdTest
%{_sysconfdir}/XrdTest/certs/hypervisorcert.pem
%{_sysconfdir}/XrdTest/certs/hypervisorkey.pem
%{_sysconfdir}/XrdTest/XrdTestHypervisor.conf
%{_sbindir}/XrdTestHypervisor.py

%clean
[ "%{buildroot}" != "/" fa] && rm -rf %{buildroot}

%changelog
* Wed Feb 15 2012 Lukasz Trzaska <ltrzaska@cern.ch>
- initial package
