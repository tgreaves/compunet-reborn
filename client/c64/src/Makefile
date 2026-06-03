# Compunet Reborn — Build System
# Usage: make
#        make HASH=6fc715   (override client hash for testing against a specific server)
# Output:
#   ../compunet-reborn.prg          (raw PRG, SYS 33184)
#   ../compunet-reborn-sfx.prg     (self-extracting, LOAD + RUN)
#   ../compunet-reborn.d64          (D64: SFX + live + raw)
#   ../compunet-reborn-live.prg    (auto-connect to vme.compunet.live:6400)
#   ../compunet-reborn-live.d64    (D64: live version only)

CA65 = ca65
LD65 = ld65
C1541 = c1541

VERSION_FILE = ../../../VERSION
VERSION := $(shell cat $(VERSION_FILE) 2>/dev/null || echo "0.0")

PRG = ../compunet-reborn.prg
SFX_PRG = ../compunet-reborn-sfx.prg
LIVE_PRG = ../compunet-reborn-live.prg
D64 = ../compunet-reborn.d64
LIVE_D64 = ../compunet-reborn-live.d64
BIN = build/compunet.bin
LIVE_BIN = build/compunet_live.bin
OBJ = build/compunet.o
LIVE_OBJ = build/compunet_live.o
SRC = compunet.s
CFG = compunet.cfg
VERSION_INC = build/version.inc

WEBSITE_STATIC = ../../../website/static
SERVER_CFG = ../../../server/cfg
TERMINAL_BIN = build/terminal.bin

.PHONY: all clean

all: $(PRG) $(SFX_PRG) $(LIVE_PRG) $(D64) $(LIVE_D64) $(TERMINAL_BIN)
	@cp $(TERMINAL_BIN) $(SERVER_CFG)/terminal.bin
	@echo "Created $(TERMINAL_BIN) ($$(wc -c < $(TERMINAL_BIN)) bytes, for LINKING)"

$(TERMINAL_BIN): $(BIN)
	@dd if=$(BIN) bs=1 skip=$$((0x2000)) count=$$((0x2900)) of=$(TERMINAL_BIN) 2>/dev/null
	@# Strip trailing zeros
	@python3 -c "d=open('$(TERMINAL_BIN)','rb').read().rstrip(b'\x00');open('$(TERMINAL_BIN)','wb').write(d)"

$(PRG): $(BIN)
	@printf '\x00\x80' > $(PRG)
	@cat $(BIN) >> $(PRG)
	@echo "Created $(PRG) ($$(wc -c < $(PRG)) bytes, SYS 33184, v$(VERSION))"

CRT_ENTRY_ADDR = $(shell python3 -c "d=open('$(BIN)','rb').read();import sys;i=d.find(b'\x78\xa2\xff\x9a\xd8');print(f'0x{0x8000+i:04X}') if i>=0 else sys.exit(1)")

$(SFX_PRG): $(PRG)
	exomizer sfx $(CRT_ENTRY_ADDR) $(PRG) -o $(SFX_PRG) -x1 -q
	@cp $(SFX_PRG) $(WEBSITE_STATIC)/compunet-reborn-sfx.prg
	@echo "Created $(SFX_PRG) ($$(wc -c < $(SFX_PRG)) bytes, LOAD + RUN, entry=$(CRT_ENTRY_ADDR))"

LIVE_CRT_ENTRY_ADDR = $(shell python3 -c "d=open('$(LIVE_BIN)','rb').read();import sys;i=d.find(b'\x78\xa2\xff\x9a\xd8');addr=0x8000+i;print(f'0x{addr:04X}');sys.exit(1) if addr+80>0xD000 else None" 2>/dev/null || (echo "ERROR: LIVE CRT_ENTRY too close to end of segment" >&2; exit 1))

$(LIVE_PRG): $(LIVE_BIN)
	@printf '\x00\x80' > $(LIVE_PRG)
	@cat $(LIVE_BIN) >> $(LIVE_PRG)
	exomizer sfx $(LIVE_CRT_ENTRY_ADDR) $(LIVE_PRG) -o $(LIVE_PRG) -x1 -q
	@echo "Created $(LIVE_PRG) ($$(wc -c < $(LIVE_PRG)) bytes, auto-connect, entry=$(LIVE_CRT_ENTRY_ADDR))"

$(LIVE_BIN): $(LIVE_OBJ) $(CFG)
	$(LD65) -C $(CFG) $(LIVE_OBJ) -o $(LIVE_BIN)

$(LIVE_OBJ): $(SRC) $(VERSION_INC) | build
	$(CA65) -t c64 -D AUTO_CONNECT $(SRC) -o $(LIVE_OBJ)

$(D64): $(SFX_PRG) $(LIVE_PRG) $(PRG)
	$(C1541) -format "compunet,cr" d64 $(D64) -write $(SFX_PRG) compunet -write $(LIVE_PRG) "compunet-live" -write $(PRG) "compunet-raw"
	@cp $(D64) $(WEBSITE_STATIC)/compunet-reborn.d64
	@echo "Created $(D64) (copied to website/static/)"

$(LIVE_D64): $(LIVE_PRG)
	$(C1541) -format "compunet,cr" d64 $(LIVE_D64) -write $(LIVE_PRG) compunet
	@cp $(LIVE_PRG) $(WEBSITE_STATIC)/compunet-reborn-live.prg
	@cp $(LIVE_D64) $(WEBSITE_STATIC)/compunet-reborn-live.d64
	@echo "Created $(LIVE_D64) (copied to website/static/)"

$(BIN): $(OBJ) $(CFG)
	$(LD65) -C $(CFG) $(OBJ) -o $(BIN)

$(OBJ): $(SRC) $(VERSION_INC) | build
	$(CA65) -t c64 $(SRC) -o $(OBJ)

# Usage: make HASH=6fc715   (override client hash for testing against a specific server)
HASH_ARG = $(if $(HASH),--hash=$(HASH),)

$(VERSION_INC): $(VERSION_FILE) | build
	python3 gen_version.py $(HASH_ARG)

build:
	mkdir -p build

clean:
	rm -rf build $(PRG) $(SFX_PRG) $(LIVE_PRG) $(D64) $(LIVE_D64)
