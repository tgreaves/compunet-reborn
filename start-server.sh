#!/bin/bash
# Start the Compunet server with logging
cd "$(dirname "$0")/server"
python3 compunet_server.py 2>&1 | tee ../client/c64/logs/compunet-server.log
