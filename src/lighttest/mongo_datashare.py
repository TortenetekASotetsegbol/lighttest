"""
A mongoDB-vel kapcsoaltos tranzakciók, mint a lekérdezések és az insertálások
"""
import json

from lighttest.mongo_connection import Mongo as con


def query(query_param: json, collection="") -> list[dict]:
    """Create a query in the specified collection. If you didn't specified the collection,
        it will run the query on the lastly specified collection"""
    if collection != "":
        con.set_collection(collection)

    result = con.collection.find(query_param)
    result_list: list[dict] = [record for record in result]
    return result_list


def insert_one(record: json, collection="") -> None:
    if collection != "":
        con.set_collection(collection)
    con.collection.insert_one(record)


def insert_many(records: [json], collection="") -> None:
    if collection != "":
        con.set_collection(collection)
    con.collection.insert_many(records)


def delete_one(records: [json], collection="") -> None:
    if collection != "":
        con.set_collection(collection)
    con.collection.delete_one(records)


def delete_many(records: [json], collection="") -> None:
    if collection != "":
        con.set_collection(collection)
    con.collection.delete_many(records)
