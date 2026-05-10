# Protocol Rules

Under no circumstances should the underlying X.25 protocol be changed. The protocol command set, packet format, framing, and command bytes are fixed as documented in PROTOCOL.md and derived from the original Compunet ROM disassembly. Do not invent new protocol commands or alter existing ones.

# Behaviour Rules

The client and server must always behave like the original Compunet system. All functionality must be verified against the disassembly before implementation. Do not guess or assume behaviour — check the code first.

# Git Rules

1. Only ever commit when instructed to do so by a human.
2. On any commit, ensure README.md and PROTOCOL.md are fully up to date and reflect any changes made.
