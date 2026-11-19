import os

from microservice_toolkit import Database

database = Database(lambda: os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1), connect_args={"connect_timeout": 3})
