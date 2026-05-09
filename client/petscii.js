/**
 * PETSCII rendering engine for the Compunet terminal.
 * Renders C64-style 40x25 character screen with the correct palette.
 */

// C64 colour palette (VIC-II colours)
const C64_PALETTE = [
    '#000000', // 0  Black
    '#FFFFFF', // 1  White
    '#880000', // 2  Red
    '#AAFFEE', // 3  Cyan
    '#CC44CC', // 4  Purple
    '#00CC55', // 5  Green
    '#0000AA', // 6  Blue
    '#EEEE77', // 7  Yellow
    '#DD8855', // 8  Orange
    '#664400', // 9  Brown
    '#FF7777', // 10 Light Red
    '#333333', // 11 Dark Grey
    '#777777', // 12 Medium Grey
    '#AAFF66', // 13 Light Green
    '#0088FF', // 14 Light Blue
    '#BBBBBB', // 15 Light Grey
];

// C64 character set (8x8 pixel font)
// This is a minimal implementation using the standard uppercase/graphics charset.
// Each character is 8 bytes, each byte is a row of 8 pixels.
// We'll generate this from a built-in bitmap representation.

class PETSCIIRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.cols = 40;
        this.rows = 25;
        this.charWidth = 8;
        this.charHeight = 8;
        
        // Screen buffer: character codes
        this.screenChars = new Uint8Array(this.cols * this.rows);
        // Colour buffer: colour index per character
        this.screenColours = new Uint8Array(this.cols * this.rows);
        // Background colour
        this.bgColour = 6;  // Blue (default Compunet background)
        // Border colour
        this.borderColour = 14; // Light blue
        // Default text colour
        this.textColour = 1;  // White
        
        // Cursor position
        this.cursorX = 0;
        this.cursorY = 0;
        
        // Character ROM (generated below)
        this.charROM = null;
        this._generateCharROM();
        
        // Fill screen with spaces
        this.clear();
    }
    
    _generateCharROM() {
        // Use the real C64 character ROM if available
        if (typeof C64_CHARROM_SET1 !== 'undefined') {
            this.charROMs = [C64_CHARROM_SET1, C64_CHARROM_SET2];
            this.charROM = this.charROMs[0]; // Start with uppercase/graphics
            this.currentCharset = 0;
            return;
        }
        if (typeof C64_CHARROM !== 'undefined') {
            this.charROMs = [C64_CHARROM, C64_CHARROM];
            this.charROM = C64_CHARROM;
            this.currentCharset = 0;
            return;
        }
        
        // Fallback: generate approximation from canvas text
        this.charROM = new Uint8Array(256 * 8);
        this.charROMs = [this.charROM, this.charROM];
        this.currentCharset = 0;
        const tmpCanvas = document.createElement('canvas');
        tmpCanvas.width = 8;
        tmpCanvas.height = 8;
        const tmpCtx = tmpCanvas.getContext('2d');
        tmpCtx.font = '8px monospace';
        tmpCtx.textBaseline = 'top';
        tmpCtx.fillStyle = '#fff';
        
        for (let i = 32; i < 128; i++) {
            tmpCtx.clearRect(0, 0, 8, 8);
            tmpCtx.fillText(String.fromCharCode(i), 0, 0);
            const imgData = tmpCtx.getImageData(0, 0, 8, 8);
            for (let row = 0; row < 8; row++) {
                let byte = 0;
                for (let col = 0; col < 8; col++) {
                    const idx = (row * 8 + col) * 4;
                    if (imgData.data[idx] > 128) {
                        byte |= (0x80 >> col);
                    }
                }
                this.charROM[i * 8 + row] = byte;
            }
        }
    }
    
    /**
     * Switch character set.
     * 0 = uppercase/graphics (set 1)
     * 1 = lowercase/uppercase (set 2)
     */
    setCharset(set) {
        this.currentCharset = set;
        this.charROM = this.charROMs[set];
    }
    
    clear() {
        this.screenChars.fill(32); // space
        this.screenColours.fill(this.textColour);
        this.cursorX = 0;
        this.cursorY = 0;
    }
    
    setChar(x, y, charCode, colour) {
        if (x >= 0 && x < this.cols && y >= 0 && y < this.rows) {
            const idx = y * this.cols + x;
            // Convert to screen code (input is PETSCII)
            this.screenChars[idx] = this._toScreenCode(charCode);
            this.screenColours[idx] = colour !== undefined ? colour : this.textColour;
        }
    }
    
    /**
     * Set a character using ASCII input (for print() convenience).
     * Converts ASCII to PETSCII first, then to screen code.
     */
    setCharASCII(x, y, charCode, colour) {
        if (x >= 0 && x < this.cols && y >= 0 && y < this.rows) {
            const idx = y * this.cols + x;
            this.screenChars[idx] = this._asciiToScreenCode(charCode);
            this.screenColours[idx] = colour !== undefined ? colour : this.textColour;
        }
    }
    
    /**
     * Convert PETSCII to C64 screen code.
     * Used for SEQ file rendering and raw PETSCII data.
     */
    _toScreenCode(petscii) {
        if (petscii >= 0x20 && petscii <= 0x3F) return petscii;          // space, digits, punct
        if (petscii >= 0x40 && petscii <= 0x5F) return petscii - 0x40;   // @=0, A=1..Z=26
        if (petscii >= 0x60 && petscii <= 0x7F) return petscii - 0x20;   // graphics -> 64-95
        if (petscii >= 0xA0 && petscii <= 0xBF) return petscii - 0x40;   // shifted graphics -> 96-127
        if (petscii >= 0xC0 && petscii <= 0xDF) return petscii - 0xC0;   // same as $40-$5F -> 0-31
        if (petscii >= 0xE0 && petscii <= 0xFE) return petscii - 0x80;   // same as $A0-$BE -> 96-126
        if (petscii === 0xFF) return 94;                                  // pi character
        return 32;
    }
    
    /**
     * Convert ASCII character code to screen code.
     * Used by print() and printAt() which receive ASCII text from JavaScript strings.
     */
    _asciiToScreenCode(ascii) {
        if (ascii >= 32 && ascii <= 63) return ascii;          // space, digits, punctuation (same)
        if (ascii === 64) return 0;                            // @
        if (ascii >= 65 && ascii <= 90) return ascii - 64;     // A-Z -> screen 1-26
        if (ascii >= 91 && ascii <= 95) return ascii - 64;     // [ \ ] ^ _ -> 27-31
        if (ascii >= 97 && ascii <= 122) return ascii - 96;    // a-z -> screen 1-26 (same as uppercase in charset 1)
        if (ascii >= 96 && ascii <= 127) return ascii - 32;    // other -> 64-95
        return 32;
    }
    
    getChar(x, y) {
        if (x >= 0 && x < this.cols && y >= 0 && y < this.rows) {
            return this.screenChars[y * this.cols + x];
        }
        return 32;
    }
    
    printAt(x, y, text, colour) {
        for (let i = 0; i < text.length; i++) {
            this.setCharASCII(x + i, y, text.charCodeAt(i), colour);
        }
    }
    
    print(text, colour) {
        const col = colour !== undefined ? colour : this.textColour;
        for (let i = 0; i < text.length; i++) {
            const ch = text.charCodeAt(i);
            if (ch === 13 || ch === 10) {
                this.cursorX = 0;
                this.cursorY++;
                if (this.cursorY >= this.rows) {
                    this._scrollUp();
                    this.cursorY = this.rows - 1;
                }
            } else {
                this.setCharASCII(this.cursorX, this.cursorY, ch, col);
                this.cursorX++;
                if (this.cursorX >= this.cols) {
                    this.cursorX = 0;
                    this.cursorY++;
                    if (this.cursorY >= this.rows) {
                        this._scrollUp();
                        this.cursorY = this.rows - 1;
                    }
                }
            }
        }
    }
    
    _scrollUp() {
        this.screenChars.copyWithin(0, this.cols);
        this.screenColours.copyWithin(0, this.cols);
        const lastRow = (this.rows - 1) * this.cols;
        this.screenChars.fill(32, lastRow);
        this.screenColours.fill(this.textColour, lastRow);
    }
    
    render() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        
        // C64 display layout with border
        const borderSize = 32;
        const screenX = borderSize;
        const screenY = borderSize;
        const screenW = this.cols * this.charWidth;  // 320
        const screenH = this.rows * this.charHeight; // 200
        
        // Fill entire canvas with border colour
        ctx.fillStyle = C64_PALETTE[this.borderColour];
        ctx.fillRect(0, 0, w, h);
        
        // Fill screen area with background colour
        ctx.fillStyle = C64_PALETTE[this.bgColour];
        ctx.fillRect(screenX, screenY, screenW, screenH);
        
        // Apply per-row background overrides (used by duckshoot)
        if (this.rowBgColours) {
            for (let row = 0; row < this.rows; row++) {
                if (this.rowBgColours[row] !== undefined) {
                    ctx.fillStyle = C64_PALETTE[this.rowBgColours[row]];
                    ctx.fillRect(screenX, screenY + row * this.charHeight, screenW, this.charHeight);
                }
            }
        }
        
        // Render each character
        for (let row = 0; row < this.rows; row++) {
            for (let col = 0; col < this.cols; col++) {
                const idx = row * this.cols + col;
                const charCode = this.screenChars[idx];
                const colour = this.screenColours[idx];
                
                if (charCode === 32) continue; // skip spaces
                
                // Determine the background for this cell (for reversed chars)
                const cellBg = (this.rowBgColours && this.rowBgColours[row] !== undefined) 
                    ? this.rowBgColours[row] : this.bgColour;
                
                this._renderChar(
                    screenX + col * this.charWidth,
                    screenY + row * this.charHeight,
                    charCode, colour, cellBg
                );
            }
        }
    }
    
    _renderChar(x, y, charCode, colourIdx, cellBg) {
        const ctx = this.ctx;
        
        // Screen codes 128-255 are "reversed" (inverted) versions of 0-127
        const isReversed = charCode >= 128;
        const baseCode = isReversed ? charCode - 128 : charCode;
        
        if (isReversed) {
            // Reversed: solid foreground colour block, with character shape
            // drawn in background colour (the shape is "cut out")
            const bgCol = cellBg !== undefined ? cellBg : this.bgColour;
            
            // Fill entire cell with foreground colour
            ctx.fillStyle = C64_PALETTE[colourIdx];
            ctx.fillRect(x, y, 8, 8);
            
            // Draw character shape pixels in background colour (cut out)
            const romOffset = baseCode * 8;
            let hasPixels = false;
            for (let row = 0; row < 8; row++) {
                if (this.charROM[romOffset + row] !== 0) { hasPixels = true; break; }
            }
            
            if (hasPixels) {
                ctx.fillStyle = C64_PALETTE[bgCol];
                for (let row = 0; row < 8; row++) {
                    const byte = this.charROM[romOffset + row];
                    if (byte === 0) continue;
                    for (let col = 0; col < 8; col++) {
                        if (byte & (0x80 >> col)) {
                            ctx.fillRect(x + col, y + row, 1, 1);
                        }
                    }
                }
            }
        } else {
            // Normal: draw character pixels in foreground colour
            ctx.fillStyle = C64_PALETTE[colourIdx];
            const romOffset = charCode * 8;
            for (let row = 0; row < 8; row++) {
                const byte = this.charROM[romOffset + row];
                if (byte === 0) continue;
                for (let col = 0; col < 8; col++) {
                    if (byte & (0x80 >> col)) {
                        ctx.fillRect(x + col, y + row, 1, 1);
                    }
                }
            }
        }
    }
    
    // Fill a row with a solid colour bar
    fillRow(y, colour) {
        for (let x = 0; x < this.cols; x++) {
            const idx = y * this.cols + x;
            // Use screen code 160 (reversed space = solid block) 
            // Actually in screen codes, 32 is space and 160 is reversed space (solid)
            // But we should use screen code 96 which is the full block in the graphics set
            this.screenChars[idx] = 160; // reversed space = solid block
            this.screenColours[idx] = colour;
        }
    }
    
    // Set background for a row
    setRowBackground(y, bgColour) {
        const ctx = this.ctx;
        ctx.fillStyle = C64_PALETTE[bgColour];
        ctx.fillRect(0, y * this.charHeight, this.cols * this.charWidth, this.charHeight);
    }
}
