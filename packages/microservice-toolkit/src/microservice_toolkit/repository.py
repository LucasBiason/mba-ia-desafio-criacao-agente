class Repository:
    def __init__(self, database):
        self.database = database
        self.session = None

    def __enter__(self):
        self.session = self.database.session()
        self.session.begin()
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            if exception_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        except Exception:
            self.session.rollback()
            raise
        finally:
            self.session.close()
