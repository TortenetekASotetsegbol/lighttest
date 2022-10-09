"""
A szerver ás adatbáziskapcsoalt létrehozása és konfigurálása
"""

from pymongo import mongo_client as mc


class Mongo:
    default_mongo_client: str = "mongodb://localhost:27017"
    default_db: str = "default"
    current_client = default_mongo_client
    current_database = default_db

    client = mc.MongoClient(default_mongo_client)
    database = client[default_db]
    collection = database["teszt"]

    @staticmethod
    def set_client(client_url: str) -> None:
        Mongo.client = mc.MongoClient(f'mongodb://{client_url}')
        Mongo.current_client = f'mongodb://{client_url}'

    @staticmethod
    def set_database(database_name: str):
        Mongo.database = Mongo.client[database_name]
        Mongo.current_database = database_name

    @staticmethod
    def set_collection(collection_name: str):
        Mongo.collection = Mongo.database[collection_name]
