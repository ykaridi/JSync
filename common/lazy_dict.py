class LazyDict(object):
    def __init__(self, mapping):
        # type: (callable) -> None
        self._mapping = mapping
        self._dict = {}

    def __getitem__(self, item):
        if item not in self._dict:
            self._dict[item] = self._mapping(item)

        return self._dict[item]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)
