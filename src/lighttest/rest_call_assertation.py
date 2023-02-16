'''
A rest apis hívások ellenőrzése

'''
import json

from lighttest.test_summary import ErrorLog as el
import lighttest.test_summary as ts
from lighttest_supplies.general import boolsum, format_rest_uri
from lighttest_supplies.general_datas import TestType as tt
from dataclasses import dataclass, KW_ONLY, field
from lighttest.datacollections import TestResult, ResultTypes, BackendPerformanceStatisticPost, BackendError, \
    TestTypes, Calls

from lighttest.testcase import Testcase

default_timelimit_in_seconds = 1


@dataclass(kw_only=True)
class RestTest:
    extra_asserts_accepted: bool
    resp: Calls
    id: str = ""
    accepted_status_code: int = 200
    error_desc: str = ""
    positivity: str = tt.POSITIVE.value
    timelimit_in_seconds: float = 1
    attributes: dict = field(default_factory=dict())


def assertion(resp: Calls, accepted_status_code: int = 200,
              error_desc: str = "", attributes: dict = dict(),
              positivity: str = tt.POSITIVE.value, timelimit_in_seconds=1, raise_error=False, **extra_asserts):
    """


    Arguments:
        testcase: a Testcase object which contains the finished testcase steps
        attributes: optional. if there is some unique attrubute of this assertion, you can put it here.
        resp: egy requests object, ami tartalmazza a requestet és response minden adatát
        positivity: it determinate how to evaulate the result.
            it can be "positive" or "negative". default value: "positive"
        accepted_status_code: a pozitív teszteset esetén elfogadott státuszkód
        error_desc: brief description of the error, if the case failed
        extra_asserts: assertions, that necessaries for the case. It can be zero or one or multiple assertions,
        but every assertattion must return a bool variabel

    Return: true, ha a teszteset sikeresnek lett elkönyvelve (a várt eredményt tapsztalta a funkció)
    """
    ass = RestTest(resp=resp, accepted_status_code=accepted_status_code, error_desc=error_desc,
                   positivity=positivity, timelimit_in_seconds=timelimit_in_seconds, attributes=attributes,
                   extra_asserts_accepted=boolsum([extra_assert(resp) for extra_assert in extra_asserts.values()]))

    request = resp.request
    result = is_succesful(ass)
    successful = result.fast and result.successful

    add_rest_api_step(testcase=resp.testcase, req_payload=request, req_response=resp.response_json,
                      statuscode=resp.status_code, perf=resp.response_time, positivity=positivity,
                      attributes=attributes, error_desc=error_desc, request_url=resp.url)

    if not successful:
        if raise_error:
            # el.result_to_db()
            raise Exception(f'Testing workflow is can not be continued. error: {error_desc}')

    ts.new_testresult(result=result_evaluation(result), testcase_name=resp.testcase.case_name,
                      required_time=resp.response_time, test_type=TestTypes.BACKEND.value,
                      description=format_rest_uri(resp.url))
    return successful


def create_error_record(request_url: str, req_payload: json, req_response: json, statuscode: int, perf: float,
                        attributes: dict = dict(),
                        positivity: str = tt.POSITIVE.value,
                        error_desc: str = ""):
    """create an error record from the collected datas"""
    error = BackendError(req_payload=req_payload, req_response=req_response,
                         statuscode=statuscode, performance_in_seconds=perf, attributes=attributes,
                         positivity=positivity,
                         error_desc=error_desc, request_url=format_rest_uri(request_url))
    el.add_error(vars(error))


def add_rest_api_step(testcase: Testcase, request_url: str, req_payload: json, req_response: json, statuscode: int,
                      perf: float,
                      attributes: dict = dict(),
                      positivity: str = tt.POSITIVE.value,
                      error_desc: str = ""):
    step: BackendError = BackendError(req_payload=req_payload, req_response=req_response,
                                      statuscode=statuscode, performance_in_seconds=perf, attributes=attributes,
                                      positivity=positivity,
                                      error_desc=error_desc, request_url=format_rest_uri(request_url))

    if testcase is not None:
        testcase.add_case_step(step)
    else:
        Testcase.add_global_case_step(step)


def result_evaluation(result: TestResult):
    match (result.successful, result.fast):
        case (True, True):
            return ResultTypes.SUCCESSFUL.value
        case (True, False):
            return ResultTypes.SLOW.value
        case (False, True) | (False, False):
            return ResultTypes.FAILED.value


def is_succesful(test_object: RestTest):
    positivity = test_object.positivity
    good_perf = test_object.resp.response_time < test_object.timelimit_in_seconds
    extra_asserts_was_successful = test_object.extra_asserts_accepted
    positive = positivity == tt.POSITIVE.value
    negative = positivity == tt.NEGATIVE.value
    status_code_accepted = test_object.resp.status_code == test_object.accepted_status_code
    is_successful = ((positive and status_code_accepted) or (
            negative and not status_code_accepted)) and extra_asserts_was_successful
    result = TestResult(fast=good_perf, successful=is_successful)

    return result
