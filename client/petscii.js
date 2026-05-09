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
        // Generate a basic C64-style character set
        // This is a simplified version - a full implementation would use
        // the actual C64 character ROM dump.
        // For now, we generate printable ASCII characters using canvas text
        // and convert to 8x8 bitmaps.
        
        this.charROM = new Uint8Array(256 * 8);
        
        // Create a temporary canvas for font rendering
        const tmpCanvas = document.createElement('canvas');
        tmpCanvas.width = 8;
        tmpCanvas.height = 8;
        const tmpCtx = tmpCanvas.getContext('2d');
        
        // Use a monospace font as approximation
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
        
        // PETSCII graphics characters (codes 160-255 and 0-31)
        // Generate some basic block graphics
        // Full block (code 160 / $A0)
        for (let row = 0; row < 8; row++) {
            this.charROM[160 * 8 + row] = 0xFF;
        }
        // Upper half block (code 163)
        for (let row = 0; row < 4; row++) {
            this.charROM[163 * 8 + row] = 0xFF;
        }
        // Lower half block (code 164)
        for (let row = 4; row < 8; row++) {
            this.charROM[164 * 8 + row] = 0xFF;
        }
        // Left half block (code 165)
        for (let row = 0; row < 8; row++) {
            this.charROM[165 * 8 + row] = 0xF0;
        }
        // Right half block (code 166)
        for (let row = 0; row < 8; row++) {
            this.charROM[166 * 8 + row] = 0x0F;
        }
        // Horizontal line (code 96 / $60 - shifted space in graphics mode)
        for (let row = 0; row < 8; row++) {
            this.charROM[96 * 8 + row] = (row === 4) ? 0xFF : 0x00;
        }
        // Vertical line
        for (let row = 0; row < 8; row++) {
            this.charROM[98 * 8 + row] = 0x08;
        }
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
            this.screenChars[idx] = charCode;
            this.screenColours[idx] = colour !== undefined ? colour : this.textColour;
        }
    }
    
    getChar(x, y) {
        if (x >= 0 && x < this.cols && y >= 0 && y < this.rows) {
            return this.screenChars[y * this.cols + x];
        }
        return 32;
    }
    
    printAt(x, y, text, colour) {
        for (let i = 0; i < text.length; i++) {
            this.setChar(x + i, y, text.charCodeAt(i), colour);
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
                this.setChar(this.cursorX, this.cursorY, ch, col);
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
        
        // Fill with border colour
        ctx.fillStyle = C64_PALETTE[this.borderColour];
        ctx.fillRect(0, 0, w, h);
        
        // Screen area (with border)
        const borderX = 0;
        const borderY = 0;
        const screenW = this.cols * this.charWidth;
        const screenH = this.rows * this.charHeight;
        
        // Fill background
        ctx.fillStyle = C64_PALETTE[this.bgColour];
        ctx.fillRect(borderX, borderY, screenW, screenH);
        
        // Render each character
        for (let row = 0; row < this.rows; row++) {
            for (let col = 0; col < this.cols; col++) {
                const idx = row * this.cols + col;
                const charCode = this.screenChars[idx];
                const colour = this.screenColours[idx];
                
                if (charCode === 32) continue; // skip spaces (background shows through)
                
                this._renderChar(
                    borderX + col * this.charWidth,
                    borderY + row * this.charHeight,
                    charCode, colour
                );
            }
        }
    }
    
    _renderChar(x, y, charCode, colourIdx) {
        const ctx = this.ctx;
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
    
    // Fill a row with a colour (for the duckshoot bar)
    fillRow(y, colour) {
        for (let x = 0; x < this.cols; x++) {
            const idx = y * this.cols + x;
            this.screenColours[idx] = colour;
            if (this.screenChars[idx] === 32) {
                this.screenChars[idx] = 160; // full block for solid bar
            }
        }
    }
    
    // Set background for a row
    setRowBackground(y, bgColour) {
        const ctx = this.ctx;
        ctx.fillStyle = C64_PALETTE[bgColour];
        ctx.fillRect(0, y * this.charHeight, this.cols * this.charWidth, this.charHeight);
    }
}
