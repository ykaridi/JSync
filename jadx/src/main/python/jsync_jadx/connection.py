from org.slf4j import Logger

from java_common.connection import JavaConnection


class JADXConnection(JavaConnection):
    def __init__(self, jsync, logger, host, port, name):
        # type: ('JSync', Logger, str, int, str) -> None
        JavaConnection.__init__(self, host, port, name)
        self._jsync = jsync
        self._logger = logger

    def close(self, on_exception=False):
        # type: (bool) -> None
        super(JADXConnection, self).close()
        if on_exception:
            self._logger.error("[JSync] Closing connection due to exception.")
            self._jsync.clean()
