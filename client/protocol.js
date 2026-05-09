/**
 * Compunet Protocol Client
 * 
 * Speaks the same binary protocol as the C64 client over WebSocket.
 * 
 * Client -> Server:
 *   Command packets: byte 0 = command letter, bytes 1+ = params
 *   GOTO: 'G' + page number as ASCII digits
 *   SELECT: 'S' + index byte
 *   Login: user_id + $00 + password + $00
 * 
 * Server -> Client:
 *   $41 'A' = ACK
 *   $44 'D' = Directory listing (PETSCII stream, $00 terminated)
 *   $46 'F' = Frame data (SEQ format, $00 terminated)
 *   $45 'E' = Error message (PETSCII, $00 terminated)
 *   $4C 'L' = Linking required
 */

class CompunetProtocol {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.onDirectory = null;   // callback(data) - raw bytes of directory listing
        this.onFrame = null;       // callback(data) - raw bytes of frame
        this.onError = null;       // callback(data) - raw bytes of error message
        this.onAck = null;         // callback()
        this.onDisconnect = null;  // callback()
        this.onConnect = null;     // callback()
    }
    
    /**
     * Connect to the Compunet server.
     */
    connect(url) {
        if (!url) {
            url = 'ws://localhost:6502';
        }
        
        this.ws = new WebSocket(url);
        this.ws.binaryType = 'arraybuffer';
        
        this.ws.onopen = () => {
            this.connected = true;
            if (this.onConnect) this.onConnect();
        };
        
        this.ws.onmessage = (event) => {
            const data = new Uint8Array(event.data);
            this._handleResponse(data);
        };
        
        this.ws.onclose = () => {
            this.connected = false;
            if (this.onDisconnect) this.onDisconnect();
        };
        
        this.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            this.connected = false;
        };
    }
    
    /**
     * Send login credentials.
     */
    login(userId, password) {
        const encoder = new TextEncoder();
        const userBytes = encoder.encode(userId);
        const passBytes = encoder.encode(password);
        const packet = new Uint8Array(userBytes.length + 1 + passBytes.length + 1);
        packet.set(userBytes, 0);
        packet[userBytes.length] = 0x00;
        packet.set(passBytes, userBytes.length + 1);
        packet[packet.length - 1] = 0x00;
        this.ws.send(packet.buffer);
    }
    
    /**
     * Send a command (same as C64 terminal_app).
     * cmd = single character command letter
     * params = Uint8Array of parameter bytes (optional)
     */
    sendCommand(cmd, params) {
        const cmdByte = cmd.charCodeAt(0);
        const packet = new Uint8Array(1 + (params ? params.length : 0));
        packet[0] = cmdByte;
        if (params) {
            packet.set(params, 1);
        }
        this.ws.send(packet.buffer);
    }
    
    /**
     * Send DIR command.
     */
    sendDir() {
        this.sendCommand('D');
    }
    
    /**
     * Send SHOW command.
     */
    sendShow() {
        this.sendCommand('P');
    }
    
    /**
     * Send BACK command.
     */
    sendBack() {
        this.sendCommand('C');
    }
    
    /**
     * Send ACCNT command.
     */
    sendAccnt() {
        this.sendCommand('A');
    }
    
    /**
     * Send MAIL command.
     */
    sendMail() {
        this.sendCommand('M');
    }
    
    /**
     * Send VOTE command.
     */
    sendVote(value) {
        const params = new Uint8Array([0, 0, value + 0x30]); // vote as ASCII digit
        this.sendCommand('V', params);
    }
    
    /**
     * Send GOTO page number.
     */
    sendGoto(pageNum) {
        const encoder = new TextEncoder();
        const numStr = encoder.encode(pageNum.toString());
        const packet = new Uint8Array(1 + numStr.length);
        packet[0] = 0x47; // 'G'
        packet.set(numStr, 1);
        this.ws.send(packet.buffer);
    }
    
    /**
     * Send SELECT (highlight change).
     */
    sendSelect(index) {
        const packet = new Uint8Array([0x53, index]); // 'S' + index
        this.ws.send(packet.buffer);
    }
    
    /**
     * Handle a response from the server.
     */
    _handleResponse(data) {
        if (data.length === 0) return;
        
        const responseType = data[0];
        const payload = data.slice(1);
        
        switch (responseType) {
            case 0x41: // ACK
                if (this.onAck) this.onAck();
                break;
            
            case 0x44: // Directory
                if (this.onDirectory) this.onDirectory(payload);
                break;
            
            case 0x46: // Frame
                if (this.onFrame) this.onFrame(payload);
                break;
            
            case 0x45: // Error
                if (this.onError) this.onError(payload);
                break;
            
            case 0x4C: // Linking
                // For web client, we don't need linking - just acknowledge
                console.log('Server requested linking (ignored for web client)');
                break;
            
            default:
                console.warn('Unknown response type:', responseType.toString(16));
                break;
        }
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.connected = false;
        }
    }
}
