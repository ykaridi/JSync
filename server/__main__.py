import argparse
import asyncio
from pathlib import Path

from server.default_symbol_server import DefaultSymbolServer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="jsync-server", description="JSync Server")
    parser.add_argument("-d", "--directory", type=Path, required=True, help="Directory for symbol stores")
    parser.add_argument("-p", "--port", type=int, default=9501, help="Port to listen on")
    parser.add_argument("-r", "--resources", type=Path, default=None, help="Path to resources directory or ZIP")

    args = parser.parse_args()
    port = args.port
    directory = args.directory
    resources = args.resources

    if resources is None:
        this_file = Path(__file__).absolute()
        parent = this_file.parent
        if parent.exists() and parent.suffix == '.zip':
            resources = parent
        else:
            raise ValueError('Must specify resources directory / zip')

    server = DefaultSymbolServer("0.0.0.0", port, directory, resources)
    asyncio.run(server.serve_forever())
