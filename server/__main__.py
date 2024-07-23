import argparse
import asyncio
from pathlib import Path

from .default_symbol_server import DefaultSymbolServer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="jsync-server", description="JSync Server")
    parser.add_argument("-d", "--directory", type=Path, required=True, help="Directory for symbol stores")
    parser.add_argument("-p", "--port", type=int, default=9501, help="Port to listen on")

    args = parser.parse_args()
    port = args.port
    directory = args.directory

    server = DefaultSymbolServer("0.0.0.0", port, directory)
    asyncio.run(server.serve_forever())
