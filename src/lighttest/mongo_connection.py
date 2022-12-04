"""
A szerver ás adatbáziskapcsoalt létrehozása és konfigurálása
"""

from pymongo import mongo_client as mc


class Mongo:
    dialect_driver: str = "mongodb"
    client_url: str = "localhost:27017"
    default_mongo_client: str = f'mongodb://localhost:27017'
    default_db: str = "default"
    current_client: str = default_mongo_client
    current_database = default_db

    client = mc.MongoClient(default_mongo_client)

    database = client[default_db]
    collection = database["teszt"]

    @staticmethod
    def set_client(new_client_url: str) -> None:
        Mongo.client_url = new_client_url
        Mongo.client = mc.MongoClient(f'{Mongo.dialect_driver}://{Mongo.client_url}')
        Mongo.current_client = f'{Mongo.dialect_driver}://{Mongo.client_url}'

    @staticmethod
    def set_dialect_driver(new_dialect_driver: str) -> None:
        Mongo.dialect_driver = new_dialect_driver
        Mongo.set_client(Mongo.client_url)
        Mongo.current_client = f'{Mongo.dialect_driver}://{Mongo.client_url}'

    @staticmethod
    def set_database(database_name: str):
        Mongo.database = Mongo.client[database_name]
        Mongo.current_database = database_name

    @staticmethod
    def set_collection(collection_name: str):
        Mongo.collection = Mongo.database[collection_name]
