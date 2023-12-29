#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A Python3 module for communicating with NUT (Network UPS Tools) servers.
In the sense of RFC-9271 this module provides a Management Daemon with limited capabilities.
Only monitoring functionality is currently supported.

* PyNUT3Error: Base class for custom exceptions.
* PyNUT3Client: Allows connecting to and communicating with PyNUT servers.

Copyright (C) 2013 george2

Modifications by mezz64 - 2016
Modifications by Mausy5043 - 2023

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

import logging.handlers
import platform
import shlex
import time

from typing import Any, Optional

import pexpect


class UnsupportedPlatformException(Exception):
    """Exception for unsupported platforms"""


if platform.system().lower() == "darwin":  # macOS
    _CALL_CMD = "nc"
    _SYSLOG_DEV = "/var/run/syslog"
elif platform.system().lower() == "linux":
    _CALL_CMD = "telnet"
    _SYSLOG_DEV = "/dev/log"
else:
    raise UnsupportedPlatformException(f"Unsupported platform {platform.system()}")

# configure the logging module
_facility = logging.handlers.SysLogHandler.LOG_DAEMON
_handlers = [logging.handlers.SysLogHandler(address=_SYSLOG_DEV, facility=_facility)]
logging.basicConfig(
    level=logging.DEBUG,
    format="%(module)s.%(funcName)s [%(levelname)s] - %(message)s",
    handlers=_handlers,
)
_LOGGER: logging.Logger = logging.getLogger(__name__)
DEBUG = False

# List of supported commands (ref. RFC-9271):
#   USERNAME and PASSWORD are not in this list as login is part of the class.__init__
#   ATTACH and DETACH are not supported because this is a monitor only.
#   FSD is not supported for security reasons.
SUPPORTED: dict[str, list[str]] = {
    "commands": ["VER", "HELP", "LOGOUT", "LIST", "PROTVER", "GET"],
    # For the following commands the listed sub-commands are supported.
    # A `%u` is used to indicate that an additional parameter is required.
    "LIST": ["CLIENT %u", "CMD %u", "RW %u", "UPS", "VAR %u"],
    "GET": ["CMDDESC %u", "DESC %u", "NUMATTACH %u", "NUMLOGINS %u", "UPSDESC %u"],
}
TIMEOUT: int = 2


class PyNUT3Error(Exception):
    """Base class for custom exceptions."""


class PyNUT3Client:
    """Access NUT (Network UPS Tools) servers.

    Attributes:
        valid_commands: (list) commands that the server accepts.
        devices: (dict) containing, per device, all data and supported instant commands.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3493,
        login: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = TIMEOUT,
        persistent: bool = True,
        descriptors: bool = False,
        debug: bool = DEBUG,
    ) -> None:
        """Class initialization method.

        Args:
            host: Host to connect (default: 127.0.0.1).
            port: Port where NUT listens for connections (default: 3493).
            login: Login used to connect to NUT server (default: None for no authentication).
            password: Password used for authentication (default: None).
            timeout: Timeout used to wait for network response (default: 2 seconds).
            persistent: When True connection will be made in init method and be
            held open; When False connection is open and closed when needed (default: True).
            NOTE: setting this to True does not protect from the other end closing the connection!
            descriptors: When True will also read descriptions of commands and variables
            from the device(s) (default: False as it is time-consuming).
            debug: When True put class in debug mode and print stuff on console (default: False).
        """
        _LOGGER.debug(f"NUT Class initialization on: {host}:{port}, Login: {login} started.")

        self._debug: bool = debug
        self._host: str = host
        self._port: int = port
        self._login: Optional[str] = login
        self._password: Optional[str] = password
        self._timeout: int = timeout
        self._persistent: bool = persistent
        self.descriptors: bool = descriptors
        self._child: Optional[pexpect.spawn] = None

        if self._persistent:
            self._connect()

        # build the list of valid commands
        self.valid_commands: list[str] = ["HELP"]
        self.valid_commands = self.help()
        self.valid_commands.append("PROTVER")

        # build the list of connected NUT-capable devices
        self.devices: dict[str, Any] = self._get_devices()
        # build
        for _dev in self.devices:  # pylint: disable=consider-using-dict-items
            # get commands supported by the device
            self.devices[_dev]["commands"] = self._get_commands(_dev)  # type: ignore[assignment]
            # get all the variables the device knows about
            self.devices[_dev]["vars"] = self._get_vars(_dev, "VAR")  # type: ignore[assignment]
            # add info about the r/w variables
            for k, v in self._get_vars(_dev, "RW").items():
                self.devices[_dev]["vars"][k] = v  # type: ignore[index]
            # add variable descriptions if requested
            for k, v in self.devices[_dev]["vars"].items():  # type: ignore[attr-defined]
                if descriptors:
                    v.append(self.get_var_desc(_dev, k))
                else:
                    v.append(" ")
                self.devices[_dev]["vars"][k] = v  # type: ignore[index]
            _t: float = time.time()
            # to be able to determine the staleness of the data we record the time of the
            # last update in both a formatted string for humans...
            self.devices[_dev]["timestamp"] = time.strftime(
                "%Y-%m-%d %H:%M %Z", time.localtime(_t)
            )
            # ... and a UN*X-epoch for automated checks.
            self.devices[_dev]["timestamp-x"] = str(_t)
        _LOGGER.debug(
            f"NUT Class initialization finished {time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(time.time()))}."
        )

    def __enter__(self) -> "PyNUT3Client":
        return self

    def __exit__(self, exc_t: type, exc_v: IndexError, trace: Any) -> None:
        self._disconnect()

    def _disconnect(self) -> None:
        """Disconnect from the server."""
        if self._child:
            try:
                self._write("LOGOUT\n")
                self._child.close()
            except pexpect.ExceptionPexpect:
                # the connection was already closed
                pass
        self._child = None

    def _connect(self) -> None:
        """Connects to the defined server.

        If login/password was specified, the class tries to authenticate.
        An error is raised if something goes wrong.
        """
        _result: list[str]
        try:
            self._child = pexpect.spawn(
                f"{_CALL_CMD} {self._host} {self._port}", timeout=self._timeout, echo=False
            )
            if self._login:
                # untested. If you can test this, let me know if it works.
                self._write(f"USERNAME {self._login}")
                _result = self._read()
                if "OK" not in _result:
                    raise PyNUT3Error(f"LOGIN ERROR (USERNAME) : {_result}")

            if self._password:
                # untested. If you can test this, let me know if it works.
                self._write(f"PASSWORD {self._password}")
                _result = self._read()
                if "OK" not in _result:
                    raise PyNUT3Error(f"LOGIN ERROR (PASSWORD) : {_result}")
        except Exception as exc:
            raise PyNUT3Error("Something went wrong!") from exc

    def _read(self, timeout: int = TIMEOUT) -> list[str]:
        """Collect the output from the server.

        Args:
            timeout: timeout to use in seconds

        Returns:
            output from the server as a list of strings.
        """
        _lines: list[str] = []
        if not self._child:
            raise RuntimeError("NUT3 connection has not been opened.")
        while True:
            try:
                index = self._child.expect([pexpect.EOF, "\n"], timeout)
                _lines.append(f"{self._child.before.decode('utf-8')}")
                if index == 0:
                    # Connection closed
                    _LOGGER.error(f"Connection closed by the other end.")
                    break
            except pexpect.exceptions.TIMEOUT:
                break
        return _lines

    def _write(self, wstring: str) -> None:
        """Wrapper for _child write method.

        Args:
            string: string to be sent to the server.
        """
        if self._debug:
            print(f"*** {wstring}")
        try:
            if not self._child:
                raise RuntimeError("NUT3 connection has not been opened.")
            self._child.sendline(wstring.encode("ascii"))
        except (pexpect.ExceptionPexpect, EOFError, BrokenPipeError):
            _LOGGER.error("NUT3 problem writing to server.")

    def _call(self, command: str) -> list[str]:
        if not self._persistent:
            self._connect()

        self._write(command)
        _returned_list: list[str] = self._read()

        if not self._persistent:
            self._disconnect()

        return _returned_list

    def _get_commands(self, device: str) -> dict[str, str]:
        """Return a list of commands supported by the device."""
        _list: list[str] = self.cmd(f"LIST CMD {device}")
        _dict: dict[str, str] = {}
        for _cmd in _list:
            _ret: str = " "
            if self.descriptors:
                _ret = self.cmd(f"GET CMDDESC {device} {_cmd}")[0]
            _dict[_cmd] = _ret.replace('"', "")
        return _dict

    def _get_devices(self) -> dict[str, dict[str, str]]:
        """Return a dict of devices connected to this server.

        Returns:
            dict containing device name and description.
        """
        _dict: dict[str, dict[str, str]] = {}
        _list: list[str] = self.cmd("LIST UPS")
        _ups: list[str] = []
        for _entry in _list:
            _ups = shlex.split(_entry)
            _dict[_ups[0]] = {"description": _ups[1]}
        return _dict

    def _get_vars(self, device: str, sub: str) -> dict[str, list[str]]:
        """Return a dict of variables and their current values.

        Returns:
            dict containing variable name and current value.
        """
        _type: str = "r-"
        if sub == "RW":
            _type = "rw"
        _dict: dict[str, list[str]] = {}
        _list: list[str] = self.cmd(f"LIST {sub} {device}")
        for _kv in _list:
            _kl: list[str] = shlex.split(_kv)
            _k: str = _kl[0]
            _v: str = _kl[1].replace('"', "")
            _dict[_k] = [_v, _type]
        return _dict

    def cmd(self, command: str) -> list[str]:
        """Execute a valid supported command on the server and return anything that gets returned.

        Args:
            command: command to be sent

        Returns:
            sanitized output from command
        """
        if self._debug:
            _LOGGER.debug(f"NUT3 {command} requested on '{self._host}'")
            print(f">> .{command}.")
        splt_cmd: list[str] = command.split(" ")
        main_cmd: str = splt_cmd[0]
        try:
            sub_cmd: str = splt_cmd[1]
        except IndexError:
            sub_cmd = ""
        try:
            par_cmd: str = splt_cmd[2]
        except IndexError:
            par_cmd = ""

        ignored_response = " ".join(command.split(" ")[1:])
        if not ignored_response:
            ignored_response = f"{sub_cmd} {par_cmd} "

        if self._debug:
            print(f">> ignoring : .{ignored_response}.")

        if main_cmd not in self.valid_commands:
            # unknown command
            if self._debug:
                print(f"Valid commands: {self.valid_commands}")
            raise PyNUT3Error(f"{main_cmd} is not supported by the server.")

        if main_cmd not in SUPPORTED["commands"]:
            # unsupported command
            if self._debug:
                print(f"Supported commands: {SUPPORTED['commands']}")
            raise PyNUT3Error(f"'{main_cmd}' is not supported by pynut3.")
        if (sub_cmd and not par_cmd) and sub_cmd not in SUPPORTED[main_cmd]:
            # unsupported sub-command
            # OR sub-command without required parameter
            if self._debug:
                print(f"Supported sub-commands for {main_cmd}: {SUPPORTED[main_cmd]}")
            raise PyNUT3Error(f"'{main_cmd} {sub_cmd}' is not supported by pynut3.")
        if (sub_cmd and par_cmd) and f"{sub_cmd} %u" not in SUPPORTED[main_cmd]:
            # sub-command does not have a parameter, but parameter was passed
            raise PyNUT3Error(f"'{main_cmd} {sub_cmd} {par_cmd}' is not supported by pynut3.")

        _returned_list: list[str] = self._call(command)
        if self._debug:
            print(f">> returned : {_returned_list}")

        _mod_list: list[str] = []
        _s: str
        # _begun: bool = False
        for _s in _returned_list:
            _s = _s.replace("\r", "")
            _s = _s.replace(f"{command}", "")
            _s = _s.replace(f"{ignored_response} ", "", 1)
            if "BEGIN" == _s.split(" ")[0]:
                # _begun = True
                _s = ""
                # Throw away everything that came before
                _mod_list = []
            # if _begun or main_cmd in ["HELP", "VER", "PROTVER"]:
            if "END" == _s.split(" ")[0]:
                _s = ""
            if _s:
                _mod_list.append(_s)
        if self._debug:
            print(f">> result   : {_mod_list}")
            print()
        return _mod_list

    def get_var_desc(self, device: str, variable: str) -> str:
        """Request the description of variable from device.

        Args:
            device: name of the device
            variable: name of the variable

        Returns:
            description of the variable, if known by the device.
        """
        _desc: str = self.cmd(f"GET DESC {device} {variable}")[0].replace('"', "")
        return _desc

    def help(self) -> list[str]:
        """Execute HELP command.

        Returns:
            list of commands supported by the server.
        """
        result: str = self.cmd("HELP")[-1]
        if self._debug:
            print(f"HELP result : {result}")
        valid_commands: list[str] = result.split()[1:]
        if self._debug:
            print(f"HELP valid  : {valid_commands}")
        return valid_commands

    def update(self, device: str) -> None:
        """Update the values of the variables for the given device.

        Args:
            device: name of the device

        Returns:
            Nothing. Instead, calling this will update the values
            in PyNUT3Client.device_state[device]
        """
        _k: str
        _v: list[str]
        for _k, _v in self._get_vars(device, "VAR").items():
            self.devices[device]["vars"][_k][0] = _v[0]
        _t = time.time()
        # update the timestamps
        self.devices[device]["timestamp"] = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(_t))
        self.devices[device]["timestamp-x"] = str(_t)

    def update_all(self) -> None:
        """Update the values of all the variables for all devices.

        Returns:
            Nothing. Instead, calling this will update the values in
            PyNUT3Client.device_state for all devices.
        """

        _dev: str
        for _dev in self.devices:
            self.update(_dev)

    def version(self) -> str:
        """Execute VER and PROTVER command.

        Returns:
            combined version string
        """
        return " - protocol ".join([self.cmd("VER")[0], self.cmd("PROTVER")[0]])


if __name__ == "__main__":
    print("Must be imported to use.")
    client = PyNUT3Client(host="192.168.2.17", debug=True)

    # client.version returns a string cnontaining the version of the server
    print(client.version())
    print()

    # def list_enum(self, ups: str, var: str) -> List[str]:
    #     """Get a list of valid values for an enum variable.

    #     The result is presented as a list.
    #     """
    #     _LOGGER.debug(f"NUT3 requesting list_enum from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"LIST ENUM {ups} {var}\n")
    #     result: str = self._read("\n")
    #     if result != f"BEGIN LIST ENUM {ups} {var}\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     result = self._read(f"END LIST ENUM {ups} {var}\n")
    #     offset: int = len(f"ENUM {ups} {var}")
    #     end_offset: int = 0 - (len(f"END LIST ENUM {ups} {var}\n") + 1)

    #     if not self._persistent:
    #         self._disconnect()

    #     try:
    #         return [
    #             c[offset:].split('"')[1].strip()
    #             for c in result[:end_offset].split("\n")
    #             if '"' in c[offset:]
    #         ]
    #     except IndexError as exc:
    #         raise PyNUT3Error(result.replace("\n", "")) from exc

    # def list_range(self, ups: str, var: str) -> List[str]:
    #     """Get a list of valid values for an range variable.

    #     The result is presented as a list.
    #     """
    #     _LOGGER.debug(f"NUT3 requesting list_range from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"LIST RANGE {ups} {var}\n")
    #     result: str = self._read("\n")
    #     if result != f"BEGIN LIST RANGE {ups} {var}\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     result = self._read(f"END LIST RANGE {ups} {var}\n")
    #     offset: int = len(f"RANGE {ups} {var}")
    #     end_offset: int = 0 - (len(f"END LIST RANGE {ups} {var}\n") + 1)

    #     if not self._persistent:
    #         self._disconnect()

    #     try:
    #         return [
    #             c[offset:].split('"')[1].strip()
    #             for c in result[:end_offset].split("\n")
    #             if '"' in c[offset:]
    #         ]
    #     except IndexError as exc:
    #         raise PyNUT3Error(result.replace("\n", "")) from exc

    # def set_var(self, ups: str, var: str, value: str) -> None:
    #     """Set a variable to the specified value on selected UPS.

    #     The variable must be a writable value (cf list_rw_vars) and you
    #     must have the proper rights to set it (maybe login/password).
    #     """
    #     _LOGGER.debug(f"NUT3 setting set_var '{var}' on '{self._host}' to '{value}'")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"SET VAR {ups} {var} {value}\n")
    #     result = self._read("\n")

    #     if result != "OK\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     if not self._persistent:
    #         self._disconnect()

    # def var_type(self, ups: str, var: str) -> str:
    #     """Get a variable's type."""
    #     _LOGGER.debug(f"NUT3 requesting var_type '{var}' on '{self._host}'.")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"GET TYPE {ups} {var}\n")
    #     result: str = self._read("\n")

    #     if not self._persistent:
    #         self._disconnect()

    #     type_: str = " ".join(result.split(" ")[3:]).strip()
    #     result_ = result.replace("\n", "")
    #     # Ensure the response was valid.
    #     if len(type_) == 0:
    #         raise PyNUT3Error(f"No TYPE returned: {result_}")
    #     if not result.startswith("TYPE"):
    #         raise PyNUT3Error(f"Unexpected response: {result_}")

    #     return type_

    # def run_command(self, ups: str, command: str) -> None:
    #     """Send a command to the specified UPS."""
    #     _LOGGER.debug(f"NUT3 run_command called '{command}' on '{self._host}'.")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"INSTCMD {ups} {command}\n")
    #     result: str = self._read("\n")

    #     if result != "OK\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     if not self._persistent:
    #         self._disconnect()

    # def num_logins(self, ups: str) -> int:
    #     """Send GET NUMLOGINS command to get the number of users logged into a given UPS."""

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"GET NUMLOGINS {ups}\n")
    #     result: str = self._read("\n")

    #     if not self._persistent:
    #         self._disconnect()

    #     try:
    #         return int(result.split(" ")[2].strip())
    #     except (ValueError, IndexError) as exc:
    #         raise PyNUT3Error(result.replace("\n", "")) from exc
