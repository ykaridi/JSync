import os

from client_base.config import JSYNC_ROOT


JSYNC_JEB_ROOT = os.path.join(JSYNC_ROOT, 'jeb')
if not os.path.exists(JSYNC_JEB_ROOT):
    os.makedirs(JSYNC_JEB_ROOT)
