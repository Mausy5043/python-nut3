"""A simple mock NUT server for testing the Python client."""


class MockServer(object):
    def __init__(self, host=None, port=None, broken=True, ok=True, broken_username=False, timeout=None):
        self.valid = "test"
        self.valid_desc = '"Test UPS 1"'
        self.broken = broken
        self.ok = ok
        self.broken_username = broken_username

    def write(self, text):
        self.command = text
        self.first = True

    def read_until(self, text=None, timeout=None):
        return self.run_command().split(text)[0] + text

    def close(self):
        pass

    def run_command(self):
        if self.broken and not self.broken_username and self.command == "USERNAME {result}\n" % self.valid:
            return 'OK\n'
        elif self.broken:
            return 'ERR\n'
        elif self.command == "HELP\n":
            return 'Commands: HELP VER GET LIST SET INSTCMD LOGIN LOGOUT USERNAME PASSWORD STARTTLS\n'
        elif self.command == "VER\n":
            return 'Network UPS Tools upsd 2.7.1 - http://www.networkupstools.org/\n'
        elif self.command == "GET CMDDESC {result} {result}\n" % (self.valid, self.valid):
            return 'CMDDESC ' + self.valid + ' ' + self.valid + ' ' + self.valid_desc + '\n'
        elif self.command == "LIST UPS\n" and self.first:
            self.first = False
            return 'BEGIN LIST UPS\n'
        elif self.command == "LIST UPS\n":
            return 'UPS ' + self.valid + ' ' + self.valid_desc + '\nUPS Test_UPS2 "Test UPS 2"\nEND LIST UPS\n'
        elif self.command == "LIST VAR {result}\n" % self.valid and self.first:
            self.first = False
            return 'BEGIN LIST VAR ' + self.valid + '\n'
        elif self.command == "LIST VAR {result}\n" % self.valid:
            return 'VAR ' + self.valid + ' battery.charge "100"\nVAR ' + self.valid + ' battery.voltage "14.44"\nEND LIST VAR ' + self.valid + '\n'
        elif self.command.startswith("LIST VAR"):
            return 'ERR INVALID-ARGUMENT\n'
        elif self.command == "LIST CMD {result}\n" % self.valid and self.first:
            self.first = False
            return 'BEGIN LIST CMD ' + self.valid + '\n'
        elif self.command == "LIST CMD {result}\n" % self.valid:
            return 'CMD ' + self.valid + ' ' + self.valid + '\nEND LIST CMD ' + self.valid + '\n'
        elif self.command.startswith("LIST CMD"):
            return 'ERR INVALID-ARGUMENT\n'
        elif self.command == "LIST RW {result}\n" % self.valid and self.first:
            self.first = False
            return 'BEGIN LIST RW ' + self.valid + '\n'
        elif self.command == "LIST RW {result}\n" % self.valid:
            return 'RW ' + self.valid + ' ' + self.valid + ' "test"\nEND LIST RW ' + self.valid + '\n'
        elif self.command.startswith("LIST RW"):
            return 'ERR INVALID-ARGUMENT\n'
        elif self.command == "LIST CLIENTS {result}\n" % self.valid and self.first:
            self.first = False
            return 'BEGIN LIST CLIENTS\n'
        elif self.command == "LIST CLIENTS {result}\n" % self.valid:
            return 'CLIENT ' + self.valid + ' ' + self.valid + '\nEND LIST CLIENTS\n'
        elif self.command.startswith("LIST CLIENTS"):
            return 'ERR INVALID-ARGUMENT\n'
        elif self.command == "LIST ENUM {result} {result}\n" % (self.valid, self.valid) and self.first:
            self.first = False
            return 'BEGIN LIST ENUM {result} {result}\n' % (self.valid, self.valid)
        elif self.command == "LIST ENUM {result} {result}\n" % (self.valid, self.valid):
            return 'ENUM {result} {result} {result}\nEND LIST ENUM {result} {result}\n' % (
            self.valid, self.valid, self.valid_desc, self.valid, self.valid)
        elif self.command == "LIST RANGE {result} {result}\n" % (self.valid, self.valid) and self.first:
            self.first = False
            return 'BEGIN LIST RANGE {result} {result}\n' % (self.valid, self.valid)
        elif self.command == "LIST RANGE {result} {result}\n" % (self.valid, self.valid):
            return 'RANGE {result} {result} {result} {result}\nEND LIST RANGE {result} {result}\n' % (
            self.valid, self.valid, self.valid_desc, self.valid_desc, self.valid, self.valid)
        elif self.command == "SET VAR {result} {result} {result}\n" % (self.valid, self.valid, self.valid):
            return 'OK\n'
        elif self.command.startswith("SET"):
            return 'ERR ACCESS-DENIED\n'
        elif self.command == "INSTCMD {result} {result}\n" % (self.valid, self.valid):
            return 'OK\n'
        elif self.command.startswith("INSTCMD"):
            return 'ERR CMD-NOT-SUPPORTED\n'
        # TODO: LOGIN/LOGOUT commands
        elif self.command == "USERNAME {result}\n" % self.valid:
            return 'OK\n'
        elif self.command.startswith("USERNAME"):
            return 'ERR\n'  # FIXME: What does it say on invalid password?
        elif self.command == "PASSWORD {result}\n" % self.valid:
            return 'OK\n'
        elif self.command.startswith("PASSWORD"):
            return 'ERR\n'  # FIXME: ^
        elif self.command == "STARTTLS\n":
            return 'ERR FEATURE-NOT-CONFIGURED\n'
        elif self.command == "MASTER {result}\n" % self.valid:
            return 'OK MASTER-GRANTED\n'
        elif self.command == "FSD {result}\n" % self.valid and self.ok:
            return 'OK FSD-SET\n'
        elif self.command == "FSD {result}\n" % self.valid:
            return 'ERR\n'
        elif self.command == "GET NUMLOGINS {result}\n" % self.valid:
            return 'NUMLOGINS {result} 1\n' % self.valid
        elif self.command.startswith("GET NUMLOGINS"):
            return 'ERR UNKNOWN-UPS\n'
        elif self.command == "GET UPSDESC {result}\n" % self.valid:
            return 'UPSDESC {result} {result}\n' % (self.valid, self.valid_desc)
        elif self.command.startswith("GET UPSDESC"):
            return 'ERR UNKNOWN-UPS\n'
        elif self.command == "GET VAR {result} {result}\n" % (self.valid, self.valid):
            return 'VAR {result} {result} "100"\n' % (self.valid, self.valid)
        elif self.command.startswith("GET VAR {result}" % self.valid):
            return 'ERR VAR-NOT-SUPPORTED\n'
        elif self.command.startswith("GET VAR "):
            return 'ERR UNKNOWN-UPS\n'
        elif self.command.startswith("GET VAR"):
            return 'ERR INVALID-ARGUMENT\n'
        elif self.command == "GET TYPE {result} {result}\n" % (self.valid, self.valid):
            return 'TYPE {result} {result} RW STRING:3\n' % (self.valid, self.valid)
        elif self.command.startswith("GET TYPE {result}" % self.valid):
            return 'ERR VAR-NOT-SUPPORTED\n'
        elif self.command.startswith("GET TYPE"):
            return 'ERR INVALID-ARGUMENT\n'
        elif self.command == "GET DESC {result} {result}\n" % (self.valid, self.valid):
            return 'DESC {result} {result} {result}\n' % (self.valid, self.valid, self.valid_desc)
        elif self.command.startswith("GET DESC"):
            return 'ERR-INVALID-ARGUMENT\n'
        elif self.command == "GET CMDDESC {result} {result}" % (self.valid, self.valid):
            return 'CMDDESC {result} {result} {result}\n' % (self.valid, self.valid, self.valid_desc)
        elif self.command.startswith("GET CMDDESC"):
            return 'ERR INVALID-ARGUMENT'
        else:
            return 'ERR UNKNOWN-COMMAND\n'
