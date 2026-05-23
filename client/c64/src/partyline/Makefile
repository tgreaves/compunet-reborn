TARGET = partyline.prg
SRC = partyline.s
CFG = partyline.cfg
OBJ = build/partyline.o
BIN = build/partyline.bin

SERVER_DATA_EXAMPLE = ../../../../server/data.example/content/root/partyline
SERVER_DATA = ../../../../server/data/content/root/partyline/join-partyline

.PHONY: all clean

all: $(TARGET)
	@mkdir -p $(SERVER_DATA_EXAMPLE)
	cp $(TARGET) $(SERVER_DATA_EXAMPLE)/partyline.prg
	@echo "Copied to $(SERVER_DATA_EXAMPLE)/partyline.prg"
	@if [ -d $(SERVER_DATA) ]; then cp $(TARGET) $(SERVER_DATA)/partyline.prg; echo "Copied to $(SERVER_DATA)/partyline.prg"; fi

$(TARGET): $(BIN)
	@# The binary is raw code at $C000. No PRG header needed for server streaming.
	cp $(BIN) $(TARGET)
	@echo "Created $(TARGET) ($$(wc -c < $(BIN)) bytes at $$C000)"

$(BIN): $(OBJ) $(CFG)
	ld65 -C $(CFG) $(OBJ) -o $(BIN)

$(OBJ): $(SRC)
	@mkdir -p build
	ca65 -t c64 $(SRC) -o $(OBJ)

clean:
	rm -rf build $(TARGET)
