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
import asyncio


class Calls:

    def post_call(self, uriPath: str, payload):
        start_time = perf_counter()
        self.response = requests.post(cd.base_url + uriPath, headers=cd.headers, json=payload)
        end_time = perf_counter()
        self.response_time: float = round(end_time - start_time, 2)
        self.request = binary_json_to_json(self.response.request.body)
        self.response_json = self.response.json()
        self.status_code = self.response.status_code
        self.headres = self.response.headers
        self.url = self.response.url
        return self

    def get_call(self, uriPath: str, param=""):
        start_time = perf_counter()
        self.response = requests.get(cd.base_url + uriPath + str(param), headers=cd.headers)
        end_time = perf_counter()
        self.response_time = round(end_time - start_time, 2)
        self.request = {}
        self.response_json = self.response.json()
        self.status_code = self.response.status_code
        self.headres = self.response.headers
        self.url = self.response.url
        return self

    def put_call(self, uriPath: str, payload):
        start_time = perf_counter()
        self.response = requests.put(cd.base_url + uriPath, headers=cd.headers, json=payload)
        end_time = perf_counter()
        self.response_time = round(end_time - start_time, 2)
        self.request = binary_json_to_json(self.response.request.body)
        self.response_json = self.response.json()
        self.status_code = self.response.status_code
        self.headres = self.response.headers
        self.url = self.response.url
        return self


async def post_req_task(uri_path, request: json, session):
    async with session.post(url=cd.base_url + uri_path, json=request) as resp:
        result = ResultDatas()
        result.headers = resp.headers
        result.status_code = resp.status
        result.request = request
        try:
            result.response_json = await resp.json()
        except aiohttp.client_exceptions.ContentTypeError:
            result.response_json = {}

    return result


async def get_req_task(uri_path, session, request: json, param=""):
    async with session.get(url=f'{cd.base_url}{uri_path}{param}') as resp:
        result = copy.deepcopy(ResultDatas())
        result.headers = resp.headers
        result.status_code = resp.status
        result.request = request
        try:
            result.response_json: json = await resp.json()
        except aiohttp.client_exceptions.ContentTypeError:
            result.response_json: json = {}

    return result


async def put_req_task(uri_path, request: json, session):
    async with session.put(url=cd.base_url + uri_path, json=request) as resp:
        result = ResultDatas()
        result.headers = resp.headers
        result.response.status_code = resp.status
        result.request = request
        try:
            result.response.response_json = await resp.json()
        except aiohttp.client_exceptions.ContentTypeError:
            result.response.response_json = {}

    return result


@dataclass()
class ResponseDatas:
    pass


@dataclass()
class ResultDatas:
    response_time: int = 0
    headers: json = None
    request: json = None
    status_code: int = None
    response_json: json = None