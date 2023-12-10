#!/usr/bin/env python

"""Test script for pexpect usage with NUT UPS.

Linux:
[1] Trying 192.168.2.17...
[2] Connected to 192.168.2.17.
[3] Escape character is '^]'.
[4]
[5] ERR UNKNOWN-COMMAND
[1] VER
[2] Network UPS Tools upsd 2.8.0 - http://www.networkupstools.org/

macOS:
[1]
[2] ERR UNKNOWN-COMMAND
[1] VER
[2] Network UPS Tools upsd 2.8.0 - http://www.networkupstools.org/

"""

import pexpect
import platform

host = "192.168.2.17"
port = "3493"
COMMAND = "VER"
if platform.system() == "Darwin":  # macOS
    shl_cmd = "nc"
elif platform.system() == "Linux":
    shl_cmd = "telnet"
else:
    raise Exception("Unsupported platform")

def wait_for_output(child_process, timeout=5) -> list[str]:
    lineno = 1
    lines: list[str] = []
    while True:
        try:
            child_process.expect([pexpect.EOF, '\n'], timeout)
            lines.append(f"[{lineno}] {child.before.decode('utf-8')}")
        except pexpect.exceptions.TIMEOUT:
            break
        lineno += 1
    return lines

# Create a Telnet child process
with pexpect.spawn(f'{shl_cmd} {host} {port}', timeout=5) as child:

    # Send a newline character (assuming no login is required)
    child.sendline('')
    result = wait_for_output(child_process=child)
    for line in result:
        print(line)

    # Send the command
    child.sendline(COMMAND)
    result = wait_for_output(child_process=child)
    for line in result:
        print(line)
