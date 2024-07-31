import os

from client_base.config import JSYNC_ROOT


JSYNC_JADX_ROOT = os.path.join(JSYNC_ROOT, 'jadx')
if not os.path.exists(JSYNC_JADX_ROOT):
    os.makedirs(JSYNC_JADX_ROOT)
