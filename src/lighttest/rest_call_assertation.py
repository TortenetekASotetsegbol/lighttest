'''
A rest apis hívások ellenőrzése

'''
import json

import requests
from lighttest import mongo_datas as mdb
from lighttest import general_calls
from lighttest.error_log import ErrorLog as el
from lighttest_supplies.general import boolsum
from lighttest_supplies import encoding as en

db_e = mdb.testcase_fields
default_timelimit_in_seconds = 1


class Assertation:
    def __init__(self, resp: general_calls.Calls, id: str, accepted_status_code: int = 200,
                 error_desc: str = "", properties: json = {db_e.POZITIVITAS.value: db_e.POSITIVITY_POSITIVE.value},
                 timelimit_in_seconds=1):
        self.resp = resp
        self.id = id
        self.accepted_status_code = accepted_status_code
        self.error_desc = error_desc
        self.properties = properties
        self.timelimit_in_seconds = timelimit_in_seconds

    def succesful(self):
        positivity = self.properties[db_e.POZITIVITAS.value]
        good_perf = self.resp.response_time < self.timelimit_in_seconds
        positive = positivity == db_e.POSITIVITY_POSITIVE.value
        negative = positivity == db_e.POSITIVITY_NEGATIVE.value
        status_code_accepted = self.resp.status_code == self.accepted_status_code
        succesful = (positive and status_code_accepted and good_perf) or (
                negative and not status_code_accepted and good_perf)
        return succesful


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
    ass = Assertation(resp=resp, id=id, accepted_status_code=accepted_status_code, error_desc=error_desc,
                      properties=properties, timelimit_in_seconds=timelimit_in_seconds)

    # global sikeres
    request = resp.request
    el.total_case_count_inc()
    succesful = ass.succesful() and boolsum(extra_asserts)

    if not succesful:
        create_error_record(req_payload=request, req_response=resp.response_json,
                            statuscode=resp.status_code, perf=resp.response_time, properties=properties, id=id,
                            error_desc=error_desc)
        if raise_error:
            el.result_to_db()
            raise Exception(f'Testing workflow is can not be continued. error: {error_desc}')

    return succesful


def create_error_record(req_payload: json, req_response: json, statuscode: int, perf: float, properties: json, id: str,
                        error_desc: str = ""):
    """create an error record from the collected datas"""
    error = error_inf(req_payload=req_payload, req_response=req_response,
                      statuscode=statuscode, perf=perf, properties=properties, id=id, error_desc=error_desc)
    el.add_error(error.get_error())
    el.error_count_inc()


class error_inf:
    req_payload: json
    req_response: json
    statuscode: int
    perf: float
    area: str
    properties: json
    id: str
    error_desc: str

    def __init__(self, req_payload: json, req_response: json, statuscode: int, perf: float, properties: json, id: str,
                 error_desc: str = ""):
        self.req_payload = req_payload
        self.req_response = req_response
        self.statuscode = statuscode
        self.perf = perf
        self.properties = properties
        self.id = id
        self.error_desc = error_desc

    def get_error(self):
        error: json = {
            "id": self.id,
            "payload": self.req_payload,
            "response": self.req_response,
            "return_code": self.statuscode,
            "performance_in_seconds": self.perf,
            "propoerties": self.properties,
            "error_describetion": self.error_desc

        }
        return error
