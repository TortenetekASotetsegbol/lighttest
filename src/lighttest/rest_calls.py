"""
REST api hívások.
A mudulban található apihívás típusok: post, get (még bővíteni kell minimum egy puttal)
Minden hívás tartalmaz egy performancia tesztet is, amit a hívás után meghívva visszadja, hogy mennyi időt igényelt a hívíás elküldésétől számítva a response beérkezése
"""
import copy
from functools import wraps

import requests

from lighttest.common_rest_call_datas import Common as cd
from time import perf_counter
from lighttest_supplies.encoding import binary_json_to_json
from lighttest_supplies.general_datas import TestType as tt
import json
import aiohttp
from lighttest.datacollections import BackendResultDatas
from lighttest.rest_call_assertation import assertion

from lighttest.testcase import Testcase, case_step



def collect_call_request_data(request_function):
    @wraps(request_function)
    @case_step
    def rest_api_call(*args, **kwargs):
        call_object: Calls = args[0]
        start_time = perf_counter()
        request_function(*args, **kwargs)
        call_object.response
        end_time = perf_counter()
        call_object.response_time: float = round(end_time - start_time, 2)

        call_object.request = binary_json_to_json(call_object.response.request.body)

        try:
            call_object.response_json = call_object.response.json()
        except json.decoder.JSONDecodeError:
            call_object.response_json: dict = {"error": "it is not json format or there is no response object"}
        call_object.status_code = call_object.response.status_code
        call_object.headers = call_object.response.headers
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

    def __init__(self, testcase: Testcase):
        self.response: object = None
        self.response_time: float = 0.0
        self.request: object = None
        self.response_json: dict = {}
        self.status_code: int = 0
        self.headers: dict = {}
        self.url: str = ""
        self.testcase: Testcase = testcase

    @collect_call_request_data
    def post_call(self, uri_path: str, payload: dict, param: str = ""):
        self.response = requests.post(url=f'{cd.base_url}{uri_path}{param}', headers=cd.headers, json=payload)

    @collect_call_request_data
    def get_call(self, uri_path: str, payload: dict = {}, param=""):
        self.response = requests.get(url=f'{cd.base_url}{uri_path}{param}', headers=cd.headers, json=payload)

    @collect_call_request_data
    def put_call(self, uri_path: str, payload: dict, param: str = ""):
        self.response = requests.put(url=f'{cd.base_url}{uri_path}{param}', headers=cd.headers, json=payload)

    @collect_call_request_data
    def delete_call(self, uri_path: str, payload: dict, param: str = ""):
        self.response = requests.delete(url=f'{cd.base_url}{uri_path}{param}', headers=cd.headers, json=payload)

    def post_call_with_assert(self, uri_path: str, payload: dict, param: str = "",
                              accepted_status_code: int = 200,
                              error_desc: str = "",
                              attributes: dict = dict(),
                              positivity: json = tt.POSITIVE.value,
                              timelimit_in_seconds=1,
                              raise_error=False,
                              **extra_asserts):
        response: Calls = self.post_call(uri_path, payload, param)
        assertion(resp=response, error_desc=error_desc, attributes=attributes,
                  positivity=positivity,
                  raise_error=raise_error,
                  timelimit_in_seconds=timelimit_in_seconds, accepted_status_code=accepted_status_code, **extra_asserts)

        return response

    @case_step
    def put_call_with_assert(self, uri_path: str, payload: dict, param: str = "",
                             accepted_status_code: int = 200,
                             error_desc: str = "",
                             attributes: dict = dict(),
                             positivity: json = tt.POSITIVE.value,
                             timelimit_in_seconds=1,
                             raise_error=False,
                             **extra_asserts):
        response: Calls = self.post_put(uri_path, payload, param)
        assertion(resp=response, error_desc=error_desc, attributes=attributes,
                  positivity=positivity, raise_error=raise_error,
                  timelimit_in_seconds=timelimit_in_seconds, accepted_status_code=accepted_status_code, **extra_asserts)

        return response

    @case_step
    def get_call_with_assert(self, uri_path: str, payload: dict, param: str = "",
                             accepted_status_code: int = 200,
                             error_desc: str = "",
                             attributes: dict = dict(),
                             positivity: json = tt.POSITIVE.value,
                             timelimit_in_seconds=1,
                             raise_error=False,
                             **extra_asserts):
        response: Calls = self.get_call(uri_path, payload, param)
        assertion(resp=response, error_desc=error_desc, attributes=attributes,
                  positivity=positivity, raise_error=raise_error,
                  timelimit_in_seconds=timelimit_in_seconds, accepted_status_code=accepted_status_code, **extra_asserts)

        return response

    @case_step
    def delete_call_with_assert(self, uri_path: str, payload: dict, param: str = "",
                                accepted_status_code: int = 200,
                                error_desc: str = "",
                                attributes: dict = dict(),
                                positivity: json = tt.POSITIVE.value,
                                timelimit_in_seconds=1,
                                raise_error=False,
                                **extra_asserts):
        response: Calls = self.delete_call(uri_path, payload, param)
        assertion(resp=response, error_desc=error_desc, attributes=attributes,
                  positivity=positivity, raise_error=raise_error,
                  timelimit_in_seconds=timelimit_in_seconds, accepted_status_code=accepted_status_code, **extra_asserts)

        return response


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
