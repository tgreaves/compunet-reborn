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
     * horizontal strip. The selected command is highlighted in the centre.
     * Commands to the left and right are visible but dimmed.
     */
    render() {
        if (!this.visible) return;
        
        const r = this.renderer;
        const row = this.menuRow;
        const barRow = this.barRow;
        
        // Clear the duckshoot rows
        for (let x = 0; x < r.cols; x++) {
            r.setChar(x, barRow, 160, 14);  // Light blue bar (separator)
            r.setChar(x, row, 32, 1);       // Clear command row
        }
        
        // Build the display string with the selected command centred
        // Each command is padded to 6 characters
        const padded = this.commands.map(cmd => {
            return cmd.length >= 6 ? cmd.substring(0, 6) : cmd + ' '.repeat(6 - cmd.length);
        });
        
        // Calculate the centre position
        const centreX = Math.floor(r.cols / 2) - Math.floor(this.highlightWidth / 2);
        
        // Render commands around the selected one
        const selectedCmd = padded[this.selectedIndex];
        
        // Place selected command at centre, highlighted
        for (let i = 0; i < this.highlightWidth; i++) {
            const ch = i < selectedCmd.length ? selectedCmd.charCodeAt(i) : 32;
            r.setChar(centreX + i, row, ch, 1); // White on blue (highlighted)
        }
        
        // Render commands to the left of selected
        let x = centreX - 1;
        for (let cmdIdx = this.selectedIndex - 1; cmdIdx >= 0 && x >= 0; cmdIdx--) {
            const cmd = padded[cmdIdx];
            // Place command right-to-left
            const startX = x - cmd.length;
            for (let i = cmd.length - 1; i >= 0 && x >= 0; i--) {
                r.setChar(x, row, cmd.charCodeAt(i), 15); // Light grey
                x--;
            }
        }
        
        // Render commands to the right of selected
        x = centreX + this.highlightWidth;
        for (let cmdIdx = this.selectedIndex + 1; cmdIdx < padded.length && x < r.cols; cmdIdx++) {
            const cmd = padded[cmdIdx];
            for (let i = 0; i < cmd.length && x < r.cols; i++) {
                r.setChar(x, row, cmd.charCodeAt(i), 15); // Light grey
                x++;
            }
        }
        
        // Draw highlight background for the selected command
        // (We'll handle this in the render pass by using reverse video)
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
