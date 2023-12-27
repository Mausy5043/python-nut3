# BUILDING

## Versionnumbers

We try to follow [semantic versioning](https://semver.org).
-   We don't have `0` MINOR or PATCH versionnumbers. Patterns `x.0.z` and `x.y.0` do not exist.
-   Testing versions are identified by odd-numbered MINOR versions.
-   Stable/production versions are identified by even-numbered MINOR versions.
-   MAJOR versions increase only when significant changes are made.

The following is documented here so I don't have to remember ;-)

## Building the package for testing (OWNERS ONLY)

To test changes the package may be built and uploaded to [test.pypi.org](https://test.pypi.org)
Preferably changes are done on a separate branch.

1.  Make the necessary changes against the `devel` branch...
2.  In `pyproject.toml` change the versionnumber.
    -   For testing we change the MINOR version to the next **odd** value.
    -   The first PATCH version always starts on x.y.1 and increases by +1 with every new build.
    -   Builds with the same versionnumber can't be uploaded to PyPi, so it's not like we have a choice.
3.  Run `./mkbld -b`
4.  Run `./mkbld -t`  *(installation instructions are displayed on the terminal after the upload)*
5.  Test the changes by installing the test package on a computer near you. *NOTE: You may have to try twice or wait a couple of minutes for the download to become available from PyPi*.
6.  Rinse and repeat...
7.  Execute `git commit -a; git push` to commit the changes.
8.  After succesfull testing create a pull request to merge the changes into the `devel` branch.


## Building the package for distribution (OWNERS ONLY)

To distribute a new production version the package must be built and uploaded to [pypi.org](https://pypi.org)

Start by making the necessary changes on the `devel` branch (see the previous paragraph). Test the changes and, if tests are succesfull create a pull request against the `devel` branch.s
1.  Merge the pull request from the `devel` branch into the `latest` branch.
    -   Merges from a separate branch are considered MINOR changes, unless they break existing functionality.
    -   Fixes etc. may be committed directly to the `latest` branch as a new PATCH version.
2.  In `pyproject.toml` change the versionnumber.
    -   For merges we change the MINOR version to the next **even** value.
    -   The first PATCH version always starts on x.y.1 and increases by +1 with every new build.
    -   Builds with the same versionnumber can't be uploaded to PyPi, so it's not like we have a choice.
3.  Run `./mkbld -b`
4.  Run `./mkbld -d`  *(installation instructions are displayed on the terminal after the upload)*
5.  Verify the changes by installing the distribution package on a computer near you. *NOTE: You may have to try twice or wait a couple of minutes for the download to become available from PyPi*.
6.  After succesfull testing of the distribution package create a new tag on the `latest` branch.
7.  Create a pull request from `latest` into `devel` to synchronise both branches.
