/**
 * Compunet SEQ Frame Renderer
 * 
 * Renders Compunet frame data (SEQ files) to the PETSCII screen.
 * 
 * Frame format:
 *   Byte 0: $00 (frame start marker)
 *   Byte 1: Border colour OR'd with $F0 (low nibble = colour 0-15)
 *   Byte 2: Background colour OR'd with $F0 (low nibble = colour 0-15)
 *   Remaining: PETSCII stream with control codes
 * 
 * Control codes:
 *   $00       = End of frame
 *   $06       = Space shorthand (equivalent to $20)
 *   $07 C N   = RLE: repeat character C, N times
 *   $0D       = Carriage return (newline)
 *   $0E       = Switch to lowercase/uppercase charset
 *   $8E       = Switch to uppercase/graphics charset
 *   $12       = Reverse video ON
 *   $92       = Reverse video OFF
 *   $05       = White    $1C = Red      $1E = Green    $1F = Blue
 *   $81 = Orange  $90 = Black    $95 = Brown    $96 = Light Red
 *   $97 = Dark Grey  $98 = Medium Grey  $99 = Light Green
 *   $9A = Light Blue  $9B = Light Grey  $9C = Purple
 *   $9E = Yellow  $9F = Cyan
 *   $11 = Cursor Down  $91 = Cursor Up
 *   $1D = Cursor Right  $9D = Cursor Left
 *   $13 = Home  $93 = Clear Screen
 */

// PETSCII colour code to C64 colour index mapping
const PETSCII_COLOUR_MAP = {
    0x05: 1,   // white
    0x1C: 2,   // red
    0x1E: 5,   // green
    0x1F: 6,   // blue
    0x81: 8,   // orange
    0x90: 0,   // black
    0x95: 9,   // brown
    0x96: 10,  // light red
    0x97: 11,  // dark grey
    0x98: 12,  // medium grey
    0x99: 13,  // light green
    0x9A: 14,  // light blue
    0x9B: 15,  // light grey
    0x9C: 4,   // purple
    0x9E: 7,   // yellow
    0x9F: 3,   // cyan
};

class SEQRenderer {
    constructor(renderer) {
        this.renderer = renderer;
    }
    
    /**
     * Render a SEQ frame to the screen.
     * @param {Uint8Array} data - Raw SEQ file bytes
     * @param {number} maxRow - Maximum row to render to (default 23, leaving room for duckshoot)
     */
    render(data, maxRow) {
        if (maxRow === undefined) maxRow = 23;
        
        const r = this.renderer;
        let pos = 0;
        
        // Parse 3-byte header
        if (data.length < 3) return;
        
        // Byte 0: $00 marker (skip)
        pos++;
        
        // Byte 1: border colour (low nibble)
        const borderByte = data[pos++];
        r.borderColour = borderByte & 0x0F;
        
        // Byte 2: background colour (low nibble)
        const bgByte = data[pos++];
        r.bgColour = bgByte & 0x0F;
        
        // Check for charset byte (some frames have $0E or $8E as byte 3)
        if (pos < data.length && (data[pos] === 0x0E || data[pos] === 0x8E)) {
            if (data[pos] === 0x0E) {
                r.setCharset(1); // lowercase/uppercase
            } else {
                r.setCharset(0); // uppercase/graphics
            }
            pos++;
        }
        
        // Clear screen with background colour
        r.clear();
        
        // Rendering state
        let curX = 0;
        let curY = 0;
        let curColour = 0; // default text colour (black on white bg, or white on dark bg)
        let reversed = false;
        
        // Set default text colour based on background
        if (r.bgColour === 0 || r.bgColour === 6 || r.bgColour === 9 || r.bgColour === 11) {
            curColour = 1; // white text on dark backgrounds
        } else {
            curColour = 0; // black text on light backgrounds
        }
        
        // RLE state
        let rleChar = 0;
        let rleCount = 0;
        
        while (pos < data.length) {
            let byte;
            
            // Check RLE repeat
            if (rleCount > 0) {
                byte = rleChar;
                rleCount--;
            } else {
                byte = data[pos++];
            }
            
            // End of frame
            if (byte === 0x00) break;
            
            // Control codes
            if (byte === 0x06) {
                // Space shorthand
                byte = 0x20;
            } else if (byte === 0x07) {
                // RLE: next byte = char, byte after = count
                if (pos + 1 < data.length) {
                    rleChar = data[pos++];
                    rleCount = data[pos++] - 1; // -1 because we output one now
                    byte = rleChar;
                } else {
                    break;
                }
            } else if (byte === 0x0D) {
                // Carriage return
                curX = 0;
                curY++;
                if (curY >= maxRow) curY = maxRow - 1;
                continue;
            } else if (byte === 0x0E) {
                // Lowercase charset
                r.setCharset(1);
                continue;
            } else if (byte === 0x8E) {
                // Uppercase charset
                r.setCharset(0);
                continue;
            } else if (byte === 0x12) {
                // Reverse ON
                reversed = true;
                continue;
            } else if (byte === 0x92) {
                // Reverse OFF
                reversed = false;
                continue;
            } else if (byte === 0x11) {
                // Cursor down
                curY++;
                if (curY >= maxRow) curY = maxRow - 1;
                continue;
            } else if (byte === 0x91) {
                // Cursor up
                curY--;
                if (curY < 0) curY = 0;
                continue;
            } else if (byte === 0x1D) {
                // Cursor right
                curX++;
                if (curX >= 40) { curX = 0; curY++; }
                if (curY >= maxRow) curY = maxRow - 1;
                continue;
            } else if (byte === 0x9D) {
                // Cursor left
                curX--;
                if (curX < 0) { curX = 39; curY--; }
                if (curY < 0) curY = 0;
                continue;
            } else if (byte === 0x13) {
                // Home
                curX = 0;
                curY = 0;
                continue;
            } else if (byte === 0x93) {
                // Clear screen
                r.clear();
                curX = 0;
                curY = 0;
                continue;
            } else if (byte === 0x14) {
                // Delete (backspace)
                curX--;
                if (curX < 0) { curX = 39; curY--; }
                if (curY < 0) { curY = 0; curX = 0; }
                r.setChar(curX, curY, 0x20, curColour);
                continue;
            } else if (PETSCII_COLOUR_MAP[byte] !== undefined) {
                // Colour change
                curColour = PETSCII_COLOUR_MAP[byte];
                continue;
            } else if (byte < 0x20 && byte !== 0x06 && byte !== 0x07) {
                // Other control codes - skip
                continue;
            } else if (byte >= 0x80 && byte <= 0x9F && PETSCII_COLOUR_MAP[byte] === undefined) {
                // Other C1 control codes - skip
                continue;
            }
            
            // Printable character - output to screen
            if (curY < maxRow) {
                let screenCode = r._toScreenCode(byte);
                if (reversed) {
                    screenCode += 128; // reversed version
                }
                const idx = curY * 40 + curX;
                r.screenChars[idx] = screenCode;
                r.screenColours[idx] = curColour;
                
                curX++;
                if (curX >= 40) {
                    curX = 0;
                    curY++;
                    if (curY >= maxRow) curY = maxRow - 1;
                }
            }
        }
    }
    
    /**
     * Load a SEQ file from a URL and render it.
     */
    async loadAndRender(url, maxRow) {
        const response = await fetch(url);
        const buffer = await response.arrayBuffer();
        const data = new Uint8Array(buffer);
        this.render(data, maxRow);
    }
}
