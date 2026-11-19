from microservice_toolkit import Repository

from services.persistence.database import database


class ApplicationRepository(Repository):
    def __init__(self):
        super().__init__(database)
