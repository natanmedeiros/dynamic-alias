---
trigger: always_on
---

Global Test Rules
These rules must be applied to every test file.
1. Create a test for every pattern present in @config-file-rules.md
2. Create multiple tests for every pattern
3. Create and use ./tests/dya.yaml as configuration file with --dya-config
4. Use .tests/dya.json as cache file and use with --dya-cache
5. every test must be related to ./tests/dya.yaml definition