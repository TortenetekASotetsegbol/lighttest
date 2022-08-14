'''
REST api hívások.
A mudulban található apihívás típusok: post, get (még bővíteni kell minimum egy puttal)
Minden hívás tartalmaz egy performancia tesztet is, amit a hívás után meghívva visszadja, hogy mennyi időt igényelt a hívíás elküldésétől számítva a response beérkezése
'''

import requests

from lighttest import common_datas as cd
from time import perf_counter


# defaultHeaders = cd.headers
class calls:
    response: requests
    response_time: float

    def post_call(self, uriPath: str, payload):
        start_time = perf_counter()
        self.response = requests.post(cd.base_url + uriPath, headers=cd.get_headers(), json=payload)
        end_time = perf_counter()
        self.response_time = round(end_time - start_time, 2)
        return self

    def get_call(self, uriPath: str, param=""):
        start_time = perf_counter()
        self.response = requests.get(cd.base_url + uriPath + str(param), headers=cd.get_headers())
        end_time = perf_counter()
        self.response_time = round(end_time - start_time, 2)
        return self


    def put_call(self, uriPath: str, payload):
        start_time = perf_counter()
        self.response = requests.post(cd.base_url + uriPath, headers=cd.get_headers(), json=payload)
        end_time = perf_counter()
        self.response_time = round(end_time - start_time, 2)
        return self