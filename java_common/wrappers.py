from java.util.function import Predicate, Consumer, Function


class JavaConsumer(Consumer):
    def __init__(self, fn):
        self.accept = fn


class JavaFunction(Function):
    def __init__(self, fn):
        self.apply = fn


class JavaPredicate(Predicate):
    def __init__(self, fn):
        self.test = fn
