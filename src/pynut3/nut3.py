#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A Python3 module for dealing with NUT (Network UPS Tools) servers.

* PyNUT3Error: Base class for custom exceptions.
* PyNUT3Client: Allows connecting to and communicating with PyNUT servers.

Copyright (C) 2013 george2

Modifications by mezz64 - 2016
Modifications by Mausy5043 - 2022

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

import logging
import socket

from telnetlib import Telnet
from typing import Any, Dict, List, Optional

__version__ = '1.1.1'
__all__ = ['PyNUT3Error', 'PyNUT3Client']

_LOGGER = logging.getLogger(__name__)


class PyNUT3Error(Exception):
    """Base class for custom exceptions.
    """


class PyNUT3Client:
    """Access NUT (Network UPS Tools) servers."""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, host: str = '127.0.0.1', port: int = 3493,
                 login: Optional[str] = None, password: Optional[str] = None,
                 timeout: float = 5, persistent: bool = True,
                 debug: bool = True) -> None:
        """Class initialization method.

        host        : Host to connect (defaults to 127.0.0.1).
        port        : Port where NUT listens for connections (defaults to 3493)
        login       : Login used to connect to NUT server (defaults to None
                        for no authentication).
        password    : Password used for authentication (defaults to None).
        timeout     : Timeout used to wait for network response (defaults
                        to 5 seconds).
        persistent  : Boolean, when true connection will be made in init method
                        and be held open, when false connection is open/closed
                        when calling each method
        debug       : Boolean, put class in debug mode (prints everything
                        on console, defaults to False).
        """
        _LOGGER.debug(f'NUT Class initialization, Host/Port: {host}:{port}, Login: {login}')

        self._debug = debug
        self._host: str = host
        self._port: int = port
        self._login: Optional[str] = login
        self._password: Optional[str] = password
        self._timeout: float = timeout
        self._persistent: bool = persistent
        self._srv_handler: Optional[Telnet] = None

        if self._persistent:
            self._connect()

    def __del__(self) -> None:
        """Try to disconnect cleanly when class is deleted."""
        _LOGGER.debug('NUT Class deleted, trying to disconnect.')
        self._disconnect()

    def __enter__(self) -> 'PyNUT3Client':
        return self

    def __exit__(self, exc_t: type, exc_v: IndexError, trace: Any) -> None:
        self.__del__()

    def _disconnect(self) -> None:
        """ Disconnects from the defined server."""
        if self._srv_handler:
            try:
                self._write('LOGOUT\n')
                self._srv_handler.close()
            except (socket.error, AttributeError):
                # The socket is already disconnected.
                pass

    def _connect(self) -> None:
        """Connects to the defined server.

        If login/pass was specified, the class tries to authenticate.
        An error is raised if something goes wrong.
        """
        try:
            self._srv_handler = Telnet(self._host, self._port, timeout=self._timeout)

            result: str
            if self._login is not None:
                self._write(f'USERNAME {self._login}\n')
                result = self._read_until('\n')
                if result != 'OK\n':
                    raise PyNUT3Error(result.replace('\n', ''))

            if self._password is not None:
                self._write(f'PASSWORD {self._password}\n')
                result = self._read_until('\n')
                if result != 'OK\n':
                    raise PyNUT3Error(result.replace('\n', ''))
        except socket.error as exc:
            raise PyNUT3Error('Socket error.') from exc

    def _read_until(self, string: str) -> str:
        """ Wrapper for _srv_handler read_until method."""
        try:
            if self._srv_handler is None:
                raise RuntimeError('NUT3 connection has not been opened.')
            return self._srv_handler.read_until(string.encode('ascii'), self._timeout).decode()
        except (EOFError, BrokenPipeError):
            _LOGGER.error('NUT3 problem reading from server.')
            return ''

    def _write(self, string: str) -> None:
        """ Wrapper for _srv_handler write method."""
        try:
            if self._srv_handler is None:
                raise RuntimeError('NUT3 connection has not been opened.')
            self._srv_handler.write(string.encode('ascii'))
            return
        except (EOFError, BrokenPipeError):
            _LOGGER.error('NUT3 problem writing to server.')

    def description(self, ups: str) -> str:
        """Returns the description for a given UPS."""
        _LOGGER.debug(f'NUT3 requesting description from server {self._host}')

        if not self._persistent:
            self._connect()

        self._write(f'GET UPSDESC {ups}\n')
        result: str = self._read_until('\n')

        if not self._persistent:
            self._disconnect()

        try:
            return result.split('"')[1].strip()
        except IndexError as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    def get_dict_ups(self) -> Dict[str, str]:
        """Returns the list of available UPS from the NUT server.

        The result is a dictionary containing 'key->val' pairs of
        'UPSName' and 'UPS Description'.
        """
        _LOGGER.debug(f'NUT3 requesting list_ups from server {self._host}')

        if not self._persistent:
            self._connect()

        self._write('LIST UPS\n')
        result: str = self._read_until('\n')
        if result != 'BEGIN LIST UPS\n':
            raise PyNUT3Error(result.replace('\n', ''))

        result = self._read_until('END LIST UPS\n')

        ups_dict: Dict[str, str] = {}
        line: str
        for line in result.split('\n'):
            if line.startswith('UPS'):
                line = line[len('UPS '):-len('"')]
                if '"' not in line:
                    continue
                ups: str
                desc: str
                ups, desc = line.split('"')[:2]
                ups_dict[ups.strip()] = desc.strip()

        if not self._persistent:
            self._disconnect()

        return ups_dict

    def get_dict_vars(self, ups: str) -> Dict[str, str]:
        """Get all available vars from the specified UPS.

        The result is a dictionary containing 'key->val' pairs of all
        available vars.
        """
        _LOGGER.debug(f"NUT3 requesting list_vars from server {self._host}")

        if not self._persistent:
            self._connect()

        self._write(f'LIST VAR {ups}\n')
        result: str = self._read_until('\n')
        if result != f'BEGIN LIST VAR {ups}\n':
            raise PyNUT3Error(result.replace('\n', ''))

        result = self._read_until(f'END LIST VAR {ups}\n')
        offset: int = len(f'VAR {ups} ')
        end_offset: int = 0 - (len(f'END LIST VAR {ups}\n') + 1)

        ups_vars: Dict[str, str] = {}
        current: str
        for current in result[:end_offset].split('\n'):
            current = current[offset:]
            if '"' not in current:
                continue
            var: str
            data: str
            var, data = current.split('"')[:2]
            ups_vars[var.strip()] = data

        if not self._persistent:
            self._disconnect()

        return ups_vars

    def get_dict_commands(self, ups: str) -> Dict[str, str]:
        """Get all available commands for the specified UPS.

        The result is a dict object with command name as key and a description
        of the command as value.
        """
        _LOGGER.debug(f"NUT3 requesting list_commands from server {self._host}")

        if not self._persistent:
            self._connect()

        self._write(f'LIST CMD {ups}\n')
        result: str = self._read_until('\n')
        if result != f'BEGIN LIST CMD {ups}\n':
            raise PyNUT3Error(result.replace('\n', ''))

        result = self._read_until(f'END LIST CMD {ups}\n')
        offset: int = len(f'CMD {ups} ')
        end_offset: int = 0 - (len(f'END LIST CMD {ups}\n') + 1)

        commands: Dict[str, str] = {}
        current: str
        for current in result[:end_offset].split('\n'):
            command: str = current[offset:].split('"')[0].strip()

            # For each var we try to get the available description
            try:
                self._write(f'GET CMDDESC {ups} {command}\n')
                temp: str = self._read_until('\n')
                if temp.startswith('CMDDESC'):
                    desc_offset = len(f'CMDDESC {ups} {command} ')
                    temp = temp[desc_offset:-1]
                    if '"' not in temp:
                        continue
                    commands[command] = temp.split('"')[1]
                else:
                    commands[command] = command
            except IndexError:
                commands[command] = command

        if not self._persistent:
            self._disconnect()

        return commands

    def get_dict_clients(self, ups: str = '') -> Dict[str, List[str]]:
        """Returns the list of connected clients from the NUT server.

        The result is a dictionary containing 'key->val' pairs of
        'UPSName' and a list of clients.
        """
        _LOGGER.debug(f"NUT3 requesting list_clients from server {self._host}")

        if not self._persistent:
            self._connect()

        if ups and (ups not in self.get_dict_ups()):
            raise PyNUT3Error(f'{ups} is not a valid UPS')

        if ups:
            self._write(f'LIST CLIENTS {ups}\n')
        else:
            self._write('LIST CLIENTS\n')
        result = self._read_until('\n')
        if result != 'BEGIN LIST CLIENTS\n':
            raise PyNUT3Error(result.replace('\n', ''))

        result = self._read_until('END LIST CLIENTS\n')

        clients: Dict[str, List[str]] = {}
        line: str
        for line in result.split('\n'):
            if line.startswith('CLIENT') and ' ' in line[len('CLIENT '):]:
                line = line[len('CLIENT '):]
                if ' ' not in line:
                    continue
                host: str
                host, ups = line.split(' ')[:2]
                if ups not in clients:
                    clients[ups] = []
                clients[ups].append(host)

        if not self._persistent:
            self._disconnect()

        return clients

    def get_dict_rw_vars(self, ups: str) -> Dict[str, str]:
        """Get a list of all writable vars from the selected UPS.

        The result is presented as a dictionary containing 'key->val'
        pairs.
        """
        _LOGGER.debug(f"NUT3 requesting list_rw_vars from server {self._host}")

        if not self._persistent:
            self._connect()

        self._write(f'LIST RW {ups}\n')
        result: str = self._read_until('\n')
        if result != f'BEGIN LIST RW {ups}\n':
            raise PyNUT3Error(result.replace('\n', ''))

        result = self._read_until(f'END LIST RW {ups}\n')
        offset: int = len(f'VAR {ups}')
        end_offset: int = 0 - (len(f'END LIST RW {ups}\n') + 1)

        rw_vars: Dict[str, str] = {}
        for current in result[:end_offset].split('\n'):
            current = current[offset:]
            if '"' not in current:
                continue
            var: str
            data: str
            var, data = current.split('"')[:2]
            rw_vars[var.strip()] = data

        if not self._persistent:
            self._disconnect()

        return rw_vars

    def list_enum(self, ups: str, var: str) -> List[str]:
        """Get a list of valid values for an enum variable.

        The result is presented as a list.
        """
        _LOGGER.debug(f"NUT3 requesting list_enum from server {self._host}")

        if not self._persistent:
            self._connect()

        self._write(f'LIST ENUM {ups} {var}\n')
        result: str = self._read_until('\n')
        if result != f'BEGIN LIST ENUM {ups} {var}\n':
            raise PyNUT3Error(result.replace('\n', ''))

        result = self._read_until(f'END LIST ENUM {ups} {var}\n')
        offset: int = len(f'ENUM {ups} {var}')
        end_offset: int = 0 - (len(f'END LIST ENUM {ups} {var}\n') + 1)

        if not self._persistent:
            self._disconnect()

        try:
            return [c[offset:].split('"')[1].strip()
                    for c in result[:end_offset].split('\n')
                    if '"' in c[offset:]]
        except IndexError as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    def list_range(self, ups: str, var: str) -> List[str]:
        """Get a list of valid values for an range variable.

        The result is presented as a list.
        """
        _LOGGER.debug(f"NUT3 requesting list_range from server {self._host}")

        if not self._persistent:
            self._connect()

        self._write(f'LIST RANGE {ups} {var}\n')
        result: str = self._read_until('\n')
        if result != f'BEGIN LIST RANGE {ups} {var}\n':
            raise PyNUT3Error(result.replace('\n', ''))

        result = self._read_until(f'END LIST RANGE {ups} {var}\n')
        offset: int = len(f'RANGE {ups} {var}')
        end_offset: int = 0 - (len(f'END LIST RANGE {ups} {var}\n') + 1)

        if not self._persistent:
            self._disconnect()

        try:
            return [c[offset:].split('"')[1].strip()
                    for c in result[:end_offset].split('\n')
                    if '"' in c[offset:]]
        except IndexError as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    def set_var(self, ups: str, var: str, value: str) -> None:
        """Set a variable to the specified value on selected UPS.

        The variable must be a writable value (cf list_rw_vars) and you
        must have the proper rights to set it (maybe login/password).
        """
        _LOGGER.debug(f"NUT3 setting set_var '{var}' on '{self._host}' to '{value}'")

        if not self._persistent:
            self._connect()

        self._write(f'SET VAR {ups} {var} {value}\n')
        result = self._read_until('\n')

        if result != 'OK\n':
            raise PyNUT3Error(result.replace('\n', ''))

        if not self._persistent:
            self._disconnect()

    def get_var(self, ups: str, var: str) -> str:
        """Get the value of a variable."""
        _LOGGER.debug(f"NUT3 requesting get_var '{var}' on '{self._host}'.")

        if not self._persistent:
            self._connect()

        self._write(f'GET VAR {ups} {var}\n')
        result = self._read_until('\n')

        if not self._persistent:
            self._disconnect()

        try:
            return result.split('"')[1].strip()
        except IndexError as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    # Alias for convenience
    def get(self, ups: str, var: str) -> str:
        """Get the value of a variable (alias for get_var)."""
        return self.get_var(ups, var)

    def var_description(self, ups: str, var: str) -> str:
        """Get a variable's description."""
        _LOGGER.debug(f"NUT3 requesting var_description '{var}' on '{self._host}'.")

        if not self._persistent:
            self._connect()

        self._write(f'GET DESC {ups} {var}\n')
        result = self._read_until('\n')

        if not self._persistent:
            self._disconnect()

        try:
            return result.split('"')[1].strip()
        except IndexError as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    def var_type(self, ups: str, var: str) -> str:
        """Get a variable's type."""
        _LOGGER.debug(f"NUT3 requesting var_type '{var}' on '{self._host}'.")

        if not self._persistent:
            self._connect()

        self._write(f'GET TYPE {ups} {var}\n')
        result: str = self._read_until('\n')

        if not self._persistent:
            self._disconnect()

        try:
            type_: str = ' '.join(result.split(' ')[3:]).strip()
            # Ensure the response was valid.
            assert len(type_) > 0
            assert result.startswith('TYPE')
            return type_
        except AssertionError as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    def command_description(self, ups: str, command: str) -> str:
        """Get a command's description."""
        _LOGGER.debug(f"NUT3 requesting command_description '{command}' on '{self._host}'.")

        if not self._persistent:
            self._connect()

        self._write(f'GET CMDDESC {ups} {command}\n')
        result: str = self._read_until('\n')

        if not self._persistent:
            self._disconnect()

        try:
            return result.split('"')[1].strip()
        except IndexError as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    def run_command(self, ups: str, command: str) -> None:
        """Send a command to the specified UPS."""
        _LOGGER.debug(f"NUT3 run_command called '{command}' on '{self._host}'.")

        if not self._persistent:
            self._connect()

        self._write(f'INSTCMD {ups} {command}\n')
        result: str = self._read_until('\n')

        if result != 'OK\n':
            raise PyNUT3Error(result.replace('\n', ''))

        if not self._persistent:
            self._disconnect()

    def fsd(self, ups: str) -> None:
        """Send MASTER and Forced ShutDown (FSD) commands."""
        _LOGGER.debug("NUT3 MASTER called on '{self._host}'.")

        if not self._persistent:
            self._connect()

        self._write(f'MASTER {ups}\n')
        result: str = self._read_until('\n')
        if result != 'OK MASTER-GRANTED\n':
            raise PyNUT3Error(('Master level functions are not available', ''))

        _LOGGER.debug('FSD called...')
        self._write(f'FSD {ups}\n')
        result = self._read_until('\n')
        if result != 'OK FSD-SET\n':
            raise PyNUT3Error(result.replace('\n', ''))

        if not self._persistent:
            self._disconnect()

    def num_logins(self, ups: str) -> int:
        """Send GET NUMLOGINS command to get the number of users logged
        into a given UPS.
        """
        _LOGGER.debug(f"NUT3 requesting num_logins called on '{self._host}'")

        if not self._persistent:
            self._connect()

        self._write(f'GET NUMLOGINS {ups}\n')
        result: str = self._read_until('\n')

        if not self._persistent:
            self._disconnect()

        try:
            return int(result.split(' ')[2].strip())
        except (ValueError, IndexError) as exc:
            raise PyNUT3Error(result.replace('\n', '')) from exc

    def help(self) -> str:
        """Send HELP command."""
        _LOGGER.debug(f"NUT3 HELP called on '{self._host}'")

        if not self._persistent:
            self._connect()

        self._write('HELP\n')

        if not self._persistent:
            self._disconnect()

        return self._read_until('\n')

    def ver(self) -> str:
        """Send VER command."""
        _LOGGER.debug(f"NUT3 VER called on '{self._host}'")

        if not self._persistent:
            self._connect()

        self._write('VER\n')

        if not self._persistent:
            self._disconnect()

        return self._read_until('\n')
