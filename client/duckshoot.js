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
        
        // Set black row background for the duckshoot bar
        if (!r.rowBgColours) r.rowBgColours = {};
        r.rowBgColours[row] = 0; // black
        
        // Clear row to spaces (light blue bg shows through)
        for (let x = 0; x < r.cols; x++) {
            const idx = row * r.cols + x;
            r.screenChars[idx] = 32;
            r.screenColours[idx] = 1;
        }
        
        // Build command string with 2 spaces between each word
        // No padding - just the command text with separators
        const cmds = this.commands;
        const separator = '  '; // 2 spaces between commands
        
        // Calculate positions of each command in the linear string
        const positions = []; // {start, end, text} for each command
        let pos = 0;
        for (let i = 0; i < cmds.length; i++) {
            if (i > 0) pos += separator.length;
            positions.push({ start: pos, end: pos + cmds[i].length, text: cmds[i] });
            pos += cmds[i].length;
        }
        
        // Centre the selected command in the row
        const sel = positions[this.selectedIndex];
        const selMid = Math.floor((sel.start + sel.end) / 2);
        const rowMid = Math.floor(r.cols / 2);
        const offset = rowMid - selMid; // offset to apply to all positions
        
        // Draw highlight: reversed chars for selected command + 1 space padding each side
        const hlStart = sel.start + offset - 1;
        const hlEnd = sel.end + offset + 1;
        for (let x = hlStart; x < hlEnd && x < r.cols; x++) {
            if (x < 0) continue;
            const idx = row * r.cols + x;
            const charPos = x - (sel.start + offset);
            if (charPos >= 0 && charPos < sel.text.length) {
                const sc = r._toScreenCode(sel.text.charCodeAt(charPos));
                r.screenChars[idx] = sc + 128; // reversed
                r.screenColours[idx] = 1; // white
            } else {
                r.screenChars[idx] = 160; // reversed space
                r.screenColours[idx] = 1;
            }
        }
        
        // Draw non-selected commands
        for (let i = 0; i < positions.length; i++) {
            if (i === this.selectedIndex) continue;
            const p = positions[i];
            for (let j = 0; j < p.text.length; j++) {
                const x = p.start + offset + j;
                if (x >= 0 && x < r.cols) {
                    const idx = row * r.cols + x;
                    r.screenChars[idx] = r._toScreenCode(p.text.charCodeAt(j));
                    r.screenColours[idx] = 1; // white
                }
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
