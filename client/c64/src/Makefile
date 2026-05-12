# Compunet Reborn — Build System
# Usage: make (from this directory)
# Output: ../compunet-reborn.prg (combined PRG)
#   LOAD "COMPUNET",8,1 : SYS 33120

CA65 = ca65
LD65 = ld65
PYTHON = python3

PRG = ../compunet-reborn.prg
ROM_BIN = build/rom.bin
TERM_BIN = build/terminal.bin
ROM_OBJ = build/compunet_rom.o
TERM_OBJ = build/terminal.o
ROM_SRC = compunet_rom.s
TERM_SRC = terminal.s

.PHONY: all clean verify

all: $(PRG) verify

$(PRG): $(ROM_BIN) $(TERM_BIN)
	$(PYTHON) make_prg.py $(ROM_BIN) $(TERM_BIN) $(PRG)

$(ROM_BIN): $(ROM_OBJ) cartridge.cfg
	$(LD65) -C cartridge.cfg $(ROM_OBJ) -o $(ROM_BIN)

$(ROM_OBJ): $(ROM_SRC) | build
	$(CA65) -t c64 $(ROM_SRC) -o $(ROM_OBJ)

$(TERM_BIN): $(TERM_OBJ) terminal.cfg
	$(LD65) -C terminal.cfg $(TERM_OBJ) -o $(TERM_BIN)

$(TERM_OBJ): $(TERM_SRC) | build
	$(CA65) -t c64 $(TERM_SRC) -o $(TERM_OBJ)

verify: $(ROM_BIN) $(TERM_BIN)
	@$(PYTHON) verify_prg.py

build:
	mkdir -p build

clean:
	rm -rf build $(PRG)
