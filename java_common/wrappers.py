from java.util.function import Predicate, Consumer, Function


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
