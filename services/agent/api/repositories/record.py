class Record(dict):
    """Linha de diagnóstico com acesso por nome ou posição."""

    def __getitem__(self, key):
        return (
            list(self.values())[key]
            if isinstance(key, int)
            else super().__getitem__(key)
        )
