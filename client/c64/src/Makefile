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
LIVE_PRG = ../compunet-reborn-live.prg
D64 = ../compunet-reborn.d64
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

CRT = ../compunet-reborn.crt
LIVE_CRT = ../compunet-reborn-live.crt

.PHONY: all clean

all: $(PRG) $(LIVE_PRG) $(D64) $(CRT) $(LIVE_CRT) $(TERMINAL_BIN)
	@cp $(TERMINAL_BIN) $(SERVER_CFG)/terminal.bin
	@echo "Created $(TERMINAL_BIN) ($$(wc -c < $(TERMINAL_BIN)) bytes, for LINKING)"

$(LIVE_CRT): $(LIVE_BIN)
	@python3 -c "\
import struct;\
rom=open('$(LIVE_BIN)','rb').read()[:0x2000].ljust(8192,b'\x00');\
crt=bytearray();\
crt.extend(b'C64 CARTRIDGE   ');\
crt.extend(struct.pack('>I',0x40));\
crt.extend(struct.pack('>H',0x0100));\
crt.extend(struct.pack('>H',0x0000));\
crt.append(0x00);crt.append(0x01);\
crt.extend(b'\x00'*6);\
crt.extend(b'COMPUNET REBORN LIVE'.ljust(32,b'\x00'));\
crt.extend(b'CHIP');\
crt.extend(struct.pack('>I',0x2010));\
crt.extend(struct.pack('>H',0x0000));\
crt.extend(struct.pack('>H',0x0000));\
crt.extend(struct.pack('>H',0x8000));\
crt.extend(struct.pack('>H',0x2000));\
crt.extend(rom);\
open('$(LIVE_CRT)','wb').write(crt)"
	@echo "Created $(LIVE_CRT) (8K cartridge, auto-connect, $$(wc -c < $(LIVE_CRT)) bytes)"

$(CRT): $(BIN)
	@python3 -c "\
import struct;\
rom=open('$(BIN)','rb').read()[:0x2000].ljust(8192,b'\x00');\
crt=bytearray();\
crt.extend(b'C64 CARTRIDGE   ');\
crt.extend(struct.pack('>I',0x40));\
crt.extend(struct.pack('>H',0x0100));\
crt.extend(struct.pack('>H',0x0000));\
crt.append(0x00);crt.append(0x01);\
crt.extend(b'\x00'*6);\
crt.extend(b'COMPUNET REBORN'.ljust(32,b'\x00'));\
crt.extend(b'CHIP');\
crt.extend(struct.pack('>I',0x2010));\
crt.extend(struct.pack('>H',0x0000));\
crt.extend(struct.pack('>H',0x0000));\
crt.extend(struct.pack('>H',0x8000));\
crt.extend(struct.pack('>H',0x2000));\
crt.extend(rom);\
open('$(CRT)','wb').write(crt)"
	@echo "Created $(CRT) (8K cartridge, $$(wc -c < $(CRT)) bytes)"

$(TERMINAL_BIN): $(BIN)
	@dd if=$(BIN) bs=1 skip=$$((0x2000)) count=$$((0x2900)) of=$(TERMINAL_BIN) 2>/dev/null
	@# Strip trailing fill zeros, but keep the final meaningful $00 (string terminator)
	@python3 -c "d=open('$(TERMINAL_BIN)','rb').read().rstrip(b'\x00')+b'\x00';open('$(TERMINAL_BIN)','wb').write(d)"

CRT_ENTRY_ADDR = $(shell python3 -c "d=open('$(BIN)','rb').read();import sys;i=d.find(b'\x78\xa2\xff\x9a\xd8');print(f'{0x8000+i}') if i>=0 else sys.exit(1)")

$(PRG): $(BIN)
	@python3 gen_sfx.py $(BIN) $(PRG) $(CRT_ENTRY_ADDR)
	@cp $(PRG) $(WEBSITE_STATIC)/compunet-reborn.prg
	@echo "Created $(PRG) ($$(wc -c < $(PRG)) bytes, LOAD + RUN)"

LIVE_CRT_ENTRY_ADDR = $(shell python3 -c "d=open('$(LIVE_BIN)','rb').read();import sys;i=d.find(b'\x78\xa2\xff\x9a\xd8');print(f'{0x8000+i}') if i>=0 else sys.exit(1)")

$(LIVE_PRG): $(LIVE_BIN)
	@python3 gen_sfx.py $(LIVE_BIN) $(LIVE_PRG) $(LIVE_CRT_ENTRY_ADDR)
	@cp $(LIVE_PRG) $(WEBSITE_STATIC)/compunet-reborn-live.prg
	@echo "Created $(LIVE_PRG) ($$(wc -c < $(LIVE_PRG)) bytes, auto-connect, LOAD + RUN)"

$(LIVE_BIN): $(LIVE_OBJ) $(CFG)
	$(LD65) -C $(CFG) $(LIVE_OBJ) -o $(LIVE_BIN)

$(LIVE_OBJ): $(SRC) $(VERSION_INC) | build
	$(CA65) -t c64 -D AUTO_CONNECT $(SRC) -o $(LIVE_OBJ)

$(D64): $(PRG) $(LIVE_PRG)
	$(C1541) -format "compunet,cr" d64 $(D64) -write $(PRG) compunet -write $(LIVE_PRG) "compunet-live"
	@cp $(D64) $(WEBSITE_STATIC)/compunet-reborn.d64
	@echo "Created $(D64) (copied to website/static/)"

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
	rm -rf build $(PRG) $(LIVE_PRG) $(D64) $(CRT) $(LIVE_CRT)
