[![PyPI](https://img.shields.io/pypi/v/pynut3.svg)](https://pypi.python.org/pypi/pynut3)

python-nut3
===========

This is a Python3 library to allow communication with NUT ([Network UPS Tools](http://www.networkupstools.org/))
Uninterruptible Power Supply servers.

**Note**: This is an unofficial project, and is in no way supported or
endorsed by the [Network UPS Tools developers](https://github.com/networkupstools).

## Requirements

The module itself requires only Python3 (Python2 may work but is nolonger supported).

## Installation

    pip install pynut3

## Usage

Assuming you have a UPS which is connected to a host on the network with IP `192.168.2.17` it can be interogated as follows:

```python3
from pynut3 import nut3
client = nut3.PyNUT3Client(host='192.168.2.17')
print(client.help())
ups_dict = client.list_ups()
for k1, v1 in ups_dict.items():
    print(f"{v1} is called with id {k1}")
    vars_dict = client.list_vars(k)
    for k2, v2 in vars_dict.items():
        print(f"{k2}\t:\t{v2}")
```

Please note that this module has completely and intentionally broken backwards compatibility with previous versions of PyNUT.

## Acknowledgements

Based on various NUT Client related Python scripts, written by David Goncalves as [PyNUT](https://github.com/networkupstools/nut/tree/master/scripts/python), and released under GPL v3.   
Later overhauled by rshipp with Python3 modifications by hordurk, george2 and mezz64.
Others will have contributed along the way. I was not able to reliably find their names.

Further updates in this fork are by me (Mausy5043) and based/inspired on prior work from timurlenk07, StSAV012, rshipp & Rojer-X86

## License

The GPL v3 license continues to apply. See [LICENSE](LICENSE).
