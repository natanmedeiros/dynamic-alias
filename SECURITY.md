# Security Policy

## Supported Versions

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 1.1.x   | :white_check_mark: | Current stable release |
| 1.0.x   | :white_check_mark: | Previous stable release |
| < 1.0.0 | :x:                | Deprecated / Beta versions |

## Dependencies

We actively monitor and update dependencies for security vulnerabilities.

| Dependency | Minimum Version | Reason |
| ---------- | --------------- | ------ |
| cryptography | >=46.0.0 | CVE-2024-12797, CVE-2025-9230 fixed in 44.0.1+ |
| PyYAML | >=6.0.0 | No known CVEs |
| prompt_toolkit | >=3.0.0 | No known CVEs |

### pip Compatibility

Due to security requirements for `cryptography>=46`, **pip 22.0+ is required** for installation. The `cryptography` package's `pyproject.toml` uses TOML syntax that older pip versions cannot parse.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

If you have discovered a security vulnerability in **Dynamic Alias**, we appreciate your help in disclosing it to us in a responsible manner.

### How to Report

Please report the vulnerability via usage of the **"Advisories"** feature in the Security tab of this repository.

Please include the following details in your report:

* Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
* Full paths of source file(s) related to the manifestation of the issue.
* The location of the affected source code (tag/branch/commit or direct URL).
* Any special configuration required to reproduce the issue.
* Step-by-step instructions to reproduce the issue.
* Proof-of-concept or exploit code (if available).
* Impact of the issue, including how an attacker might exploit the issue.

### Our Response Process

1.  We will acknowledge receipt of your report.
2.  We will investigate the issue and determine its impact.
3.  We will formulate a plan to fix the vulnerability and communicate the timeline to you.
4.  Once fixed, we will release a patch and publish a security advisory.

We ask that you refrain from publicizing the vulnerability until we have had the opportunity to release a fix.

Thank you for helping keep Dynamic Alias safe!
