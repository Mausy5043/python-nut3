[![PyPI version](https://img.shields.io/pypi/v/pynut3.svg?logo=pypi&logoColor=FFE873)](https://pypi.org/project/pynut3)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pynut3.svg?logo=python&logoColor=FFE873)](https://pypi.org/project/pynut3)
[![PyPI downloads](https://img.shields.io/pypi/dm/pynut3.svg)](https://pypistats.org/packages/pynut3)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)

# (DEPRECATED) pynut3

#### (aka python-nut3)

This is a Python3 library to allow communication with NUT ([Network UPS Tools](http://www.networkupstools.org/)) Uninterruptible Power Supply servers following [RFC-9271](https://www.rfc-editor.org/rfc/rfc9271.html)

**Note**: This is an unofficial project, and is in no way supported or endorsed by the [Network UPS Tools developers](https://github.com/networkupstools).

## Requirements

Development of this package is done in Python 3.11. The package is considered forwards compatible probably upto Python 3.12 and possibly also beyond. Backwards compatibility is not guaranteed on versions prior to 3.9; if it works on Python 3.8 or before consider yourself lucky.
[Python versions that are end-of-life](https://devguide.python.org/versions/) are not supported.

## Installation

On Linux systems `pynut3` requires telnet to be installed. If it is not available on your system you'll need to install it first.
```bash
sudo apt install telnet
```
On macOS `telnet` is not needed; `nc` will be used automatically.
Then install using:
```bash
python -m pip install pynut3
```
This software was not tested on systems other than Linux (Debian) and macOS. If you have access to another OS, feel free to contribute improvements for support.

## Usage

See `demo/upsdemo.py` for a usage example.

Please note that this module has completely and intentionally broken backwards compatibility with (previous) versions of pynut3.

## Acknowledgements

Based on various NUT Client related Python scripts, written by David Goncalves
as [PyNUT](https://github.com/networkupstools/nut/tree/master/scripts/python), and released under GPL v3.
Later overhauled by rshipp with Python3 modifications by hordurk, george2 and mezz64.
Others will have contributed along the way. I was not able to reliably find their names.

Further updates are by me (Mausy5043) and based/inspired on prior work from timurlenk07, StSAV012, rshipp & Rojer-X86.

## License

The GPL v3 license continues to apply. See [LICENSE](LICENSE).
