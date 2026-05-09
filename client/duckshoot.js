/**
 * Duckshoot menu implementation.
 * 
 * Based on the Compunet terminal disassembly:
 * - Horizontal scrolling command list displayed on the bottom row(s)
 * - Left/right cursor keys scroll the menu
 * - The highlighted (centre) command is the active selection
 * - RETURN executes the highlighted command
 * 
 * The duckshoot occupies the bottom 2 rows of the screen (rows 23-24).
 * Row 24 shows the commands, row 23 is a separator bar.
 */

class Duckshoot {
    constructor(renderer) {
        this.renderer = renderer;
        this.commands = [];
        this.selectedIndex = 0;
        this.visible = false;
        this.onSelect = null; // callback when command is selected
        
        // Display parameters
        this.menuRow = 24;      // bottom row for commands
        this.barRow = 23;       // separator bar row
        this.highlightWidth = 6; // width of highlighted area (chars)
        this.scrollOffset = 0;  // horizontal scroll position
    }
    
    /**
     * Set the command list for this duckshoot context.
     * Commands are strings like: ['HELP', 'DIR', 'SHOW', 'BACK', ...]
     */
    setCommands(commands) {
        this.commands = commands;
        this.selectedIndex = 0;
        this.scrollOffset = 0;
    }
    
    show() {
        this.visible = true;
        this.render();
    }
    
    hide() {
        this.visible = false;
    }
    
    /**
     * Handle keyboard input.
     * Returns the selected command name if RETURN pressed, null otherwise.
     */
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
    
    /**
     * Render the duckshoot to the screen buffer.
     * 
     * The original Compunet duckshoot displays commands in a scrolling
     * horizontal strip. The selected command is highlighted in reverse
     * video (dark text on light background). The bar itself is dark.
     */
    render() {
        if (!this.visible) return;
        
        const r = this.renderer;
        const row = this.menuRow;
        const barRow = this.barRow;
        
        // Clear the duckshoot rows with a dark background
        // Row 23: separator bar (solid light blue)
        for (let x = 0; x < r.cols; x++) {
            const idx = barRow * r.cols + x;
            r.screenChars[idx] = 160; // reversed space = solid block
            r.screenColours[idx] = 14; // light blue
        }
        
        // Row 24: command row (dark blue background via reversed spaces)
        for (let x = 0; x < r.cols; x++) {
            const idx = row * r.cols + x;
            r.screenChars[idx] = 160; // solid block for background
            r.screenColours[idx] = 6; // blue (dark background)
        }
        
        // Build the display string with the selected command centred
        const padded = this.commands.map(cmd => {
            return cmd.length >= 6 ? cmd.substring(0, 6) : cmd + ' '.repeat(6 - cmd.length);
        });
        
        // Calculate the centre position
        const centreX = Math.floor(r.cols / 2) - Math.floor(this.highlightWidth / 2);
        
        // Render selected command at centre - REVERSE VIDEO (white bg, blue text)
        const selectedCmd = padded[this.selectedIndex];
        for (let i = 0; i < this.highlightWidth; i++) {
            const idx = row * r.cols + centreX + i;
            if (i < selectedCmd.length && selectedCmd[i] !== ' ') {
                // Character on white background: use reversed char
                r.screenChars[idx] = r._toScreenCode(selectedCmd.charCodeAt(i)) + 128; // reversed
                r.screenColours[idx] = 1; // white (this becomes the "background" for reversed chars)
            } else {
                r.screenChars[idx] = 160; // solid block
                r.screenColours[idx] = 1; // white background for highlight area
            }
        }
        
        // Render commands to the left of selected (light text on dark bg)
        let x = centreX - 1;
        for (let cmdIdx = this.selectedIndex - 1; cmdIdx >= 0 && x >= 0; cmdIdx--) {
            const cmd = padded[cmdIdx];
            for (let i = cmd.length - 1; i >= 0 && x >= 0; i--) {
                const idx = row * r.cols + x;
                if (cmd[i] !== ' ') {
                    r.screenChars[idx] = r._toScreenCode(cmd.charCodeAt(i));
                    r.screenColours[idx] = 15; // light grey text
                } else {
                    r.screenChars[idx] = 160;
                    r.screenColours[idx] = 6; // dark bg
                }
                x--;
            }
        }
        
        // Render commands to the right of selected
        x = centreX + this.highlightWidth;
        for (let cmdIdx = this.selectedIndex + 1; cmdIdx < padded.length && x < r.cols; cmdIdx++) {
            const cmd = padded[cmdIdx];
            for (let i = 0; i < cmd.length && x < r.cols; i++) {
                const idx = row * r.cols + x;
                if (cmd[i] !== ' ') {
                    r.screenChars[idx] = r._toScreenCode(cmd.charCodeAt(i));
                    r.screenColours[idx] = 15; // light grey text
                } else {
                    r.screenChars[idx] = 160;
                    r.screenColours[idx] = 6; // dark bg
                }
                x++;
            }
        }
    }
}

// Predefined duckshoot command sets (from the disassembly)
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
