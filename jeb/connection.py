from java.net import Socket

from java_common.connection import JavaConnection


class JEBConnection(JavaConnection):
    def __init__(self, jsync, sock):
        # type: ('JSync', Socket) -> None
        super(JEBConnection, self).__init__(sock)
        self._jsync = jsync

    def close(self, on_exception=False):
        # type: (bool) -> None
        super(JEBConnection, self).close()
        if on_exception:
            print("[JSync] Closing connection due to exception.")
            self._jsync.clean()
