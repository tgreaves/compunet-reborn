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
        
        // Connect login prompts take priority
        if (this.connectState === 'userid' || this.connectState === 'password') {
            this._handleConnectKey(e);
            return;
        }
        
        if (this._seqFrames && this.state === 'editor') {
            if (e.key === 'ArrowRight' && this._seqFrameIndex < this._seqFrames.length - 1) {
                this._seqFrameIndex++;
                this._renderSeqFrame();
                this._updateSeqInfo();
                return;
            } else if (e.key === 'ArrowLeft' && this._seqFrameIndex > 0) {
                this._seqFrameIndex--;
                this._renderSeqFrame();
                this._updateSeqInfo();
                return;
            }
        }

        if (this.state === 'ready') {
            this._handleReadyKey(e);
        } else if (this.state === 'editor') {
            this.editor.handleKey(e);
        } else if (this.state === 'online') {
            this._handleOnlineKey(e);
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
                this._connect();
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
    
    _connect() {
        const r = this.renderer;
        r.print('\nCONNECTING...\n', 1);
        
        this.protocol = new CompunetProtocol();
        this.connectState = 'connecting';
        
        this.protocol.onConnect = () => {
            r.print('CONNECTED\n\n', 5);
            r.print('  COMPUNET SYSTEM LOGON.\n\n', 1);
            r.print('  ENTER USER ID: ', 1);
            this.connectState = 'userid';
            this.inputBuffer = '';
        };
        
        this.protocol.onDirectory = (data) => {
            this.state = 'online';
            this.connectState = null;
            this._renderDirectoryData(data);
        };
        
        this.protocol.onFrame = (data) => {
            if (this.connectState === 'linking') {
                // Welcome frame after login - always show directory duckshoot
                this.state = 'online';
                this.connectState = null;
                const frameData = data.slice(1); // skip more-pages flag
                const seq = new SEQRenderer(r);
                seq.render(frameData, 23);
                this.duckshoot.setCommands(DUCKSHOOT_DIRECTORY);
                this.duckshoot.show();
                return;
            }
            
            // Normal frame display (SHOW command)
            const hasMore = data[0] === 0x01;
            const frameData = data.slice(1);
            const seq = new SEQRenderer(r);
            seq.render(frameData, 23);
            
            if (hasMore) {
                this.duckshoot.setCommands(DUCKSHOOT_SHOW);
            } else {
                this.duckshoot.setCommands(['FINISH']);
            }
            this.duckshoot.show();
        };
        
        this.protocol.onError = (data) => {
            let msg = '';
            for (let i = 0; i < data.length && data[i] !== 0; i++) {
                const b = data[i];
                if (b >= 0xC1 && b <= 0xDA) msg += String.fromCharCode(b - 0x80);
                else if (b >= 0x41 && b <= 0x5A) msg += String.fromCharCode(b);
                else if (b >= 0x20 && b <= 0x3F) msg += String.fromCharCode(b);
                else msg += '?';
            }
            
            if (this.connectState === 'linking') {
                // Login failed - show error and re-prompt
                r.print('\n\n  ' + msg + '\n\n', 2);
                r.print('  ENTER USER ID: ', 1);
                this.connectState = 'userid';
                this.inputBuffer = '';
            } else {
                r.printAt(1, 22, msg, 2);
            }
        };
        
        this.protocol.onDisconnect = () => {
            r.print('\nDISCONNECTED\n', 2);
            r.print('\nREADY.\n', 5);
            this.state = 'ready';
            this.connectState = null;
            this.duckshoot.hide();
        };
        
        this.protocol.connect('ws://localhost:6502');
    }
    
    _handleConnectKey(e) {
        const r = this.renderer;
        
        if (e.key === 'Enter') {
            const input = this.inputBuffer.trim();
            r.print('\n', 1);
            
            if (this.connectState === 'userid') {
                this._loginUserId = input || 'NEW-USER';
                r.print('  PASSWORD: ', 1);
                this.connectState = 'password';
                this.inputBuffer = '';
            } else if (this.connectState === 'password') {
                const password = input || 'INTRO';
                r.print('\n  LINKING...', 1);
                this.connectState = 'linking';
                this.protocol.login(this._loginUserId, password);
            }
        } else if (e.key === 'Backspace') {
            if (this.inputBuffer.length > 0) {
                this.inputBuffer = this.inputBuffer.slice(0, -1);
                r.cursorX--;
                if (r.cursorX < 0) { r.cursorX = 39; r.cursorY--; }
                r.setCharASCII(r.cursorX, r.cursorY, 32, 1);
            }
        } else if (e.key.length === 1) {
            const ch = e.key.toUpperCase();
            this.inputBuffer += ch;
            if (this.connectState === 'password') {
                r.print('*', 1);  // mask password
            } else {
                r.print(ch, 14);
            }
        }
    }
    
    _handleOnlineKey(e) {
        // Help mode: any key returns to directory
        if (this.helpMode) {
            this.helpMode = false;
            const r = this.renderer;
            r.bgColour = 15;
            r.borderColour = 6;
            r.setCharset(0);
            this._drawDirectory();
            this.duckshoot.setCommands(DUCKSHOOT_DIRECTORY);
            this.duckshoot.show();
            return;
        }
        
        // Handle GOTO input mode
        if (this.gotoMode) {
            this._handleGotoKey(e);
            return;
        }

        // Handle VOTE input mode
        if (this.voteMode) {
            this._handleVoteKey(e);
            return;
        }
        
        // Handle UP/DOWN for directory navigation (client-side, no server traffic)
        if (this.dirEntries && this.dirEntries.length > 0) {
            if (e.key === 'ArrowDown') {
                if (this.dirHighlight < this.dirEntries.length - 1) {
                    this.dirHighlight++;
                    this._drawDirectory();
                    this.duckshoot.render();
                }
                return;
            }
            if (e.key === 'ArrowUp') {
                if (this.dirHighlight > 0) {
                    this.dirHighlight--;
                    this._drawDirectory();
                    this.duckshoot.render();
                }
                return;
            }
            // F7/F8 toggle extra column (price/life/author/vote)
            if (e.key === 'F7' || e.key === 'F8') {
                this.dirColumn = (this.dirColumn + 1) % 4;
                this._drawDirectory();
                this.duckshoot.render();
                return;
            }
        }
        
        // Pass to duckshoot for LEFT/RIGHT/ENTER
        const cmd = this.duckshoot.handleKey(e.key);
        if (cmd) {
            this._handleOnlineCommand(cmd);
        }
    }
    
    _handleOnlineCommand(cmd) {
        switch (cmd) {
            case 'DIR':
                this.protocol.sendDir(this.dirHighlight);
                break;
            case 'SHOW':
                this.protocol.sendShow(this.dirHighlight);
                break;
            case 'MORE':
                this.protocol.sendMore();
                break;
            case 'BACK':
                this.protocol.sendBack();
                break;
            case 'GOTO':
                this._startGoto();
                break;
            case 'VOTE':
                this._startVote();
                break;
            case 'ACCNT':
                this.protocol.sendAccnt();
                break;
            case 'HELP':
                this._showOnlineHelp();
                break;
            case 'MAIL':
                this.protocol.sendMail();
                break;
            case 'LEAVE':
                this.protocol.disconnect();
                this.dirEntries = null;
                this.dirTitle = null;
                this.showReady();
                break;
            case 'EDITR':
                this.state = 'editor';
                this.editor.enter();
                break;
            case 'FINISH':
                // Return to directory listing - client-side, data already in memory
                if (this.dirEntries) {
                    const r = this.renderer;
                    r.bgColour = 15;    // light grey
                    r.borderColour = 6; // blue
                    r.setCharset(0);
                    this._drawDirectory();
                    this.duckshoot.setCommands(DUCKSHOOT_DIRECTORY);
                    this.duckshoot.show();
                }
                break;
            default:
                break;
        }
    }
    
    _startGoto() {
        const r = this.renderer;
        // Display prompt on row 22 (status area)
        for (let x = 0; x < 40; x++) {
            r.setCharASCII(x, 22, 32, 6);
        }
        r.printAt(1, 22, 'PAGE NUMBER? ', 6);
        this.gotoMode = true;
        this.inputBuffer = '';
    }
    
    _showOnlineHelp() {
        // Display the help frame (client-side, no server communication)
        // From disassembly: help is a pre-stored frame at $BB0C in cnet.prg
        if (typeof HELP_FRAME_DATA !== 'undefined') {
            const r = this.renderer;
            const seq = new SEQRenderer(r);
            seq.render(HELP_FRAME_DATA, 23);
            this.duckshoot.hide();
            this.helpMode = true;
        }
    }
    
    _handleGotoKey(e) {
        const r = this.renderer;
        
        if (e.key === 'Enter') {
            const pageNum = parseInt(this.inputBuffer);
            this.gotoMode = false;
            // Clear the prompt
            for (let x = 0; x < 40; x++) {
                r.setCharASCII(x, 22, 32, 0);
            }
            if (pageNum > 0) {
                this.protocol.sendGoto(pageNum);
            }
        } else if (e.key === 'Backspace') {
            if (this.inputBuffer.length > 0) {
                this.inputBuffer = this.inputBuffer.slice(0, -1);
                const col = 14 + this.inputBuffer.length;
                r.setCharASCII(col, 22, 32, 6);
            }
        } else if (e.key >= '0' && e.key <= '9' && this.inputBuffer.length < 6) {
            this.inputBuffer += e.key;
            r.printAt(14 + this.inputBuffer.length - 1, 22, e.key, 1);
        } else if (e.key === 'Escape') {
            this.gotoMode = false;
            for (let x = 0; x < 40; x++) {
                r.setCharASCII(x, 22, 32, 0);
            }
        }
    }
    
    _startVote() {
        const r = this.renderer;
        // Display prompt on row 22 (status area)
        for (let x = 0; x < 40; x++) {
            r.setCharASCII(x, 22, 32, 6);
        }
        r.printAt(1, 22, 'VOTE (1-5)? ', 6);
        this.voteMode = true;
    }

    _handleVoteKey(e) {
        const r = this.renderer;

        if (e.key >= '1' && e.key <= '5') {
            const vote = parseInt(e.key);
            this.voteMode = false;
            // Clear the prompt
            for (let x = 0; x < 40; x++) {
                r.setCharASCII(x, 22, 32, 0);
            }
            this.protocol.sendVote(vote);
        } else if (e.key === 'Escape') {
            this.voteMode = false;
            for (let x = 0; x < 40; x++) {
                r.setCharASCII(x, 22, 32, 0);
            }
        }
    }

    _renderDirectoryData(data) {
        const r = this.renderer;
        r.clear();
        r.bgColour = 15;  // light grey (from disassembly: LDA #$0F / STA $D021)
        r.borderColour = 6;  // blue (from disassembly: LDA $8012 = $06 / STA $D020)
        r.setCharset(0);  // uppercase/graphics

        // Parse 6-part directory format from server:
        //   Part 1: Frame header [PETSCII...] $00
        //   Part 2: Footer text [line1 $0D line2 $0D]
        //   Part 3: Field definitions $00
        //   Part 4: Column header/breadcrumb [text...] $00
        //   Part 5: Column headers: field1,field2,...$0D + separator $00
        //   Part 6: Directory entries (CR-terminated lines until end of data)
        let pos = 0;

        // --- Part 1: Skip frame header (until $00) ---
        while (pos < data.length && data[pos] !== 0x00) {
            pos++;
        }
        pos++; // skip $00

        // --- Part 2: Skip footer (two CR-terminated lines) ---
        // Line 1: until $0D
        while (pos < data.length && data[pos] !== 0x0D) {
            pos++;
        }
        pos++; // skip $0D
        // Line 2: until $0D
        while (pos < data.length && data[pos] !== 0x0D) {
            pos++;
        }
        pos++; // skip $0D

        // --- Part 3: Skip field definitions (until $00) ---
        while (pos < data.length && data[pos] !== 0x00) {
            pos++;
        }
        pos++; // skip $00

        // --- Part 4: Extract breadcrumb/routing (until $00) ---
        // This is displayed at row 7 in the directory box.
        // Contains two CR-separated lines (e.g. "    1 *** COMPUNET ***" + page path)
        this.dirTitle = '';
        while (pos < data.length && data[pos] !== 0x00) {
            // Convert PETSCII to displayable char for title extraction
            const b = data[pos];
            if (b === 0x0D) {
                // Second line is the page path - use that as title
                this.dirTitle = '';
            } else if (b >= 0xC1 && b <= 0xDA) {
                this.dirTitle += String.fromCharCode(b - 0x80);
            } else if (b >= 0x41 && b <= 0x5A) {
                this.dirTitle += String.fromCharCode(b);
            } else if (b >= 0x20 && b <= 0x3F) {
                this.dirTitle += String.fromCharCode(b);
            } else {
                this.dirTitle += ' ';
            }
            pos++;
        }
        this.dirTitle = this.dirTitle.trim();
        pos++; // skip $00

        // --- Part 5: Skip column headers (fields,... $0D + separator $00) ---
        while (pos < data.length && data[pos] !== 0x0D) {
            pos++;
        }
        pos++; // skip $0D
        // Skip separator byte + $00
        while (pos < data.length && data[pos] !== 0x00) {
            pos++;
        }
        pos++; // skip $00

        // --- Part 6: Parse directory entries ---
        // Each entry: [6-char page_num][title+type padded ~21 chars] , price , life , author , vote $0D
        this.dirEntries = [];
        while (pos < data.length) {
            // Read one entry line until $0D or end of data
            let lineBytes = [];
            while (pos < data.length && data[pos] !== 0x0D) {
                lineBytes.push(data[pos]);
                pos++;
            }
            if (data[pos] === 0x0D) pos++; // skip $0D

            if (lineBytes.length === 0) continue;

            // Convert PETSCII bytes to string for parsing
            let line = '';
            for (let i = 0; i < lineBytes.length; i++) {
                const b = lineBytes[i];
                if (b >= 0xC1 && b <= 0xDA) {
                    line += String.fromCharCode(b - 0x80);
                } else if (b >= 0x41 && b <= 0x5A) {
                    line += String.fromCharCode(b);
                } else if (b >= 0x20 && b <= 0x3F) {
                    line += String.fromCharCode(b);
                } else {
                    line += ' ';
                }
            }

            // Split on commas: first field is page_num+title+type, then price, life, author, vote
            const parts = line.split(',');
            if (parts.length < 2) continue;

            const titleField = parts[0]; // "  nnnn title........type"

            // First 6 chars = page number
            const pageNum = titleField.substring(0, 6).trim();

            // Chars 6 onwards = title + type (title is left-aligned, type is at the end)
            const titleType = titleField.substring(6);
            // Type is the last 3 chars of the title+type field
            const type = titleType.substring(titleType.length - 3).trim();
            const title = titleType.substring(0, titleType.length - 3).trim();

            this.dirEntries.push({
                pageNum: pageNum,
                title: title,
                type: type,
                price: (parts[1] || '').trim(),
                life: (parts[2] || '').trim(),
                author: (parts[3] || '').trim(),
                vote: (parts[4] || '').trim(),
            });
        }

        this.dirHighlight = 0;
        this.dirColumn = 0; // 0=price, 1=life, 2=author, 3=vote

        this._drawDirectory();
        this.duckshoot.setCommands(DUCKSHOOT_DIRECTORY);
        this.duckshoot.show();
    }
    
    _drawDirectory() {
        const r = this.renderer;
        
        // Clear screen area (rows 0-22)
        for (let y = 0; y < 23; y++) {
            for (let x = 0; x < 40; x++) {
                const idx = y * 40 + x;
                r.screenChars[idx] = 32;
                r.screenColours[idx] = 0;
            }
        }
        
        // Row 7, col 1: Routing/directory title (blue) - from SUB_A544
        if (this.dirTitle) {
            r.printAt(1, 7, this.dirTitle, 6);
        }
        
        // Row 8, col 31: Column header - from SUB_A56E
        const colHeaders = ['PRICE', 'LIFE', 'AUTHOR', 'VOTE'];
        r.printAt(31, 8, colHeaders[this.dirColumn], 6);
        
        // Directory entries starting at row 10 (from disassembly: ADC #$0A)
        const startRow = 10;
        for (let i = 0; i < this.dirEntries.length && i + startRow < 22; i++) {
            const entry = this.dirEntries[i];
            const row = startRow + i;
            
            // From SUB_A661:
            // First 6 chars: page number, in background colour (dim)
            const numStr = entry.pageNum.padStart(6);
            r.printAt(0, row, numStr, 6); // blue (same as bg-ish)
            
            // From disassembly SUB_A6D9: highlight colour is red at position 0, blue otherwise
            // Non-highlighted entries are always blue
            const titleColour = (i === this.dirHighlight && this.dirHighlight === 0) ? 2 : 6;
            r.printAt(7, row, entry.title.substring(0, 20), titleColour);
            
            // Type (after title) - same colour as title
            const typeColour = titleColour;
            r.printAt(28, row, entry.type.substring(0, 5), typeColour);
            
            // Extra column at column 31 (from disassembly: LDY #$1F)
            let extraVal = '';
            let extraCol = 6;
            switch (this.dirColumn) {
                case 0: extraVal = entry.price; extraCol = 7; break;
                case 1: extraVal = entry.life; extraCol = 5; break;
                case 2: extraVal = entry.author; extraCol = 3; break;
                case 3: extraVal = entry.vote; extraCol = 2; break;
            }
            if (extraVal) {
                r.printAt(31, row, extraVal.substring(0, 8), extraCol);
            }
            
            // Highlight: reverse video (OR with $80) across columns 0-38
            // From disassembly: ORA #$80 applied to screen codes
            if (i === this.dirHighlight) {
                for (let x = 0; x < 39; x++) {
                    const idx = row * 40 + x;
                    r.screenChars[idx] |= 128;
                    r.screenColours[idx] = 14; // light blue bar
                }
            }
        }
    }

    _renderSeqFrame() {
        if (!this._seqFrames) return;
        const seq = new SEQRenderer(this.renderer);
        seq.render(this._seqFrames[this._seqFrameIndex], 25);
    }

    _updateSeqInfo() {
        const el = document.getElementById('seq-info');
        if (el && this._seqFrames) {
            el.textContent = `Frame ${this._seqFrameIndex + 1} of ${this._seqFrames.length}`;
        }
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
            r.setCharASCII(this.cursorX, this.cursorY, e.key.charCodeAt(0), this.currentColour);
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
                
            case 'FINISH':
                this.duckshoot.setCommands(DUCKSHOOT_EDITOR);
                this.duckshoot.render();
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

            // Split multi-frame SEQ files into individual frames.
            // Two formats exist:
            //   Server/4Rich: $00 [border] [bg] [content...] $00 (flags byte is $00)
            //   Historical:   [border] [bg] [content...] $00 (no flags byte)
            // Detect by checking if first byte is $00 (flags) and bytes 1-2 have
            // high nibble $F0 (colour OR mask).
            const frames = [];
            const serverFormat = data[0] === 0x00 && data.length > 2 &&
                                (data[1] & 0xF0) === 0xF0 && (data[2] & 0xF0) === 0xF0;
            if (serverFormat) {
                // Frames start with $00 flags byte; split on $00 that follows content
                let i = 0;
                while (i < data.length) {
                    if (data[i] !== 0x00) { i++; continue; }
                    // Found a $00 flags byte — scan for terminating $00
                    let frameStart = i;
                    i++; // skip flags
                    while (i < data.length && data[i] !== 0x00) i++;
                    // i now points to terminating $00 (or end of file)
                    if (i > frameStart + 1) {
                        frames.push(data.slice(frameStart, i + 1));
                    }
                    i++; // skip terminator
                }
            } else {
                // Historical format: no flags byte, split on $00, prepend marker
                let start = 0;
                for (let i = 0; i < data.length; i++) {
                    if (data[i] === 0x00) {
                        if (i > start) {
                            const frame = new Uint8Array(i - start + 1);
                            frame[0] = 0x00;
                            frame.set(data.slice(start, i), 1);
                            frames.push(frame);
                        }
                        start = i + 1;
                    }
                }
            }
            // Filter out preamble-only frames (just header bytes, no content)
            const filtered = frames.filter(f => f.length > 5);
            if (filtered.length > 0) {
                frames.length = 0;
                frames.push(...filtered);
            }
            if (frames.length === 0) {
                frames.push(data);
            }

            // Store frames and render first
            t._seqFrames = frames;
            t._seqFrameIndex = 0;
            t._renderSeqFrame();

            t.state = 'editor';
            t.duckshoot.setCommands(DUCKSHOOT_SHOW);
            t.duckshoot.show();
            t._updateSeqInfo();
        };
        reader.readAsArrayBuffer(file);
    });

    document.getElementById('seq-prev').addEventListener('click', () => {
        const t = window.terminal;
        if (!t._seqFrames || t._seqFrameIndex <= 0) return;
        t._seqFrameIndex--;
        t._renderSeqFrame();
        t._updateSeqInfo();
    });

    document.getElementById('seq-next').addEventListener('click', () => {
        const t = window.terminal;
        if (!t._seqFrames || t._seqFrameIndex >= t._seqFrames.length - 1) return;
        t._seqFrameIndex++;
        t._renderSeqFrame();
        t._updateSeqInfo();
    });
});
