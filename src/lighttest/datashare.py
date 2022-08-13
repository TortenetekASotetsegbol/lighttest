'''
A mongoDB-vel kapcsoaltos tranzakciók, mint a lekérdezések és az insertálások
'''
import json

from lighttest import connection as con


def query(query_param: json, collection=""):
    '''Create a query in the specifird collection. If you didnt specifie the collection,
    it will run the query on the lastly specified collection'''
    if (collection != ""):
        con.set_collection(collection)

    result = con.collection.find(query_param)
    result_list = [record for record in result]
    return result_list


def insert_one(record: json, collection=""):
    if (collection != ""):
        con.set_collection(collection)
    con.collection.insert_one(record)


def insert_many(records: [json], collection=""):
    if (collection != ""):
        con.set_collection(collection)
    con.collection.insert_many(records)
