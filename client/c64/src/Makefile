# Compunet Reborn ROM — Build System
# Usage: make (from this directory)
# Output: ../compunet-reborn.crt

CA65 = ca65
LD65 = ld65
PYTHON = python3

TARGET = ../compunet-reborn.crt
BIN = build/compunet_reborn.bin
OBJ = build/compunet_reborn.o
SRC = compunet_rom.s
CFG = cartridge.cfg

.PHONY: all clean

all: $(TARGET) verify

$(TARGET): $(BIN)
	$(PYTHON) make_crt.py $(BIN) $(TARGET)

verify: $(BIN)
	@cmp -s $(BIN) original_rom.bin && echo "✓ BYTE-IDENTICAL to original ROM" || echo "✗ DIFFERS from original ROM"

$(BIN): $(OBJ) $(CFG)
	$(LD65) -C $(CFG) $(OBJ) -o $(BIN)

$(OBJ): $(SRC) $(wildcard *.s) | build
	$(CA65) -t c64 $(SRC) -o $(OBJ)

build:
	mkdir -p build

clean:
	rm -rf build $(TARGET)
