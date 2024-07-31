from java.util.function import Predicate, Consumer, Function
from java.lang import Runnable


class JavaConsumer(Consumer):
    def __init__(self, fn):
        # type: (callable) -> None
        self.accept = fn


class JavaFunction(Function):
    def __init__(self, fn):
        # type: (callable) -> None
        self.apply = fn


class JavaPredicate(Predicate):
    def __init__(self, fn):
        # type: (callable) -> None
        self.test = fn


class ThreadWrapper(Runnable):
    def __init__(self, target, *args, **kwargs):
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        self._target(*self._args, **self._kwargs)
