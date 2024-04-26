# JEBSync

A python plugin for JEB which allows synchronizing symbols across multiple JEB instances.
Allows teams to collaborate on JEB decompilation projects.

## Setup
1. Download client and server scripts from [latest release](https://github.com/ykaridi/JEBSync/releases/latest)
2. Place [JEBSync.py](https://github.com/ykaridi/JEBSync/releases/latest/download/JEBSync.py) 
in JEB's scripts folder
3. Download [server.py](https://github.com/ykaridi/JEBSync/releases/latest/download/server.py)
and run ```python3 server.py -d <stores_directory> (-p <port>)```
4. Run JEBSync script in JEB and connect to server with a username of your choice
