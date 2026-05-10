"""
Simple echo server for testing VICE ACIA connectivity.
Sends 'HELLO' on connection, then echoes back anything received.
Listens on port 6400.
"""
import asyncio

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f'Connected: {addr}')
    
    # Wait 2 seconds for tcpser break delay to expire
    await asyncio.sleep(2.0)
    
    # Send greeting
    writer.write(b'HELLO\r\n')
    await writer.drain()
    print('Sent: HELLO')
    
    try:
        while True:
            data = await reader.read(256)
            if not data:
                break
            hex_str = data.hex()
            printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
            print(f'RX: {len(data)} bytes: {hex_str} [{printable}]')
            
            # Echo it back
            writer.write(data)
            await writer.drain()
            print(f'TX: echoed {len(data)} bytes')
    except (ConnectionResetError, BrokenPipeError):
        pass
    
    print(f'Disconnected: {addr}')
    writer.close()

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 6400)
    print('Echo server listening on port 6400')
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
