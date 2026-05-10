# C64 Client

Patched Compunet ROM for use with the C64 Ultimate's 6551 ACIA modem emulation.

This will contain a modified bootstrap ROM that:
- Replaces the Compunet modem register routines with 6551 ACIA equivalents
- Replaces the dialling sequence with Hayes AT commands (ATDT<host>:<port>)
- Connects to the Compunet server over TCP via the C64 Ultimate's Telnet support
- Keeps the X.25 protocol layer and terminal software unchanged
