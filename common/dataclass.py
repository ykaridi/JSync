class Dataclass(object):
    def description(self, descriptor=str):
        # type: (str | repr) -> str
        return "%s(%s)" % (self.__class__.__name__, ', '.join("%s=%s" % (k, descriptor(v))
                                                              for k, v in vars(self).items()))

    def __str__(self):
        # type: () -> str
        return self.description(descriptor=repr)

    def __repr__(self):
        # type: () -> str
        return self.description(descriptor=repr)

    def clone(self, **kwargs):
        v = vars(self)
        v.update(kwargs)
        cls = type(self)
        return cls(**v)
