Summary: vcputune, tools to tweak vcpu usage in dom0.
Name: vcputune
Version: 2.0.1
Release: 1.xs44%{dist}

Source0: https://code.citrite.net/rest/archive/latest/projects/XS/repos/vcputune/archive?at=refs%2Ftags%2Fv2.0.1&format=tar.gz&prefix=vcputune-2.0.1#/vcputune-2.0.1.tar.gz


Provides: gitsha(https://code.citrite.net/rest/archive/latest/projects/XS/repos/vcputune/archive?at=refs%2Ftags%2Fv2.0.1&format=tar.gz&prefix=vcputune-2.0.1#/vcputune-2.0.1.tar.gz) = 0bf371faff06c848244488d32c3ccb8feddbc868

License: LGPLv2+
Group: Development/Tools
Buildroot: %{_tmppath}/%{name}-root
BuildArch: noarch

%description
This package's purpose is to provide a set of tools to tweak vcpu usage in dom0.


%prep
%autosetup -p1
%build
%install

mkdir -p ${RPM_BUILD_ROOT}/opt/xensource/bin
install -m 755 host-cpu-tune ${RPM_BUILD_ROOT}/opt/xensource/bin/host-cpu-tune

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/opt/xensource/bin/host-cpu-tune

%changelog
* Thu May 22 2014 Simon Rowe <simon.rowe@eu.citrix.com> - 2.0.1
- Move script to /opt/xensource/bin

* Tue Feb 12 2013 Felipe Franciosi <felipe.franciosi@citrix.com> - 2.0
- Package rewritten to use host-cpu-tune instead of tune-vcpus and advise-pcpus

* Tue Apr 23 2012 Marcus Granado <marcus.granado@citrix.com> - 1.0
- Created
