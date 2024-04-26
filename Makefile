.PHONY: *

all: init client server

clean:
	@echo "Cleaning dist/ folder"
	rm -rf dist

init:
	@echo "Creating dist/ folder"
	mkdir -p dist

client:
	@echo "Packing JEBSync.py"
	(awk '/^#/ {print} !/^#/ {exit}' < client/jebsync.py &&\
	 echo && echo &&\
	 python3 -m pybunch -r . -e client.jebsync -so) > dist/JEBSync.py

server:
	@echo "Packing server.py"
	python3 -m pybunch -r . -e server.__main__ -so -o dist/server.py
