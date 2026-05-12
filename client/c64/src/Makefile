# Compunet Reborn — Build System
# Usage: make (from this directory)
# Output: ../compunet-reborn.crt + build/terminal.bin + build/acia_driver.bin

CA65 = ca65
LD65 = ld65
PYTHON = python3

CRT = ../compunet-reborn.crt
ROM_BIN = build/compunet_reborn.bin
TERM_BIN = build/terminal.bin
ACIA_BIN = build/acia_driver.bin
ROM_OBJ = build/compunet_reborn.o
TERM_OBJ = build/terminal.o
ACIA_OBJ = build/acia_driver.o
ROM_SRC = compunet_rom.s
TERM_SRC = terminal.s
ACIA_SRC = acia_driver.s
CFG = cartridge.cfg

.PHONY: all clean verify

all: $(CRT) $(TERM_BIN) $(ACIA_BIN) verify

$(CRT): $(ROM_BIN)
	$(PYTHON) make_crt.py $(ROM_BIN) $(CRT)

$(ROM_BIN): $(ROM_OBJ) $(CFG)
	$(LD65) -C $(CFG) $(ROM_OBJ) -o $(ROM_BIN)

$(ROM_OBJ): $(ROM_SRC) | build
	$(CA65) -t c64 $(ROM_SRC) -o $(ROM_OBJ)

$(TERM_BIN): $(TERM_OBJ) terminal.cfg
	$(LD65) -C terminal.cfg $(TERM_OBJ) -o $(TERM_BIN)

$(TERM_OBJ): $(TERM_SRC) | build
	$(CA65) -t c64 $(TERM_SRC) -o $(TERM_OBJ)

$(ACIA_BIN): $(ACIA_OBJ) acia_driver.cfg
	$(LD65) -C acia_driver.cfg $(ACIA_OBJ) -o $(ACIA_BIN)
	@# Also create a PRG file (2-byte load address header + code)
	@printf '\x00\xc8' > build/acia.prg
	@cat $(ACIA_BIN) >> build/acia.prg

$(ACIA_OBJ): $(ACIA_SRC) | build
	$(CA65) -t c64 $(ACIA_SRC) -o $(ACIA_OBJ)

verify: $(ROM_BIN) $(TERM_BIN) $(ACIA_BIN)
	@cmp -s $(ROM_BIN) original_rom.bin && echo "✓ ROM: BYTE-IDENTICAL to original" || echo "✗ ROM: DIFFERS from original (modified)"
	@$(PYTHON) -c "import sys; d=open('$(TERM_BIN)','rb').read(); r=open('../../../historical/cnet.prg','rb').read()[2:]; print('✓ TERMINAL: BYTE-IDENTICAL to original' if d==r else '✗ TERMINAL: DIFFERS from original (modified)')"
	@echo "  ACIA driver: $$(wc -c < $(ACIA_BIN)) bytes at \$$C800"

build:
	mkdir -p build

clean:
	rm -rf build $(CRT)
