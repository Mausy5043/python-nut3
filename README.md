# pynut3 
#### (aka python-nut3)


[![PyPI version](https://img.shields.io/pypi/v/pynut3.svg?logo=pypi&logoColor=FFE873)](https://pypi.org/project/pynut3)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pynut3.svg?logo=python&logoColor=FFE873)](https://pypi.org/project/pynut3)
[![PyPI downloads](https://img.shields.io/pypi/dm/pynut3.svg)](https://pypistats.org/packages/pynut3)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)


This is a Python3 library to allow communication with NUT ([Network UPS Tools](http://www.networkupstools.org/))
Uninterruptible Power Supply servers.

**Note**: This is an unofficial project, and is in no way supported or
endorsed by the [Network UPS Tools developers](https://github.com/networkupstools).

## Requirements

Development of this package is done in Python 3.9. The package is considered forwards compatible at least upto Python 3.11 and probably also beyond. Backwards compatibility is not guaranteed; if it works on Python 3.7 or before consider yourself lucky. [Python versions that are end-of-life](https://devguide.python.org/versions/) are not supported.  


## Installation
```bash
pip install pynut3
```

## Usage

Assuming you have a UPS which is connected to a host on the network with IP `192.168.2.17` it can be interogated as follows:

```python3
from pynut3 import nut3
client = nut3.PyNUT3Client(host='192.168.2.17')
print(client.help())
ups_dict = client.get_dict_ups()
for k1, v1 in ups_dict.items():
    print(f"{v1} is called with id {k1}")
    vars_dict = client.get_dict_vars(k1)
    for k2, v2 in vars_dict.items():
        print(f"{k2}\t:\t{v2}")
```

Please note that this module has completely and intentionally broken backwards compatibility with (previous) versions of PyNUT.

## Acknowledgements

Based on various NUT Client related Python scripts, written by David Goncalves as [PyNUT](https://github.com/networkupstools/nut/tree/master/scripts/python), and released under GPL v3.   
Later overhauled by rshipp with Python3 modifications by hordurk, george2 and mezz64.
Others will have contributed along the way. I was not able to reliably find their names.

Further updates in this fork are by me (Mausy5043) and based/inspired on prior work from timurlenk07, StSAV012, rshipp & Rojer-X86

## License

The GPL v3 license continues to apply. See [LICENSE](LICENSE).
