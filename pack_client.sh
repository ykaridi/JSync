#!/bin/bash
mkdir -p dist
( (awk '/^#/ {print} !/^#/ {exit}' < client/jebsync.py) &&\
 echo -ne "\n\n" &&\
 python3 -m pybunch -r . -e client.jebsync -so) > dist/JEBSync.py
