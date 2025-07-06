# Test Suite

This directory contains Bats tests and Python unit tests for the homelab infrastructure scripts.

Interactive tests are automated using `test/expect_helper.sh`, which wraps
[`expect`](https://core.tcl-lang.org/expect/index). Pass the command to run
followed by prompt/response pairs:

```bash
run test/expect_helper.sh \
    "Create service config file" \
    "Continue anyway? \\[y/N\\]:" "n"
```

Ensure dependencies are installed prior to running tests:

```bash
make deps
make test
```
