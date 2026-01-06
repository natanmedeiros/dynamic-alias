Name:           dynamic-alias
Version:        0.1.0
Release:        1%{?dist}
Summary:        A dynamic alias builder for command line power users
License:        MIT
URL:            https://github.com/natanmedeiros/custom-alias
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

Requires:       python3-prompt-toolkit
Requires:       python3-pyyaml

%description
Dynamic Alias is a tool to create powerful aliases for your command line.

%prep
%autosetup

%build
%py3_build

%install
%py3_install

%files
%{_bindir}/dya
%{python3_sitelib}/dynamic_alias
%{python3_sitelib}/dynamic_alias-*.egg-info

%changelog
* Sun Jan 05 2026 Natan Medeiros <natanmedeiros@example.com> - 0.1.0-1
- Initial package
