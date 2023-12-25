#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A Python3 module for communicating with NUT (Network UPS Tools) servers.

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
DEBUG = True

# list of supported commands (ref. RFC-9271)
# USERNAME and PASSWORD are not in this list as login is part of the class.__init__
SUPPORTED: dict[str, list[str]] = {"commands": ["VER", "HELP", "LOGOUT", "LIST", "PROTVER"],
                                   # For the following commands the listed sub-commands are supported.
                                   # A `%` is used to indicate that an additional parameter is required.
                                   "LIST": ["CLIENT %", "CMD %", "RW %", "UPS", "VAR %"],
                       }
TIMEOUT: int = 2


class PyNUT3Error(Exception):
    """Base class for custom exceptions."""


class PyNUT3Client:
    """Access NUT (Network UPS Tools) servers."""

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3493,
        login: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = TIMEOUT,
        persistent: bool = True,
        debug: bool = True,
    ) -> None:
        """Class initialization method.

        host        : Host to connect (defaults to 127.0.0.1).
        port        : Port where NUT listens for connections (defaults to 3493)
        login       : Login used to connect to NUT server (defaults to None
                        for no authentication).
        password    : Password used for authentication (defaults to None).
        timeout     : Timeout used to wait for network response (defaults
                        to 2 seconds).
        persistent  : Boolean, when true connection will be made in init method
                        and be held open, when false connection is open/closed
                        when calling each method
        debug       : Boolean, put class in debug mode (prints everything
                        on console, defaults to False).
        """
        _LOGGER.debug(f"NUT Class initialization on: {host}:{port}, Login: {login}")

        self._debug: bool = debug
        self._host: str = host
        self._port: int = port
        self._login: Optional[str] = login
        self._password: Optional[str] = password
        self._timeout: int = timeout
        self._persistent: bool = persistent
        self._child: Optional[pexpect.spawn] = None


        if self._persistent:
            self._connect()

        # build the list of valid commands
        self.valid_commands: list[str] = ["HELP"]
        self.valid_commands = self.help()
        self.valid_commands.append("PROTVER")
        self.connected_devices: dict[str, str] = self._get_devices()
        self.devices: dict= {}
        for dev in self.connected_devices:
            self.devices[dev]: dict= {}
            print(dev)
            self.devices[dev]['commands'] = self._get_commands(dev)
            self.devices[dev]['vars'] = self._get_vars(dev, 'VAR')  # r
            self.devices[dev]['rw'] = self._get_vars(dev, 'RW')  # w

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
                self._child.expect([pexpect.EOF, "\n"], timeout)
                _lines.append(f"{self._child.before.decode('utf-8')}")
            except pexpect.exceptions.TIMEOUT:
                break
        return _lines

    def _write(self, string: str) -> None:
        """Wrapper for _child write method.

        Args:
            string: string to be sent to the server.
        """
        if DEBUG:
            print("***",string)
        try:
            if not self._child:
                raise RuntimeError("NUT3 connection has not been opened.")
            self._child.sendline(string.encode("ascii"))
        except (pexpect.ExceptionPexpect, EOFError, BrokenPipeError):
            _LOGGER.error("NUT3 problem writing to server.")

    def cmd(self, command: str) -> list[str]:
        """Execute a valid supported command and return anything that gets returned.

        Args:
            command: command to be sent

        Returns:
            sanitized output from command
        """
        if DEBUG:
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

        if main_cmd not in self.valid_commands:
            # unknown command
            raise PyNUT3Error(f"{main_cmd} is not supported by the server.")

        if main_cmd not in SUPPORTED["commands"]:
            # unsupported command
            raise PyNUT3Error(f"'{main_cmd}' is not supported by pynut3.")
        if (sub_cmd and not par_cmd) and sub_cmd not in SUPPORTED[main_cmd]:
            # unsupported sub-command
            # OR sub-command without required parameter
            raise PyNUT3Error(f"'{main_cmd} {sub_cmd}' is not supported by pynut3.")
        if (sub_cmd and par_cmd) and f"{sub_cmd} %" not in SUPPORTED[main_cmd]:
            # sub-command does not have a parameter, but parameter was passed
            raise PyNUT3Error(f"'{main_cmd} {sub_cmd} {par_cmd}' is not supported by pynut3.")

        if not self._persistent:
            self._connect()

        self._write(command)
        _returned_list: list[str] = self._read()

        if not self._persistent:
            self._disconnect()

        _mod_list: list[str] = []
        _s: str
        for _s in _returned_list:
            if "BEGIN" == _s.split(" ")[0]:
                _s = ""
            if "END" == _s.split(" ")[0]:
                _s = ""
            if _s:
                _s = _s.replace(f"{sub_cmd} {par_cmd} ", "")
            if _s:
                _mod_list.append(_s.replace("\r", ""))
        return _mod_list

    def _get_commands(self, device: str) -> dict[str, list[str]]:
        """Return a list of commands supported by the device."""
        _dict: dict[str, list[str]]  = {}
        _list = self.cmd(f"LIST CMD {device}")
        return _list

    def _get_devices(self) -> dict[str, str]:
        """Return a dict of devices connected to this server.

        Returns:
            dict containing device name and description.
        """
        _dict: dict[str, str] = {}
        _list: list[str]= self.cmd("LIST UPS")
        _ups: list[str] = []
        for _entry in _list:
            _ups = shlex.split(_entry)
            _dict[_ups[1]] = _ups[2]
        return _dict

    def _get_vars(self, device: str, sub: str) -> dict[str,str]:
        """Return a dict of variables and their current values.

        Returns:
            dict containing variable name and current value.
        """
        _type = "r-"
        if sub == "RW":
            _type = "rw"
        _dict: dict[str, str] = {}
        _list: list[str]= self.cmd(f"LIST {sub} {device}")
        for _kv in _list:
            _kv: list[str] = shlex.split(_kv)
            _k: str = _kv[0]
            _v: str = _kv[1].replace('\"', '')
            _dict[_k] = [_v, _type]
        return _dict

    def update(self, device) -> None:
        for k,v in self._get_vars(device, 'VAR').items():
            self.devices[device]['vars'][k][0] = v[0]

    # def device_vars(self):
    #     return self._get_vars()

    def help(self) -> list[str]:
        """Execute HELP command.

        Returns:
            list of commands supported by the stack.
        """
        result: list[str] = self.cmd("HELP")
        valid_commands: list[str] = result[0].split()[1:]
        return valid_commands

    def ver(self) -> str:
        """Execute VER and PROTVER command.

        Returns:
            combined version string
        """
        return " - protocol ".join([self.cmd("VER")[0], self.cmd("PROTVER")[0]])



if __name__ == "__main__":
    client = PyNUT3Client(host="192.168.2.17")
    print(client.valid_commands)
    print("Connected Devices & Available Commands:")
    for dev in client.connected_devices:
        print(f"    {dev} = {client.connected_devices[dev]}")
        print("Commands")
        for num,item in enumerate(client.devices[dev]['commands']):
            print(f"        x {item}")
        print("Variables")
        for num,item in client.devices[dev]['vars'].items():
            print(f"        r {num} = {item}")
        print("Settings")
        for num,item in client.devices[dev]['rw'].items():
            print(f"        w {num} = {item}")
        #     print(f"       r--   {item}")
        # for num,item in enumerate(client.device_commands[dev]):
        #     print(f"       --x   {item}")
    # version: str = client.ver()
    # print(version)
    # helpstr: list[str] = client.help()
    # print(helpstr)


    # print(client.help())
    # ups_dict = client.get_dict_ups()
    # for k1, v1 in ups_dict.items():
    #     print(f"{v1} is called with id {k1}")
    #     vars_dict = client.get_dict_vars(k1)
    #     for k2, v2 in vars_dict.items():
    #         print(f"{k2}\t:\t{v2}")




    # def description(self, ups: str) -> str:
    #     """Returns the description for a given UPS."""
    #     _LOGGER.debug(f"NUT3 requesting description from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"GET UPSDESC {ups}\n")
    #     result: str = self._read()

    #     if not self._persistent:
    #         self._disconnect()

    #     try:
    #         return result.split('"')[1].strip()
    #     except IndexError as exc:
    #         raise PyNUT3Error(result.replace("\n", "")) from exc

    # def get_dict_ups(self) -> Dict[str, str]:
    #     """Returns the list of available UPS from the NUT server.

    #     The result is a dictionary containing 'key->val' pairs of
    #     'UPSName' and 'UPS Description'.
    #     """
    #     _LOGGER.debug(f"NUT3 requesting list_ups from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     self._write("LIST UPS\n")
    #     result: str = self._read()
    #     if result != "BEGIN LIST UPS\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     result = self._read("END LIST UPS\n")

    #     ups_dict: Dict[str, str] = {}
    #     line: str
    #     for line in result.split("\n"):
    #         if line.startswith("UPS"):
    #             line = line[len("UPS ") : -len('"')]
    #             if '"' not in line:
    #                 continue
    #             ups: str
    #             desc: str
    #             ups, desc = line.split('"')[:2]
    #             ups_dict[ups.strip()] = desc.strip()

    #     if not self._persistent:
    #         self._disconnect()

    #     return ups_dict

    # def get_dict_vars(self, ups: str) -> Dict[str, str]:
    #     """Get all available vars from the specified UPS.

    #     The result is a dictionary containing 'key: val' pairs of all
    #     available vars.
    #     """
    #     _LOGGER.debug(f"NUT3 requesting list_vars from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"LIST VAR {ups}\n")
    #     result: str = self._read("\n")
    #     if result != f"BEGIN LIST VAR {ups}\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     result = self._read(f"END LIST VAR {ups}\n")
    #     offset: int = len(f"VAR {ups} ")
    #     end_offset: int = 0 - (len(f"END LIST VAR {ups}\n") + 1)

    #     ups_vars: Dict[str, str] = {}
    #     current: str
    #     for current in result[:end_offset].split("\n"):
    #         current = current[offset:]
    #         if '"' not in current:
    #             continue
    #         var: str
    #         data: str
    #         var, data = current.split('"')[:2]
    #         ups_vars[var.strip()] = data

    #     if not self._persistent:
    #         self._disconnect()

    #     return ups_vars

    # def get_dict_commands(self, ups: str) -> Dict[str, str]:
    #     """Get all available commands for the specified UPS.

    #     The result is a dict object with command name as key and a description
    #     of the command as value.
    #     """
    #     _LOGGER.debug(f"NUT3 requesting list_commands from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"LIST CMD {ups}\n")
    #     result: str = self._read("\n")
    #     if result != f"BEGIN LIST CMD {ups}\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     result = self._read(f"END LIST CMD {ups}\n")
    #     offset: int = len(f"CMD {ups} ")
    #     end_offset: int = 0 - (len(f"END LIST CMD {ups}\n") + 1)

    #     commands: Dict[str, str] = {}
    #     current: str
    #     for current in result[:end_offset].split("\n"):
    #         command: str = current[offset:].split('"')[0].strip()

    #         # For each var we try to get the available description
    #         try:
    #             self._write(f"GET CMDDESC {ups} {command}\n")
    #             temp: str = self._read("\n")
    #             if temp.startswith("CMDDESC"):
    #                 desc_offset = len(f"CMDDESC {ups} {command} ")
    #                 temp = temp[desc_offset:-1]
    #                 if '"' not in temp:
    #                     continue
    #                 commands[command] = temp.split('"')[1]
    #             else:
    #                 commands[command] = command
    #         except IndexError:
    #             commands[command] = command

    #     if not self._persistent:
    #         self._disconnect()

    #     return commands

    # def get_dict_clients(self, ups: str = "") -> Dict[str, List[str]]:
    #     """Returns the list of connected clients from the NUT server.

    #     The result is a dictionary containing 'key->val' pairs of
    #     'UPSName' and a list of clients.
    #     """
    #     _LOGGER.debug(f"NUT3 requesting list_clients from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     if ups and (ups not in self.get_dict_ups()):
    #         raise PyNUT3Error(f"{ups} is not a valid UPS")

    #     if ups:
    #         self._write(f"LIST CLIENTS {ups}\n")
    #     else:
    #         self._write("LIST CLIENTS\n")
    #     result = self._read("\n")
    #     if result != "BEGIN LIST CLIENTS\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     result = self._read("END LIST CLIENTS\n")

    #     clients: Dict[str, List[str]] = {}
    #     line: str
    #     for line in result.split("\n"):
    #         if line.startswith("CLIENT") and " " in line[len("CLIENT ") :]:
    #             line = line[len("CLIENT ") :]
    #             if " " not in line:
    #                 continue
    #             host: str
    #             host, ups = line.split(" ")[:2]
    #             if ups not in clients:
    #                 clients[ups] = []
    #             clients[ups].append(host)

    #     if not self._persistent:
    #         self._disconnect()

    #     return clients

    # def get_dict_rw_vars(self, ups: str) -> Dict[str, str]:
    #     """Get a list of all writable vars from the selected UPS.

    #     The result is presented as a dictionary containing 'key->val'
    #     pairs.
    #     """
    #     _LOGGER.debug(f"NUT3 requesting list_rw_vars from server {self._host}")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"LIST RW {ups}\n")
    #     result: str = self._read("\n")
    #     if result != f"BEGIN LIST RW {ups}\n":
    #         raise PyNUT3Error(result.replace("\n", ""))

    #     result = self._read(f"END LIST RW {ups}\n")
    #     offset: int = len(f"VAR {ups}")
    #     end_offset: int = 0 - (len(f"END LIST RW {ups}\n") + 1)

    #     rw_vars: Dict[str, str] = {}
    #     for current in result[:end_offset].split("\n"):
    #         current = current[offset:]
    #         if '"' not in current:
    #             continue
    #         var: str
    #         data: str
    #         var, data = current.split('"')[:2]
    #         rw_vars[var.strip()] = data

    #     if not self._persistent:
    #         self._disconnect()

    #     return rw_vars

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

    # def get_var(self, ups: str, var: str) -> str:
    #     """Get the value of a variable."""
    #     _LOGGER.debug(f"NUT3 requesting get_var '{var}' on '{self._host}'.")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"GET VAR {ups} {var}\n")
    #     result: str = self._read("\n")

    #     if not self._persistent:
    #         self._disconnect()

    #     try:
    #         return result.split('"')[1].strip()
    #     except IndexError as exc:
    #         raise PyNUT3Error(result.replace("\n", "")) from exc

    # # Alias for convenience
    # def get(self, ups: str, var: str) -> str:
    #     """Get the value of a variable (alias for get_var)."""
    #     return self.get_var(ups, var)

    # def var_description(self, ups: str, var: str) -> str:
    #     """Get a variable's description."""
    #     _LOGGER.debug(f"NUT3 requesting var_description '{var}' on '{self._host}'.")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"GET DESC {ups} {var}\n")
    #     result: str = self._read("\n")

    #     if not self._persistent:
    #         self._disconnect()

    #     try:
    #         return result.split('"')[1].strip()
    #     except IndexError as exc:
    #         raise PyNUT3Error(result.replace("\n", "")) from exc

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

    # def command_description(self, ups: str, command: str) -> str:
    #     """Get a command's description."""
    #     _LOGGER.debug(f"NUT3 requesting command_description '{command}' on '{self._host}'.")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"GET CMDDESC {ups} {command}\n")
    #     result: str = self._read("\n")

    #     if not self._persistent:
    #         self._disconnect()

    #     try:
    #         return result.split('"')[1].strip()
    #     except IndexError as exc:
    #         raise PyNUT3Error(result.replace("\n", "")) from exc

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

    # def fsd(self, ups: str) -> None:
    #     """Send MASTER and Forced ShutDown (FSD) commands."""
    #     _LOGGER.debug("NUT3 MASTER called on '{self._host}'.")

    #     if not self._persistent:
    #         self._connect()

    #     self._write(f"MASTER {ups}\n")
    #     result: str = self._read("\n")
    #     if result != "OK MASTER-GRANTED\n":
    #         raise PyNUT3Error(("Master level functions are not available", ""))

    #     _LOGGER.debug("FSD called...")
    #     self._write(f"FSD {ups}\n")
    #     result = self._read("\n")
    #     if result != "OK FSD-SET\n":
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
