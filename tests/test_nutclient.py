#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This source code is provided for testing/debuging purpose ;)

import sys

from nut3 import PyNUT3Client

if __name__ == "__main__":

    print("PyNUT3Client test...")
    nut = PyNUT3Client(debug=True)
    # nut    = PyNUT3Client( login="upsadmin", password="upsadmin", debug=True )

    print(80 * "-" + "\nTesting 'GetUPSList' :")
    result = nut.GetUPSList()
    print(f"\033[01;33m{result}\033[0m\n")

    print(80 * "-" + "\nTesting 'GetUPSVars' :")
    result = nut.GetUPSVars("dummy")
    print(f"\033[01;33m{result}\033[0m\n")

    print(80 * "-" + "\nTesting 'GetUPSCommands' :")
    result = nut.GetUPSCommands("dummy")
    print(f"\033[01;33m{result}\033[0m\n")

    print(80 * "-" + "\nTesting 'GetRWVars' :")
    result = nut.GetRWVars("dummy")
    print(f"\033[01;33m{result}\033[0m\n")

    print(80 * "-" + "\nTesting 'RunUPSCommand' (Test front panel) :")
    try:
        result = nut.RunUPSCommand("UPS1", "test.panel.start")
    except:
        result = sys.exc_info()[1]
    print(f"\033[01;33m{result}\033[0m\n")

    print(80 * "-" + "\nTesting 'SetUPSVar' (set ups.id to test):")
    try:
        result = nut.SetRWVar("UPS1", "ups.id", "test")
    except:
        result = sys.exc_info()[1]
    print(f"\033[01;33m{result}\033[0m\n")
