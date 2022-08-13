'''
A szerver ás adatbáziskapcsoalt létrehozása és konfigurálása
'''

from pymongo import mongo_client as m

default_mongo_client = "mongodb://localhost:27017"
default_db = "medcent"
current_client = default_mongo_client
current_database = default_db

client = m.MongoClient(default_mongo_client)
database = client[default_db]
collection = database["teszt"]


def set_client(client_url: str):
    global client
    global current_client
    client = m.MongoClient(f'mongodb://{client_url}')
    current_client = f'mongodb://{client_url}'


def set_database(database_name: str):
    global database
    global current_database
    database = client[database_name]
    current_database = database_name


def set_collection(collection_name: str):
    global collection
    collection = database[collection_name]
