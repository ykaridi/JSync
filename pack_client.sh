#!/bin/bash
mkdir -p dist
python3 -m pybunch -r . -e client.jebsync -so -o dist/_JEBSync.py &&
cat client/jebsync_headers.py dist/_JEBSync.py > dist/JEBSync.py &&
rm dist/_JEBSync.py
