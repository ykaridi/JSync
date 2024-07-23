import os


DATA_ROOT = os.path.expanduser("~/.jsync/jeb")
if not os.path.exists(DATA_ROOT):
    os.makedirs(DATA_ROOT)
