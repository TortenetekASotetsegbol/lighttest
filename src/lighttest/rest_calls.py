"""
REST api hívások.
A mudulban található apihívás típusok: post, get (még bővíteni kell minimum egy puttal)
Minden hívás tartalmaz egy performancia tesztet is, amit a hívás után meghívva visszadja, hogy mennyi időt igényelt a hívíás elküldésétől számítva a response beérkezése
"""
import copy

import requests

from lighttest.common_rest_call_datas import Common as cd
from time import perf_counter
from lighttest_supplies.encoding import binary_json_to_json
from dataclasses import dataclass
import json
import aiohttp
from lighttest.datacollections import BackendResultDatas


def collect_call_request_data(request_function):
    def rest_api_call(*args, **kwargs):
        call_object: Calls = args[0]
        start_time = perf_counter()
        request_function(*args, **kwargs)
        call_object.response
        end_time = perf_counter()
        call_object.response_time: float = round(end_time - start_time, 2)

        call_object.request = binary_json_to_json(call_object.response.request.body)

        call_object.response_json = call_object.response.json()
        call_object.status_code = call_object.response.status_code
        call_object.headres = call_object.response.headers
        call_object.url = call_object.response.url
        return call_object

    return rest_api_call


async def collect_async_data(resp: object, request: dict):
    result: BackendResultDatas = copy.deepcopy(BackendResultDatas())
    result.headers = resp.headers
    result.status_code = resp.status
    result.request = request
    result.url = str(resp.url)
    try:
        result.response_json = await resp.json()
    except aiohttp.client_exceptions.ContentTypeError:
        result.response_json = {}
    result.response_time = 0
    return result


class Calls:

    def __init__(self):
        self.response: object = None
        self.response_time: float = 0.0
        self.request: object = None
        self.response_json: dict = {}
        self.status_code: int = 0
        self.headers: dict = {}
        self.url: str = ""

    @collect_call_request_data
    def post_call(self, uri_path: str, payload: dict, param: str = ""):
        self.response = requests.post(url=f'{cd.base_url}{uri_path}{param}', headers=cd.headers, json=payload)

    @collect_call_request_data
    def get_call(self, uri_path: str, param="", payload: dict = {}):
        self.response = requests.get(url=f'{cd.base_url}{uri_path}{param}', headers=cd.headers, json=payload)

    @collect_call_request_data
    def put_call(self, uri_path: str, payload: dict, param: str = ""):
        self.response = requests.put(url=f'{cd.base_url}{uri_path}{param}', headers=cd.headers, json=payload)


async def post_req_task(uri_path, request: json, session):
    async with session.post(url=f'{cd.base_url}{uri_path}', json=request) as resp:
        return await collect_async_data(resp=resp, request=request)


async def get_req_task(uri_path, session, request: json, param=""):
    async with session.get(url=f'{cd.base_url}{uri_path}{param}') as resp:
        return await collect_async_data(resp=resp, request=request)


async def put_req_task(uri_path, request: json, session):
    async with session.put(url=cd.base_url + uri_path, json=request) as resp:
        return await collect_async_data(resp=resp, request=request)


# decorator
# def async_collect_call_request_data(request_function):
#     async def async_rest_api_call(*args, **kwargs):
#         with request_function(*args, **kwargs) as resp:
#
#             result: BackendResultDatas = copy.deepcopy(BackendResultDatas())
#             result.headers = resp.headers
#             result.status_code = resp.status
#             result.request = kwargs["request"]
#             try:
#                 result.response_json: dict = await resp.json()
#             except aiohttp.client_exceptions.ContentTypeError:
#                 result.response_json: dict = {}
#
#             return await result
#
#     return async_rest_api_call
