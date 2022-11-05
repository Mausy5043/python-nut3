#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A demonstration of the use of the `python-nut3` package

Copyright (c) 2022 Mausy5043

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

nut3_dir = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + '/src/')
sys.path.append(nut3_dir)

from pynut3 import nut3  # noqa


def demo(ip: str):
    """Perform the demonstration.

    Args:
        ip (str): IP address or hostname of the UPS-server

    Returns:
        None
    """
    client = nut3.PyNUT3Client(host=ip)

    # client.ver returns a string
    print(f"\nNUT driver version: {client.ver()}")
    print(f"Scanning for UPSes...")
    ups_dict = client.list_ups()
    for ups_id, desc in ups_dict.items():
        print(f"'{desc}' is called with id '{ups_id}'")

        # client.description returns a string
        print(f"\nclient.description({ups_id}) returns: {client.description(ups_id)}")

        # client.num_login returns the numer of users logge into the UPS
        print(f"Number of users : {client.num_logins(ups_id)}")

        # client.list_commands returns a dict
        try:
            clnts_dict = client.list_clients(ups_id)
            print(f"\nUPS '{ups_id}' has the following clients connected")
            for var, value in clnts_dict.items():
                print(f"{var:<36}: {value}")
        except nut3.PyNUT3Error:
            print(f"\n** UPS '{ups_id}' does not support listing it's clients")

        # client.list_vars returns a dict
        vars_dict = client.list_vars(ups_id)
        rw_vars_dict = client.list_rw_vars(ups_id)
        print(f"\nUPS '{ups_id}' has the following variables available:")
        for var, value in vars_dict.items():
            rw_ro = "  (r-)"
            if var in rw_vars_dict:
                rw_ro = "  (rw)"
            print(f"{rw_ro} {var:<36}: {value}")

        # client.list_commands returns a dict
        cmds_dict = client.list_commands(ups_id)
        print(f"\nUPS '{ups_id}' has the following commands available")
        for var, value in cmds_dict.items():
            print(f"{var:<20}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute a demo of the package.")
    parser.add_argument("--host",
                        type=str,
                        required=True,
                        help="IP-address or hostname of the UPS-server"
                        )
    OPTION = parser.parse_args()

    demo(OPTION.host)
