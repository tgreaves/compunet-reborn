/**
 * Duckshoot menu implementation.
 * 
 * From the real hardware screenshot:
 * - Single row at the bottom, light blue (colour 14) background
 * - All command text in white (colour 1)
 * - Selected command shown in reverse video: white block with letters
 *   cut out in the background colour (appears as coloured text on white)
 * - Left/right cursor keys scroll, RETURN selects
 */

class Duckshoot {
    constructor(renderer) {
        this.renderer = renderer;
        this.commands = [];
        this.selectedIndex = 0;
        this.visible = false;
        this.onSelect = null;
        
        this.menuRow = 24;      // bottom row
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
        const r = this.renderer;
        if (r.rowBgColours) {
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
        
        // Set light blue row background for the duckshoot bar
        if (!r.rowBgColours) r.rowBgColours = {};
        r.rowBgColours[row] = 14; // light blue
        
        // Clear row to spaces (light blue bg shows through)
        for (let x = 0; x < r.cols; x++) {
            const idx = row * r.cols + x;
            r.screenChars[idx] = 32;
            r.screenColours[idx] = 1;
        }
        
        // Pad commands to fixed width
        const padded = this.commands.map(cmd => (cmd + '      ').substring(0, 6));
        
        // Centre position for highlight
        const centreX = Math.floor(r.cols / 2) - Math.floor(this.highlightWidth / 2);
        
        // Draw selected command in reverse video:
        // Reversed char with colour=white -> white solid block, letter shape in row bg (light blue)
        const selectedCmd = padded[this.selectedIndex];
        for (let i = 0; i < this.highlightWidth; i++) {
            const idx = row * r.cols + centreX + i;
            if (i < selectedCmd.length && selectedCmd[i] !== ' ') {
                const sc = r._toScreenCode(selectedCmd.charCodeAt(i));
                r.screenChars[idx] = sc + 128; // reversed character
                r.screenColours[idx] = 1; // white
            } else {
                r.screenChars[idx] = 160; // reversed space = solid white block
                r.screenColours[idx] = 1;
            }
        }
        
        // Draw commands to the left (white text on light blue bg)
        let x = centreX - 1;
        for (let cmdIdx = this.selectedIndex - 1; cmdIdx >= 0 && x >= 0; cmdIdx--) {
            const cmd = padded[cmdIdx];
            for (let i = cmd.length - 1; i >= 0 && x >= 0; i--) {
                if (cmd[i] !== ' ') {
                    const idx = row * r.cols + x;
                    r.screenChars[idx] = r._toScreenCode(cmd.charCodeAt(i));
                    r.screenColours[idx] = 1; // white
                }
                x--;
            }
        }
        
        // Draw commands to the right (white text on light blue bg)
        x = centreX + this.highlightWidth;
        for (let cmdIdx = this.selectedIndex + 1; cmdIdx < padded.length && x < r.cols; cmdIdx++) {
            const cmd = padded[cmdIdx];
            for (let i = 0; i < cmd.length && x < r.cols; i++) {
                if (cmd[i] !== ' ') {
                    const idx = row * r.cols + x;
                    r.screenChars[idx] = r._toScreenCode(cmd.charCodeAt(i));
                    r.screenColours[idx] = 1; // white
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
