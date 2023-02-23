from functools import wraps

from src.lighttest.interface_methods import MiUsIn
from lighttest.rest_calls import Calls
from src.lighttest.sql_methods import SqlConnection
from lighttest.test_summary import ErrorLog


class Testcase:
    global_step_counter: int
    global_case_name: str
    global_case_steps: list[object] = list()

    def __init__(self, case_name: str):
        self.case_name: str = case_name
        self.step_counter: int = 0
        self.case_steps: list[object] = list()
        self.error_counter: int = 0
        self.critical_error: bool = False
        self.miusin: MiUsIn = None
        self.http_request: Calls = None
        self.sql: SqlConnection = None

    @staticmethod
    def add_global_case_step(case_step: dict):
        Testcase.global_step_counter += 1
        case_step.update({"step_id": Testcase.global_step_counter})
        Testcase.global_case_steps.append(case_step)

    def add_case_step(self, case_step: dict):
        self.step_counter += 1
        case_step.update({"step_id": self.step_counter})
        self.case_steps.append(case_step)

    def close_case(self):
        if self.error_counter > 0:
            ErrorLog.errors.append({self.case_name: self.case_steps})
            ErrorLog.errors
        del self

    def set_miusin(self):
        self.miusin = MiUsIn(testcase=self)
        return self.miusin

    def set_http_request(self):
        self.http_request = Calls(self)
        return self.http_request

    def set_sql(self, username: str, password: str, dialect_driver: str, dbname: str, host: str, port: str):
        self.sql = SqlConnection(testcase=self, username=username, password=password, dialect_driver=dialect_driver,
                                 dbname=dbname, host=host, port=port)
        return self.sql


# decorator
def case_step(case_function):
    @wraps(case_function)
    def method(*args, **kwargs):
        testcase_object: Testcase = args[0].testcase
        if testcase_object.critical_error:
            return

        return case_function(*args, **kwargs)

    return method


def case_method(case_method):
    @wraps(case_method)
    def method(*args, **kwargs):
        arguments: list = list(args) + list(kwargs.values())
        testcase: Testcase = find_testcase_object(arguments)

        if testcase.critical_error:
            return None

        return_value = case_method(*args, **kwargs)

        return return_value

    return method


def find_testcase_object(args_kwargs: list) -> Testcase:
    """
    Find and return the testcase object from a list.
    If there is no Testcase object in the list, rise KeyError Exception.
    """
    for argumentum in args_kwargs:
        if isinstance(argumentum, Testcase):
            return argumentum

    raise KeyError("Testcase object not found")
