# Compunet Reborn — Build System
# Single combined source file → PRG + D64
# Usage: make
# Output: ../compunet-reborn.prg, ../compunet-reborn.d64
#   LOAD "COMPUNET",8,1 : SYS 33184

CA65 = ca65
LD65 = ld65
C1541 = c1541

PRG = ../compunet-reborn.prg
D64 = ../compunet-reborn.d64
BIN = build/compunet.bin
OBJ = build/compunet.o
SRC = compunet.s
CFG = compunet.cfg

.PHONY: all clean

all: $(PRG) $(D64)

$(PRG): $(BIN)
	@printf '\x00\x80' > $(PRG)
	@cat $(BIN) >> $(PRG)
	@echo "Created $(PRG) ($$(wc -c < $(PRG)) bytes, SYS 33184)"

$(D64): $(PRG)
	$(C1541) -format "compunet,cr" d64 $(D64) -write $(PRG) compunet
	@echo "Created $(D64)"

$(BIN): $(OBJ) $(CFG)
	$(LD65) -C $(CFG) $(OBJ) -o $(BIN)

$(OBJ): $(SRC) | build
	$(CA65) -t c64 $(SRC) -o $(OBJ)

build:
	mkdir -p build

clean:
	rm -rf build $(PRG) $(D64)
