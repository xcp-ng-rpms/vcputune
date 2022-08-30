%global package_speccommit b9aa760ebceaa8069588081fce75b52dbb0d6aad
%global usver 2.0.1
%global xsver 5
%global xsrel %{xsver}%{?xscount}%{?xshash}
%global package_srccommit v2.0.1

Summary: vcputune, tools to tweak vcpu usage in dom0.
Name: vcputune
Version: 2.0.1
Release: %{?xsrel}%{?dist}
Source0: host-cpu-tune.py
License: LGPLv2+
Group: Development/Tools
Buildroot: %{_tmppath}/%{name}-root
BuildArch: noarch

%description
This package's purpose is to provide a set of tools to tweak vcpu usage in dom0.


%prep
%build
%install

mkdir -p ${RPM_BUILD_ROOT}/opt/xensource/bin
install -m 755 %{SOURCE0} ${RPM_BUILD_ROOT}/opt/xensource/bin/host-cpu-tune

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/opt/xensource/bin/host-cpu-tune

%changelog
* Fri Dec 10 2021 Edwin Török <edvin.torok@citrix.com> - 2.0.1-5
- Maintenance: move single source into .spec repo instead of separate repo
- CP-38218: rename to .py so SonarQube can find it

* Mon Dec 06 2021 Edwin Török <edvin.torok@citrix.com> - 2.0.1-4
- CP-38218: add static-analysis.json

* Mon Jan 04 2021 Edwin Török <edvin.torok@citrix.com> - 2.0.1-3
- Imported v2.0.1-1.xs44 from xenserver-specs
- Imported into Koji

* Thu May 22 2014 Simon Rowe <simon.rowe@eu.citrix.com> - 2.0.1
- Move script to /opt/xensource/bin

* Tue Feb 12 2013 Felipe Franciosi <felipe.franciosi@citrix.com> - 2.0
- Package rewritten to use host-cpu-tune instead of tune-vcpus and advise-pcpus

* Mon Apr 23 2012 Marcus Granado <marcus.granado@citrix.com> - 1.0
- Created
