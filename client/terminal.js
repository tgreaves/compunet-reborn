/**
 * Compunet Terminal - main application logic.
 * Ties together the PETSCII renderer and duckshoot menu.
 */

class CompunetTerminal {
    constructor() {
        this.canvas = document.getElementById('screen');
        this.renderer = new PETSCIIRenderer(this.canvas);
        this.duckshoot = new Duckshoot(this.renderer);
        
        // Terminal state
        this.state = 'boot'; // boot, directory, show, editor, mail
        this.currentPage = null;
        
        // Set up keyboard handler
        document.addEventListener('keydown', (e) => this.handleKey(e));
        
        // Set up duckshoot callback
        this.duckshoot.onSelect = (cmd) => this.handleCommand(cmd);
        
        // Boot sequence
        this.boot();
    }
    
    boot() {
        const r = this.renderer;
        
        // Set Compunet colours (from ROM: background=1 white initially,
        // but the terminal uses blue background with white text)
        r.bgColour = 6;       // Blue background
        r.borderColour = 14;  // Light blue border
        r.textColour = 1;     // White text
        r.clear();
        
        // Display boot message (from ROM version string at $807A)
        r.cursorY = 2;
        r.cursorX = 0;
        r.print(' COMPUNET TERMINAL 1.22\n', 1);
        r.print(' SEPTEMBER 1984 ARIADNE SOFTWARE LTD.\n', 1);
        r.print('\n');
        r.print(' Compunet Reborn - Web Terminal\n', 15);
        r.print('\n');
        
        // Simulate the login sequence
        r.print('  COMPUNET SYSTEM LOGON.\n', 1);
        r.print('\n');
        r.print('  ENTER USER ID: ', 1);
        r.print('NEW-USER\n', 7);
        r.print('\n');
        r.print('  PASSWORD: ', 1);
        r.print('****\n', 7);
        r.print('\n');
        r.print('  LINKING', 1);
        
        // After a brief delay, show the directory
        setTimeout(() => {
            r.print('...DONE\n', 5);
            setTimeout(() => this.showDirectory(), 500);
        }, 1000);
        
        r.render();
        this._startRenderLoop();
    }
    
    showDirectory() {
        const r = this.renderer;
        r.clear();
        
        // Set directory colours
        r.bgColour = 6;
        r.borderColour = 14;
        r.textColour = 1;
        
        // Display a sample directory (based on the manual's description)
        r.cursorX = 0;
        r.cursorY = 0;
        
        // Routing header
        r.print('  COMPUNET MAIN DIRECTORY\n', 7);
        r.print('\n', 1);
        
        // Directory entries (format: page_num TITLE type+size)
        const entries = [
            { page: '100', title: 'WELCOME', type: 'T8+' },
            { page: '107', title: 'COMPUNET NEWS', type: 'T+' },
            { page: '120', title: 'FULL GUIDE', type: 'T12+' },
            { page: '140', title: 'COURIER GUIDE', type: 'T6' },
            { page: '150', title: 'INDEX', type: 'D+' },
            { page: '202', title: 'NEWS', type: 'T+' },
            { page: '210', title: 'COMMODORE NEWS', type: 'T+' },
            { page: '231', title: 'TELESOFTWARE', type: 'P+' },
            { page: '310', title: 'TELESHOPPING', type: 'S+' },
            { page: '600', title: 'GENERAL JUNGLE', type: 'D+' },
            { page: '2020', title: 'COMMS SOFTWARE', type: 'P6+' },
        ];
        
        this.directoryEntries = entries;
        this.selectedEntry = 0;
        
        this._renderDirectoryEntries();
        
        // Show directory duckshoot
        this.state = 'directory';
        this.duckshoot.setCommands(DUCKSHOOT_DIRECTORY);
        this.duckshoot.show();
    }
    
    _renderDirectoryEntries() {
        const r = this.renderer;
        const entries = this.directoryEntries;
        const startRow = 2;
        
        for (let i = 0; i < entries.length && i + startRow < 22; i++) {
            const entry = entries[i];
            const row = startRow + i;
            const isSelected = (i === this.selectedEntry);
            
            // Clear row
            for (let x = 0; x < r.cols; x++) {
                r.setChar(x, row, 32, 1);
            }
            
            // Page number
            const pageStr = entry.page.padStart(5);
            r.printAt(1, row, pageStr, isSelected ? 1 : 15);
            
            // Title
            r.printAt(7, row, entry.title, isSelected ? 1 : 14);
            
            // Type
            r.printAt(32, row, entry.type, isSelected ? 1 : 13);
            
            // Highlight bar for selected entry
            if (isSelected) {
                for (let x = 0; x < r.cols; x++) {
                    const idx = row * r.cols + x;
                    // Swap to reverse video effect (blue text on white bg)
                    // We'll simulate this by using a different colour scheme
                    r.screenColours[idx] = r.screenColours[idx]; // keep colour but we'll render bg differently
                }
            }
        }
    }
    
    showPage(title) {
        const r = this.renderer;
        r.clear();
        r.bgColour = 1;  // White background for pages
        r.textColour = 0; // Black text
        r.borderColour = 6; // Blue border
        
        r.cursorX = 0;
        r.cursorY = 0;
        r.print('  ' + title + '\n', 0);
        r.print('\n');
        r.print('  This is a sample Compunet page.\n', 0);
        r.print('  The original system delivered frames\n', 0);
        r.print('  containing PETSCII graphics, text,\n', 0);
        r.print('  and colour information.\n', 0);
        r.print('\n');
        r.print('  Pages were created using the built-in\n', 0);
        r.print('  Editor with full C64 graphics.\n', 0);
        
        // Show the SHOW duckshoot
        this.state = 'show';
        this.duckshoot.setCommands(DUCKSHOOT_SHOW);
        this.duckshoot.show();
    }
    
    handleKey(e) {
        // Prevent default for arrow keys and enter
        if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter'].includes(e.key)) {
            e.preventDefault();
        }
        
        // Directory navigation with up/down
        if (this.state === 'directory') {
            if (e.key === 'ArrowUp' && this.selectedEntry > 0) {
                this.selectedEntry--;
                this._renderDirectoryEntries();
                return;
            }
            if (e.key === 'ArrowDown' && this.selectedEntry < this.directoryEntries.length - 1) {
                this.selectedEntry++;
                this._renderDirectoryEntries();
                return;
            }
        }
        
        // Pass to duckshoot
        this.duckshoot.handleKey(e.key);
    }
    
    handleCommand(cmd) {
        switch (cmd) {
            case 'SHOW':
                if (this.state === 'directory' && this.directoryEntries) {
                    const entry = this.directoryEntries[this.selectedEntry];
                    if (entry.type.startsWith('T')) {
                        this.showPage(entry.title);
                    }
                }
                break;
                
            case 'DIR':
                if (this.state === 'directory' && this.directoryEntries) {
                    const entry = this.directoryEntries[this.selectedEntry];
                    if (entry.type.includes('+')) {
                        // Would navigate to sub-directory
                        this._showStatus('DIR: ' + entry.title);
                    }
                }
                break;
                
            case 'FINISH':
            case 'BACK':
                this.showDirectory();
                break;
                
            case 'MORE':
                this._showStatus('No more pages');
                break;
                
            case 'GOTO':
                this._showStatus('GOTO: Enter page number');
                break;
                
            case 'HELP':
                this._showHelp();
                break;
                
            case 'LEAVE':
                this._showStatus('DISCONNECTED');
                break;
                
            case 'ACCNT':
                this._showStatus('YOU ARE 0.00 IN CREDIT');
                break;
                
            case 'VOTE':
                this._showStatus('VOTE (1-9)?');
                break;
                
            case 'BUY':
                if (this.state === 'directory' && this.directoryEntries) {
                    const entry = this.directoryEntries[this.selectedEntry];
                    if (entry.type.startsWith('P')) {
                        this._showStatus('DOWNLOADING ' + entry.title + '...');
                    } else {
                        this._showStatus('Cannot BUY text entries - use SHOW');
                    }
                }
                break;
                
            case 'MAIL':
                this._showStatus('No mail waiting');
                break;
                
            case 'EDITR':
                this._enterEditor();
                break;
                
            default:
                this._showStatus(cmd + ': Not yet implemented');
                break;
        }
    }
    
    _showStatus(message) {
        const r = this.renderer;
        // Display status message on row 22
        for (let x = 0; x < r.cols; x++) {
            r.setChar(x, 22, 32, 1);
        }
        r.printAt(1, 22, message, 7); // Yellow
    }
    
    _showHelp() {
        const r = this.renderer;
        r.clear();
        r.bgColour = 6;
        r.textColour = 1;
        
        r.cursorX = 0;
        r.cursorY = 1;
        r.print(' COMPUNET HELP\n\n', 7);
        r.print(' Use LEFT/RIGHT to scroll the\n', 1);
        r.print(' duckshoot menu at the bottom.\n', 1);
        r.print(' Press RETURN to select.\n\n', 1);
        r.print(' Use UP/DOWN to highlight\n', 1);
        r.print(' directory entries.\n\n', 1);
        r.print(' Commands:\n', 7);
        r.print('  SHOW  - Read text pages\n', 14);
        r.print('  DIR   - Enter sub-directory\n', 14);
        r.print('  BACK  - Go up one level\n', 14);
        r.print('  GOTO  - Jump to page number\n', 14);
        r.print('  BUY   - Download programs\n', 14);
        r.print('  MAIL  - Access Courier\n', 14);
        r.print('  ACCNT - Account details\n', 14);
        r.print('  LEAVE - Disconnect\n', 14);
        
        this.state = 'show';
        this.duckshoot.setCommands(['FINISH']);
        this.duckshoot.show();
    }
    
    _enterEditor() {
        const r = this.renderer;
        r.clear();
        r.bgColour = 1;  // White background
        r.borderColour = 6;
        r.textColour = 0;
        
        r.cursorX = 0;
        r.cursorY = 0;
        
        this.state = 'editor';
        this.duckshoot.setCommands(DUCKSHOOT_EDITOR);
        this.duckshoot.show();
    }
    
    _startRenderLoop() {
        const loop = () => {
            this.renderer.render();
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }
}

// Start the terminal when the page loads
window.addEventListener('DOMContentLoaded', () => {
    window.terminal = new CompunetTerminal();
});
