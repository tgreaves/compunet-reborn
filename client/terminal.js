/**
 * Compunet Terminal - main application logic.
 * 
 * Starts at the BASIC READY prompt with Compunet commands available:
 *   EDITOR  - Enter the offline page editor
 *   CONNECT - Dial up and connect to Compunet (requires server)
 *   CNLOAD  - Load saved terminal software from disk
 *   CNSAVE  - Save terminal software to disk
 *   HELP    - Show available commands
 *   OFF     - Remove Compunet extensions
 */

class CompunetTerminal {
    constructor() {
        this.canvas = document.getElementById('screen');
        this.renderer = new PETSCIIRenderer(this.canvas);
        this.duckshoot = new Duckshoot(this.renderer);
        this.editor = new FrameEditor(this.renderer, this.duckshoot);
        
        // Terminal state
        this.state = 'ready'; // ready, editor, connecting, online
        this.inputBuffer = '';
        
        // Set up keyboard handler
        document.addEventListener('keydown', (e) => this.handleKey(e));
        
        // Boot
        this.showReady();
        this._startRenderLoop();
    }
    
    showReady() {
        const r = this.renderer;
        r.bgColour = 6;       // Blue
        r.borderColour = 14;  // Light blue
        r.textColour = 1;     // White
        r.setCharset(1);      // Lowercase/uppercase
        r.clear();
        
        // Print version (from ROM at $807A)
        r.print('\n COMPUNET TERMINAL 1.22\n', 1);
        r.print(' SEPTEMBER 1984 ARIADNE SOFTWARE LTD.\n\n', 1);
        r.print('READY.\n', 5);
        
        this.state = 'ready';
        this.inputBuffer = '';
        this.duckshoot.hide();
    }
    
    handleKey(e) {
        e.preventDefault();
        
        if (this.state === 'ready') {
            this._handleReadyKey(e);
        } else if (this.state === 'editor') {
            this.editor.handleKey(e);
        }
    }
    
    _handleReadyKey(e) {
        const r = this.renderer;
        
        if (e.key === 'Enter') {
            // Process command
            const cmd = this.inputBuffer.trim().toUpperCase();
            r.print('\n', 1);
            this._executeCommand(cmd);
            this.inputBuffer = '';
        } else if (e.key === 'Backspace') {
            if (this.inputBuffer.length > 0) {
                this.inputBuffer = this.inputBuffer.slice(0, -1);
                // Move cursor back and erase
                r.cursorX--;
                if (r.cursorX < 0) { r.cursorX = 39; r.cursorY--; }
                r.setChar(r.cursorX, r.cursorY, 32, 1);
            }
        } else if (e.key.length === 1) {
            // Printable character
            const ch = e.key.toUpperCase();
            this.inputBuffer += ch;
            r.print(ch, 1);
        }
    }
    
    _executeCommand(cmd) {
        const r = this.renderer;
        
        switch (cmd) {
            case 'EDITOR':
            case 'E':
                this.state = 'editor';
                this.editor.enter();
                break;
                
            case 'CONNECT':
            case 'C':
                r.print('?NOT CONNECTED - NO SERVER\n', 2);
                r.print('\nREADY.\n', 5);
                break;
                
            case 'HELP':
                r.print('\n COMPUNET TERMINAL 1.22\n', 1);
                r.print(' SEPTEMBER 1984 ARIADNE SOFTWARE LTD.\n\n', 1);
                r.print(' EDITOR\n', 14);
                r.print(' CONNECT\n', 14);
                r.print(' CNLOAD\n', 14);
                r.print(' CNSAVE\n', 14);
                r.print(' HELP\n', 14);
                r.print(' OFF\n', 14);
                r.print('\nREADY.\n', 5);
                break;
                
            case 'CNLOAD':
                r.print('?NO FILE\n', 2);
                r.print('\nREADY.\n', 5);
                break;
                
            case 'CNSAVE':
                r.print('?NOT LINKED\n', 2);
                r.print('\nREADY.\n', 5);
                break;
                
            case 'OFF':
                r.print('COMPUNET EXTENSIONS REMOVED\n', 1);
                r.print('\nREADY.\n', 5);
                break;
                
            case '':
                r.print('READY.\n', 5);
                break;
                
            default:
                r.print('?SYNTAX ERROR\n', 2);
                r.print('\nREADY.\n', 5);
                break;
        }
    }
    
    _startRenderLoop() {
        const loop = () => {
            this.renderer.render();
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }
}

/**
 * Frame Editor - the Compunet page editor.
 * 
 * A frame is a single 40x25 screen containing:
 * - 1000 character codes (40 * 25)
 * - 1000 colour values (40 * 25)
 * - Background colour
 * - Border colour (not stored in frame, set per-session)
 * 
 * The editor holds multiple frames in memory (10-15 pages).
 * Navigation between frames uses LAST/NEXT.
 * EDIT mode allows direct typing/drawing on the current frame.
 */
class FrameEditor {
    constructor(renderer, duckshoot) {
        this.renderer = renderer;
        this.duckshoot = duckshoot;
        
        // Frame storage - array of frame objects
        this.frames = [];
        this.currentFrameIndex = 0;
        
        // Editor state
        this.editing = false;  // true when in EDIT mode (typing on page)
        this.cursorX = 0;
        this.cursorY = 0;
        this.currentColour = 0; // Black text on white page
        
        // Duckshoot callback
        this.duckshoot.onSelect = (cmd) => this._handleCommand(cmd);
    }
    
    /**
     * A frame stores screen codes and colours directly.
     */
    _createFrame() {
        return {
            chars: new Uint8Array(40 * 25).fill(32),   // screen code 32 = space
            colours: new Uint8Array(40 * 25).fill(0),  // black text
            bgColour: 1,       // white background (standard Compunet page)
            borderColour: 6,   // blue border
            charset: 1,        // lowercase/uppercase
        };
    }
    
    /**
     * Enter the editor from BASIC.
     * Sets up a white page with blue border and the editor duckshoot.
     */
    enter() {
        // Create initial frame if none exist
        if (this.frames.length === 0) {
            this.frames.push(this._createFrame());
        }
        
        this.currentFrameIndex = 0;
        this.editing = false;
        this._displayCurrentFrame();
        
        // Show editor duckshoot
        this.duckshoot.setCommands(DUCKSHOOT_EDITOR);
        this.duckshoot.show();
    }
    
    /**
     * Display the current frame on screen.
     */
    _displayCurrentFrame() {
        const r = this.renderer;
        const frame = this.frames[this.currentFrameIndex];
        
        // Set page colours
        r.bgColour = frame.bgColour;
        r.borderColour = frame.borderColour !== undefined ? frame.borderColour : 6;
        if (frame.charset !== undefined) {
            r.setCharset(frame.charset);
        } else {
            r.setCharset(1);
        }
        
        // Copy frame screen codes directly to screen buffer (rows 0-22)
        for (let y = 0; y < 23; y++) {
            for (let x = 0; x < 40; x++) {
                const idx = y * 40 + x;
                r.screenChars[idx] = frame.chars[idx];
                r.screenColours[idx] = frame.colours[idx];
            }
        }
        
        // Clear duckshoot rows
        for (let x = 0; x < 40; x++) {
            r.setChar(x, 23, 32, 14);
            r.setChar(x, 24, 32, 14);
        }
        
        // Render duckshoot
        this.duckshoot.render();
    }
    
    /**
     * Save current screen state back to the frame.
     * Stores screen codes directly - no conversion needed.
     */
    _saveCurrentFrame() {
        const r = this.renderer;
        const frame = this.frames[this.currentFrameIndex];
        
        for (let y = 0; y < 23; y++) {
            for (let x = 0; x < 40; x++) {
                const idx = y * 40 + x;
                frame.chars[idx] = r.screenChars[idx];
                frame.colours[idx] = r.screenColours[idx];
            }
        }
        frame.bgColour = r.bgColour;
        frame.borderColour = r.borderColour;
        frame.charset = r.currentCharset;
    }
    
    handleKey(e) {
        if (this.editing) {
            this._handleEditKey(e);
        } else {
            // In non-edit mode, only duckshoot navigation works
            this.duckshoot.handleKey(e.key);
        }
    }
    
    /**
     * Handle keypress while in EDIT mode.
     * Full C64-style editing: type characters, move cursor, change colours.
     */
    _handleEditKey(e) {
        const r = this.renderer;
        
        // F-keys for editor functions
        if (e.key === 'F1' || e.key === 'F2') {
            // F1 = stop editing (return to duckshoot)
            this._saveCurrentFrame();
            this.editing = false;
            this.duckshoot.show();
            this.duckshoot.render();
            return;
        }
        
        if (e.key === 'Escape') {
            // Also stop editing
            this._saveCurrentFrame();
            this.editing = false;
            this.duckshoot.show();
            this.duckshoot.render();
            return;
        }
        
        // Cursor movement
        if (e.key === 'ArrowLeft') {
            this.cursorX--;
            if (this.cursorX < 0) { this.cursorX = 39; this.cursorY--; }
            if (this.cursorY < 0) this.cursorY = 0;
            return;
        }
        if (e.key === 'ArrowRight') {
            this.cursorX++;
            if (this.cursorX >= 40) { this.cursorX = 0; this.cursorY++; }
            if (this.cursorY >= 23) this.cursorY = 22;
            return;
        }
        if (e.key === 'ArrowUp') {
            this.cursorY--;
            if (this.cursorY < 0) this.cursorY = 0;
            return;
        }
        if (e.key === 'ArrowDown') {
            this.cursorY++;
            if (this.cursorY >= 23) this.cursorY = 22;
            return;
        }
        
        // Enter = newline
        if (e.key === 'Enter') {
            this.cursorX = 0;
            this.cursorY++;
            if (this.cursorY >= 23) this.cursorY = 22;
            return;
        }
        
        // Backspace = delete
        if (e.key === 'Backspace') {
            this.cursorX--;
            if (this.cursorX < 0) { this.cursorX = 39; this.cursorY--; }
            if (this.cursorY < 0) { this.cursorY = 0; this.cursorX = 0; }
            r.setChar(this.cursorX, this.cursorY, 32, this.currentColour);
            return;
        }
        
        // Colour keys (Ctrl+1-8 on C64, we'll use 1-8 with Ctrl)
        if (e.ctrlKey && e.key >= '1' && e.key <= '8') {
            this.currentColour = parseInt(e.key) - 1;
            return;
        }
        
        // Printable character
        if (e.key.length === 1 && !e.ctrlKey && !e.altKey) {
            r.setChar(this.cursorX, this.cursorY, e.key.charCodeAt(0), this.currentColour);
            this.cursorX++;
            if (this.cursorX >= 40) {
                this.cursorX = 0;
                this.cursorY++;
                if (this.cursorY >= 23) this.cursorY = 22;
            }
        }
    }
    
    _handleCommand(cmd) {
        switch (cmd) {
            case 'EDIT':
                this.editing = true;
                this.cursorX = 0;
                this.cursorY = 0;
                this.duckshoot.hide();
                break;
                
            case 'NEW':
                this._saveCurrentFrame();
                this.frames.splice(this.currentFrameIndex + 1, 0, this._createFrame());
                this.currentFrameIndex++;
                this._displayCurrentFrame();
                break;
                
            case 'NEXT':
                if (this.currentFrameIndex < this.frames.length - 1) {
                    this._saveCurrentFrame();
                    this.currentFrameIndex++;
                    this._displayCurrentFrame();
                }
                break;
                
            case 'LAST':
                if (this.currentFrameIndex > 0) {
                    this._saveCurrentFrame();
                    this.currentFrameIndex--;
                    this._displayCurrentFrame();
                }
                break;
                
            case 'ERASE':
                if (this.frames.length > 1) {
                    this.frames.splice(this.currentFrameIndex, 1);
                    if (this.currentFrameIndex >= this.frames.length) {
                        this.currentFrameIndex = this.frames.length - 1;
                    }
                } else {
                    // Can't erase last frame, just clear it
                    this.frames[0] = this._createFrame();
                }
                this._displayCurrentFrame();
                break;
                
            case 'COPY':
                this._saveCurrentFrame();
                const copy = this._createFrame();
                const src = this.frames[this.currentFrameIndex];
                copy.chars.set(src.chars);
                copy.colours.set(src.colours);
                copy.bgColour = src.bgColour;
                this.frames.splice(this.currentFrameIndex + 1, 0, copy);
                this.currentFrameIndex++;
                this._displayCurrentFrame();
                break;
                
            case 'FREE':
                this._showStatus('FREE: ' + (15 - this.frames.length) + ' PAGES');
                break;
                
            case 'GET':
                this._getFile();
                break;
                
            case 'HELP':
                this._showHelp();
                break;
                
            case 'RETURN':
                this._saveCurrentFrame();
                // Return to BASIC prompt
                window.terminal.showReady();
                break;
                
            default:
                this._showStatus(cmd + ': NOT IMPLEMENTED');
                break;
        }
    }
    
    _showStatus(msg) {
        const r = this.renderer;
        // Show message on row 22 briefly
        r.printAt(0, 22, ' '.repeat(40), 0);
        r.printAt(1, 22, msg, 2); // Red text
    }
    
    /**
     * GET - Load a SEQ file from disk into the editor.
     * Opens a file picker, loads the SEQ data, and renders it as the current frame.
     */
    _getFile() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.seq';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => {
                const data = new Uint8Array(reader.result);
                const seq = new SEQRenderer(this.renderer);
                seq.render(data, 23);
                // Save the rendered screen as the current frame
                this._saveCurrentFrame();
                // Re-render duckshoot on top
                this.duckshoot.render();
                this._showStatus('LOADED: ' + file.name);
            };
            reader.readAsArrayBuffer(file);
        };
        input.click();
    }
    
    _showHelp() {
        const r = this.renderer;
        // Display help on the page area
        const savedFrame = this.frames[this.currentFrameIndex];
        
        r.bgColour = 6;
        for (let y = 0; y < 23; y++) {
            for (let x = 0; x < 40; x++) {
                r.setChar(x, y, 32, 1);
            }
        }
        
        r.printAt(1, 1, 'COMPUNET EDITOR HELP', 7);
        r.printAt(1, 3, 'EDIT  - Type/draw on page', 1);
        r.printAt(1, 4, 'NEW   - Create blank page', 1);
        r.printAt(1, 5, 'LAST  - Previous page', 1);
        r.printAt(1, 6, 'NEXT  - Next page', 1);
        r.printAt(1, 7, 'COPY  - Duplicate page', 1);
        r.printAt(1, 8, 'ERASE - Delete page', 1);
        r.printAt(1, 9, 'FREE  - Show space left', 1);
        r.printAt(1, 11, 'In EDIT mode:', 7);
        r.printAt(1, 12, 'F1/ESC - Stop editing', 1);
        r.printAt(1, 13, 'Ctrl+1-8 - Change colour', 1);
        r.printAt(1, 14, 'Arrows - Move cursor', 1);
        r.printAt(1, 16, 'RETURN - Back to BASIC', 7);
        r.printAt(1, 18, 'Page ' + (this.currentFrameIndex + 1) + 
                  ' of ' + this.frames.length, 14);
    }
}

// Start the terminal when the page loads
window.addEventListener('DOMContentLoaded', () => {
    window.terminal = new CompunetTerminal();
    
    // SEQ file loader
    document.getElementById('seq-file').addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            const data = new Uint8Array(reader.result);
            const t = window.terminal;
            const seq = new SEQRenderer(t.renderer);
            seq.render(data, 23);
            // Show the SHOW duckshoot after loading
            t.state = 'editor';
            t.duckshoot.setCommands(DUCKSHOOT_SHOW);
            t.duckshoot.show();
        };
        reader.readAsArrayBuffer(file);
    });
});
