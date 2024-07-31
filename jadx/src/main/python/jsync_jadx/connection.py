from java.net import Socket
from org.slf4j import Logger

from java_common.connection import JavaConnection


class JADXConnection(JavaConnection):
    def __init__(self, jsync, logger, sock):
        # type: ('JSync', Logger, Socket) -> None
        super(JADXConnection, self).__init__(sock)
        self._jsync = jsync
        self._logger = logger

    def close(self, on_exception=False):
        # type: (bool) -> None
        super(JADXConnection, self).close()
        if on_exception:
            self._logger.error("[JSync] Closing connection due to exception.")
            self._jsync.clean()
