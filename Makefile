.PHONY: *

all: init jeb jadx server

clean:
	@echo "Cleaning project"
	rm -rf dist
	rm -rf dist-resources
	find . -regex '^.*\(__pycache__\|\.py[co]\)$$' -delete
	jadx/gradlew -p jadx clean

init:
	@echo "Creating dist/ folder"
	mkdir -p dist

jeb: init
	@echo "Packing JEB plugin"
	(awk '/^#/ {print} !/^#/ {exit}' < jeb/JSync.py &&\
	 echo && echo &&\
	 pybunch -p common -p java_common -p client_base -p jeb -e jeb.JSync -so) > dist/JSync.py

jadx: init
	@echo "Building JADX plugin"
	jadx/gradlew -p jadx build
	cp jadx/build/libs/JSync.jar dist/JSync.jar

server: init
	@echo "Downloading needed resources"
	mkdir -p dist-resources
	if [ ! -f "dist-resources/slf4j.jar" ]; then \
		wget https://search.maven.org/remotecontent?filepath=org/slf4j/slf4j-api/1.7.36/slf4j-api-1.7.36.jar \
 				-O dist-resources/slf4j.jar; \
	fi

	if [ ! -f "dist-resources/sqlite-jdbc.jar" ]; then \
		wget https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/3.46.0.1/sqlite-jdbc-3.46.0.1.jar \
				-O dist-resources/sqlite-jdbc.jar; \
	fi

	@echo "Packing server"
	rm -rf dist/server_zip
	mkdir dist/server_zip
	ln -s ../../dist-resources dist/server_zip/
	ln -s ../../server dist/server_zip/
	ln -s ../../server/__main__.py dist/server_zip/
	ln -s ../../common dist/server_zip/
	cd dist/server_zip && zip -r ../jsync-server.zip *
	rm -rf dist/server_zip

