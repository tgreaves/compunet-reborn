# Compunet Reborn — Build System
# Single combined source file → PRG
# Usage: make
# Output: ../compunet-reborn.prg
#   LOAD "COMPUNET",8,1 : SYS 33184

CA65 = ca65
LD65 = ld65

PRG = ../compunet-reborn.prg
BIN = build/compunet.bin
OBJ = build/compunet.o
SRC = compunet.s
CFG = compunet.cfg

.PHONY: all clean

all: $(PRG)

$(PRG): $(BIN)
	@printf '\x00\x80' > $(PRG)
	@cat $(BIN) >> $(PRG)
	@echo "Created $(PRG) ($$(wc -c < $(PRG)) bytes, SYS 33184)"

$(BIN): $(OBJ) $(CFG)
	$(LD65) -C $(CFG) $(OBJ) -o $(BIN)

$(OBJ): $(SRC) | build
	$(CA65) -t c64 $(SRC) -o $(OBJ)

build:
	mkdir -p build

clean:
	rm -rf build $(PRG)
