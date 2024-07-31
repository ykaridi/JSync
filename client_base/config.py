import os


JSYNC_ROOT = os.path.expanduser("~/.jsync")
if not os.path.exists(JSYNC_ROOT):
    os.makedirs(JSYNC_ROOT)
