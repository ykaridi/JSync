#!/bin/sh
mkdir -p dist
python3 -m pybunch -r . -e server.__main__ -so -o dist/server.py
