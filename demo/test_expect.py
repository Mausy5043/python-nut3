#!/usr/bin/env python

"""Test script for pexpect usage with NUT UPS.

"""

import platform

import pexpect

host = "192.168.2.17"
port = "3493"
COMMAND = "VER"
if platform.system() == "Darwin":  # macOS
    shl_cmd = "nc"
elif platform.system() == "Linux":
    shl_cmd = "telnet"
else:
    raise Exception("Unsupported platform")


def wait_for_output(child_process, timeout: int = 5) -> list[str]:
    lineno = 1
    lines: list[str] = []
    while True:
        try:
            child_process.expect([pexpect.EOF, "\n"], timeout)
            lines.append(f"[{lineno}] {child_process.before.decode('utf-8')}")
        except pexpect.exceptions.TIMEOUT:
            break
        lineno += 1
    return lines


# Create a pexpect child process
with pexpect.spawn(f"{shl_cmd} {host} {port}", timeout=5, echo=False) as child:
    # Send a newline character (assuming no login is required)
    child.sendline("")
    result: list[str] = wait_for_output(child_process=child)
    for line in result:
        print(line)

    # Send the command
    child.sendline(COMMAND)
    result = wait_for_output(child_process=child)
    for line in result:
        print(line)
