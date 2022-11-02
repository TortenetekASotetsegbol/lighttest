'''
A rest apis hívások ellenőrzése

'''
import json

import requests
from lighttest import mongo_datas as mdb
from lighttest import general_calls
from src.lighttest.error_log import ErrorLog as el
from src.lighttest.error_log import Error
from lighttest_supplies.general import boolsum, format_rest_uri
from lighttest_supplies import encoding as en
from dataclasses import dataclass, KW_ONLY, field
from enum import Enum, unique
from src.lighttest.error_log import ResultTypes, TestResult, BackendPerformanceStatisticPost

db_e = mdb.testcase_fields
default_timelimit_in_seconds = 1


@dataclass(kw_only=True)
class RestTest:
    resp: general_calls.Calls
    id: str = ""
    accepted_status_code: int = 200
    error_desc: str = ""
    properties: dict = field(default_factory={db_e.POZITIVITAS.value: db_e.POSITIVITY_POSITIVE.value})
    timelimit_in_seconds: float = 1


def assertion(resp: general_calls.Calls, id: str, accepted_status_code: int = 200,
              error_desc: str = "",
              properties: json = {db_e.POZITIVITAS.value: db_e.POSITIVITY_POSITIVE.value}, timelimit_in_seconds=1,
              raise_error=False,
              **extra_asserts):
    """


    Arguments:
        resp: egy requests objekt, ami tartalmazza a requestet és response minden adatát
        properties: a mongodb-ből kapott teszteset tulajdonságait tartalmazza, mint pozittivitás, terület, stb.
        accepted_status_code: a pozitív teszteset esetén elfogadott státuszkód
        error_desc: brief description of the error, if the case failed
        extra_asserts: assertions, that necessaries for the case. It can be zero or one or multiple assertions,
        but every assertattion must return a bool variabel

    Return: true, ha a teszteset sikeresnek lett elkönyvelve (a várt eredményt tapsztalta a funkció)
    """
    ass = RestTest(resp=resp, id=id, accepted_status_code=accepted_status_code, error_desc=error_desc,
                   properties=properties, timelimit_in_seconds=timelimit_in_seconds)

    request = resp.request
    el.total_case_count_inc()
    result = is_succesful(ass)
    successful = result.fast and result.successful and boolsum(extra_asserts)

    if not successful:
        create_error_record(req_payload=request, req_response=resp.response_json,
                            statuscode=resp.status_code, perf=resp.response_time, properties=properties, id=id,
                            error_desc=error_desc, request_url=resp.url)
        if raise_error:
            el.result_to_db()
            raise Exception(f'Testing workflow is can not be continued. error: {error_desc}')

    create_call_result_post(result=result_evaluation(result), request_url=format_rest_uri(resp.url),
                            response_time=resp.response_time)

    return successful


def create_error_record(request_url: str, req_payload: json, req_response: json, statuscode: int, perf: float,
                        properties: json, id: str,
                        error_desc: str = ""):
    """create an error record from the collected datas"""
    error = Error(req_payload=req_payload, req_response=req_response,
                  statuscode=statuscode, performance_in_seconds=perf, properties=properties, id=id,
                  error_desc=error_desc, request_url=format_rest_uri(request_url))
    el.add_error(error.__dict__)
    el.error_count_inc()


def create_call_result_post(result: str, request_url: str, response_time: float):
    if response_time == 0:
        return

    error_post = BackendPerformanceStatisticPost(result=result, request_url=format_rest_uri(request_url),
                                                 response_time=response_time)
    el.backend_performance_datas.append(error_post)


def add_new_performance_post(name: str, response_time: float):
    error_post = BackendPerformanceStatisticPost(result=ResultTypes.UNRECOGNISABLE.value, request_url=name,
                                                 response_time=response_time)
    el.backend_performance_datas.append(error_post)


def result_evaluation(result: TestResult):
    match (result.successful, result.fast):
        case (True, True):
            return ResultTypes.SUCCESSFUL.value
        case (True, False):
            return ResultTypes.SLOW.value
        case [(False, True), (False, False)]:
            return ResultTypes.FAILED.value


def is_succesful(test_object: RestTest):
    positivity = test_object.properties[db_e.POZITIVITAS.value]
    good_perf = test_object.resp.response_time < test_object.timelimit_in_seconds
    positive = positivity == db_e.POSITIVITY_POSITIVE.value
    negative = positivity == db_e.POSITIVITY_NEGATIVE.value
    status_code_accepted = test_object.resp.status_code == test_object.accepted_status_code
    is_successful = (positive and status_code_accepted) or (negative and not status_code_accepted)
    result = TestResult(fast=good_perf, successful=is_successful)

    return result
