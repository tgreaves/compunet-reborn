/**
 * Duckshoot menu implementation.
 * 
 * Based on the Compunet terminal disassembly:
 * - Horizontal scrolling command list on the bottom rows
 * - Left/right cursor keys scroll the menu
 * - The highlighted (centre) command is the active selection
 * - RETURN executes the highlighted command
 * 
 * The duckshoot occupies rows 23-24 of the screen.
 */

class Duckshoot {
    constructor(renderer) {
        this.renderer = renderer;
        this.commands = [];
        this.selectedIndex = 0;
        this.visible = false;
        this.onSelect = null;
        
        this.menuRow = 24;
        this.barRow = 23;
        this.highlightWidth = 6;
    }
    
    setCommands(commands) {
        this.commands = commands;
        this.selectedIndex = 0;
    }
    
    show() {
        this.visible = true;
        this.render();
    }
    
    hide() {
        this.visible = false;
        // Clear row background overrides
        const r = this.renderer;
        if (r.rowBgColours) {
            delete r.rowBgColours[this.barRow];
            delete r.rowBgColours[this.menuRow];
        }
    }
    
    handleKey(key) {
        if (!this.visible) return null;
        
        if (key === 'ArrowLeft') {
            if (this.selectedIndex > 0) {
                this.selectedIndex--;
                this.render();
            }
            return null;
        }
        
        if (key === 'ArrowRight') {
            if (this.selectedIndex < this.commands.length - 1) {
                this.selectedIndex++;
                this.render();
            }
            return null;
        }
        
        if (key === 'Enter') {
            const cmd = this.commands[this.selectedIndex];
            if (this.onSelect) {
                this.onSelect(cmd);
            }
            return cmd;
        }
        
        return null;
    }
    
    render() {
        if (!this.visible) return;
        
        const r = this.renderer;
        const row = this.menuRow;
        const barRow = this.barRow;
        
        // Set per-row backgrounds for the duckshoot area
        if (!r.rowBgColours) r.rowBgColours = {};
        r.rowBgColours[barRow] = 14; // light blue separator
        r.rowBgColours[row] = 6;     // blue command area
        
        // Row 23: separator - just use the row background (no chars needed)
        for (let x = 0; x < r.cols; x++) {
            const idx = barRow * r.cols + x;
            r.screenChars[idx] = 32; // space (shows row bg)
            r.screenColours[idx] = 14;
        }
        
        // Row 24: clear to spaces (shows blue row bg)
        for (let x = 0; x < r.cols; x++) {
            const idx = row * r.cols + x;
            r.screenChars[idx] = 32;
            r.screenColours[idx] = 15;
        }
        
        // Pad commands to fixed width
        const padded = this.commands.map(cmd => {
            return (cmd + '      ').substring(0, 6);
        });
        
        // Centre position for highlight
        const centreX = Math.floor(r.cols / 2) - Math.floor(this.highlightWidth / 2);
        
        // Draw highlight background: reversed spaces in white = white solid block
        for (let i = 0; i < this.highlightWidth; i++) {
            const idx = row * r.cols + centreX + i;
            r.screenChars[idx] = 160; // reversed space = solid block
            r.screenColours[idx] = 1; // white
        }
        
        // Draw selected command text as reversed chars on the white block
        // Reversed char in blue colour on white row-bg = blue solid with white letter cutout
        // That gives us: blue text appearance on white background
        const selectedCmd = padded[this.selectedIndex];
        for (let i = 0; i < selectedCmd.length; i++) {
            if (selectedCmd[i] !== ' ') {
                const idx = row * r.cols + centreX + i;
                const sc = r._toScreenCode(selectedCmd.charCodeAt(i));
                r.screenChars[idx] = sc + 128; // reversed character
                r.screenColours[idx] = 6; // blue - shows as blue block with letter in row-bg (white? no...)
            }
        }
        
        // Hmm - reversed char in colour 6 on row-bg 6 won't work either.
        // Let's think about this differently.
        //
        // On C64: reversed char = solid foreground colour with char shape in bg colour
        // Row bg = 6 (blue). If we put reversed char colour=1 (white):
        //   -> white solid block with letter shape in blue (row bg)
        //   -> Result: white block with blue letters = PERFECT!
        
        // Redo: highlight uses reversed chars in WHITE colour
        for (let i = 0; i < selectedCmd.length; i++) {
            const idx = row * r.cols + centreX + i;
            if (selectedCmd[i] !== ' ') {
                const sc = r._toScreenCode(selectedCmd.charCodeAt(i));
                r.screenChars[idx] = sc + 128; // reversed
                r.screenColours[idx] = 1; // white fg -> white block, letter in row-bg (blue)
            } else {
                r.screenChars[idx] = 160; // reversed space = solid white block
                r.screenColours[idx] = 1;
            }
        }
        
        // Draw commands to the left (light grey text on blue bg)
        let x = centreX - 1;
        for (let cmdIdx = this.selectedIndex - 1; cmdIdx >= 0 && x >= 0; cmdIdx--) {
            const cmd = padded[cmdIdx];
            for (let i = cmd.length - 1; i >= 0 && x >= 0; i--) {
                if (cmd[i] !== ' ') {
                    const idx = row * r.cols + x;
                    r.screenChars[idx] = r._toScreenCode(cmd.charCodeAt(i));
                    r.screenColours[idx] = 15; // light grey
                }
                x--;
            }
        }
        
        // Draw commands to the right (light grey text on blue bg)
        x = centreX + this.highlightWidth;
        for (let cmdIdx = this.selectedIndex + 1; cmdIdx < padded.length && x < r.cols; cmdIdx++) {
            const cmd = padded[cmdIdx];
            for (let i = 0; i < cmd.length && x < r.cols; i++) {
                if (cmd[i] !== ' ') {
                    const idx = row * r.cols + x;
                    r.screenChars[idx] = r._toScreenCode(cmd.charCodeAt(i));
                    r.screenColours[idx] = 15; // light grey
                }
                x++;
            }
        }
    }
}

// Predefined duckshoot command sets
const DUCKSHOOT_DIRECTORY = [
    'HELP', 'DIR', 'SHOW', 'BACK', 'GOTO', 'UCAT', 'MAIL',
    'ACCNT', 'EDITR', 'LEAVE', 'PRINT', 'LIFE', 'BUY',
    'UPLD', 'VOTE'
];

const DUCKSHOOT_EDITOR = [
    'HELP', 'EDIT', 'LAST', 'NEXT', 'NEW', 'COPY', 'ERASE',
    'GET', 'PUT', 'STORE', 'PRINT', 'FREE', 'DOS', 'RETURN'
];

const DUCKSHOOT_SHOW = [
    'MORE', 'FINISH', 'ALL'
];

const DUCKSHOOT_COURIER = [
    'SEND', 'FINISH', 'NEXT', 'LAST', 'GET', 'DONE'
];

const DUCKSHOOT_UPLOAD = [
    'SEND', 'FINISH', 'ABORT', 'LOAD', 'SAVE', 'LAST', 'NEXT', 'GET'
];
