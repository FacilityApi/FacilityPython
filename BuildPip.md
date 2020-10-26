# Building the FacilityPython Pip Package

When `facility.py` changes, a new verison of [`facilitypython`](https://pypi.org/project/facilitypython/) should be published.

1. Update the version number in `setup.py` to match `VersionPrefix` in `Directory.build.props`.
2. Ensure PyPI credentials with permission to update `facilitypython` are in `~/.pypirc` or ready for interactive entry.
2. Run `./build pip-publish`
