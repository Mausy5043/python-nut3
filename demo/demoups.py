#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A demonstration of the use of the `python-nut3` package.

Copyright (c) 2023 Mausy5043

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import os
import sys

nut3_dir: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) + "/src/"
sys.path.append(nut3_dir)

# pylint: disable=wrong-import-position
from pynut3 import nut3  # noqa


# pylint: disable=invalid-name
def demo() -> None:
    """Perform the demonstration.

    Args:
        ip (str): IP address or hostname of the UPS-server

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Execute a demo of the package.")
    parser.add_argument(
        "--server",
        type=str,
        required=True,
        help="IP-address or hostname of the UPS-server",
    )
    parser.add_argument(
        "-f",
        "--fast",
        action="store_true",
        help="Skip fetching descriptions",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="For debugging",
    )
    OPTION = parser.parse_args()
    debug = False
    if OPTION.debug:
        debug = True
    desc = True
    if OPTION.fast:
        desc = False
    # For the demo we include descriptors. In normal use this is likely
    # not such a good idea because it will make the initialisation slo-o-ow.
    client = nut3.PyNUT3Client(host=OPTION.server, descriptors=desc, debug=debug)

    # client.version returns a string cnontaining the version of the server
    print(client.version())
    print()
    print("Connected Devices & Available Commands:")
    for device, state in client.devices.items():
        print(f"{state['timestamp']}")
        print(f"    {device:<32} : {state['description']}")
        print("    Commands")
        for name, desc in state["commands"].items():
            print(f"        {name:<32}({desc})")
        print("    Variables & Settings")
        for name, item in state["vars"].items():
            print(f"  ({item[1]})  {name:<32}= {item[0]:<30}({item[2]})")
        print()
    client.update_all()
    print()
    for device, state in client.devices.items():
        print(f"{device} data updated on {state['timestamp']}")
    # You can also send commands directly
    print(client.cmd("LIST CLIENT ups"))
    print(client.cmd("GET NUMLOGINS ups"))


if __name__ == "__main__":
    demo()
