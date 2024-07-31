# JSync

A product allowing collaboration on Java decompilation projects (like Android applications) across multiple users (using either JEB or JADX, the leading products); Allows teams to collaborate on such decompilation projects.

## Setup
1. Download [server.py](https://github.com/ykaridi/JSync/releases/latest/download/jsync-server.py)
and run ```python3 jsync-server.py -d <stores_directory> (-p <port>)```
2. Download [jsync.py](https://github.com/ykaridi/JSync/releases/latest/download/jsync.py) and place in JEB's scripts folder (Make sure to run new enough JEB!)
3. Download [jsync.jar](https://github.com/ykaridi/JSync/releases/latest/download/jsync.jar) and install it as a JADX plugin

### Custom Rename Mechanics
The default mechanic for choosing the *most relevant* rename is simply choosing the latest.
It is possible to override this behaviour by creating a file in `~/.jsync/symbol_evaluator.py` which defines the following function
```python
def evaluate_symbol(symbols, self_author):
    # type: (list[Symbol], str) -> Symbol
    raise NotImplementedError
```

An example implementation might be 
```python
def evaluate_symbol(symbols, self_author):
	my_symbol = next((symbol for symbol in symbols if symbol.author == self_author), None)
	if my_symbol:
		return my_symbol
	
	latest = max(symbols, key=lambda symbol: symbol.timestamp)
	return latest.clone(name='%s_%s' % (latest.author[0], latest.name))
```

## Development
For stub generation, run (from within the `typings` directory)
```bash
python3 -m pip install requirements.txt
python3 generate_stubs.py --jeb <path to jeb installation> --jadx <path to jadx build>
```
