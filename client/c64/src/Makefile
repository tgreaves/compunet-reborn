# Compunet Reborn — Build System
# Usage: make (from this directory)
# Output: ../compunet-reborn.prg (combined PRG)
#   LOAD "COMPUNET",8,1 : SYS 33184

CA65 = ca65
LD65 = ld65
PYTHON = python3

PRG = ../compunet-reborn.prg
ROM_BIN = build/rom.bin
TERM_BIN = build/terminal.bin
ACIA_BIN = build/acia.bin
ROM_OBJ = build/compunet_rom.o
TERM_OBJ = build/terminal.o
ACIA_OBJ = build/acia_driver.o
ROM_SRC = compunet_rom.s
TERM_SRC = terminal.s
ACIA_SRC = acia_driver.s

.PHONY: all clean

all: $(PRG)

$(PRG): $(ROM_BIN) $(TERM_BIN) $(ACIA_BIN)
	$(PYTHON) make_prg.py $(ROM_BIN) $(TERM_BIN) $(ACIA_BIN) $(PRG)

$(ROM_BIN): $(ROM_OBJ) cartridge.cfg
	$(LD65) -C cartridge.cfg $(ROM_OBJ) -o $(ROM_BIN)

$(TERM_BIN): $(TERM_OBJ) terminal.cfg
	$(LD65) -C terminal.cfg $(TERM_OBJ) -o $(TERM_BIN)

$(ACIA_BIN): $(ACIA_OBJ) acia_driver.cfg
	$(LD65) -C acia_driver.cfg $(ACIA_OBJ) -o $(ACIA_BIN)

$(ROM_OBJ): $(ROM_SRC) | build
	$(CA65) -t c64 $(ROM_SRC) -o $(ROM_OBJ)

$(TERM_OBJ): $(TERM_SRC) | build
	$(CA65) -t c64 $(TERM_SRC) -o $(TERM_OBJ)

$(ACIA_OBJ): $(ACIA_SRC) | build
	$(CA65) -t c64 $(ACIA_SRC) -o $(ACIA_OBJ)

build:
	mkdir -p build

clean:
	rm -rf build $(PRG)
