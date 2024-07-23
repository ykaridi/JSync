.PHONY: *

all: init jeb jadx server

clean:
	@echo "Cleaning project"
	rm -rf dist
	find . -regex '^.*\(__pycache__\|\.py[co]\)$$' -delete
	jadx/gradlew -p jadx clean

init:
	@echo "Creating dist/ folder"
	mkdir -p dist

jeb:
	@echo "Packing JEB plugin"
	(awk '/^#/ {print} !/^#/ {exit}' < jeb/JSync.py &&\
	 echo && echo &&\
	 pybunch -p common -p java_common -p client_base -p jeb -e jeb.JSync -so) > dist/JSync.py

jadx:
	@echo "Building JADX plugin"
	jadx/gradlew -p jadx

server:
	@echo "Packing Server"
	pybunch -p common -p server -e server -so -o dist/jsync-server.py
