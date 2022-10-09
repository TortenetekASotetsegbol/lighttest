"""
Create and buffer errors into an error log record in the prefered format. Currently only available the mongodb document
format, which is create and send a json object to the specified database's collection
"""

import datetime
import json
from lighttest import mongo_datashare
from lighttest_supplies import timers
from lighttest import error_log


class ErrorLog:
    teststart: float
    time_consumed: datetime = 0
    total_testcase_count: int = 0
    succesful_testcase_count: int = 0
    error_count: int = 0
    errors: list = []
    frontend_errors: list = []
    statistics: str = "statistics"

    @staticmethod
    def add_error(error: dict) -> None:
        """
        Arguments:
            error: a json object, which is contains the necessary information about the error
        """

        ErrorLog.errors.append(error)

    @staticmethod
    def add_frontend_error(error: dict) -> None:
        """
        error: a json object, which is contains the necessary information about the error
        """

        ErrorLog.frontend_errors.append(error)

    @staticmethod
    def error_count_inc() -> None:
        ErrorLog.error_count += 1

    @staticmethod
    def total_case_count_inc() -> None:
        """Increase the current case-count by one"""
        ErrorLog.total_testcase_count += 1

    @staticmethod
    def result_to_db() -> None:
        """Send the collected error records to the mongodb database"""

        result: dict = {
            "time_consumed_in_seconds": ErrorLog.time_consumed,
            "test_start": ErrorLog.teststart,
            "total_testcase_count": ErrorLog.total_testcase_count,
            "error_count": ErrorLog.error_count,
            "succesful_testcase_count": ErrorLog.total_testcase_count - ErrorLog.error_count,
            "API_call_errors": ErrorLog.errors,
            "frontend_errors": ErrorLog.frontend_errors

        }
        mongo_datashare.insert_one(result, collection=ErrorLog.statistics)

    @staticmethod
    def worktime(testcontroller_fun):
        def run_testcases(*args, **kwargs):
            ErrorLog.teststart = datetime.datetime.now()
            timer = timers.Utimer()
            timer.set_start()
            testcontroller_fun(*args, **kwargs)
            timer.set_end()
            ErrorLog.time_consumed = timer.elapsed_time()

        return run_testcases

    @staticmethod
    def create_log(log_to_db=False, log_to_txt=False):
        def inner_method(testcontroller_fun):
            def run_testcases(*args, **kwargs):

                ErrorLog.teststart = datetime.datetime.now()
                timer = timers.Utimer()
                timer.set_start()
                testcontroller_fun(*args, **kwargs)
                timer.set_end()
                ErrorLog.time_consumed = timer.elapsed_time()

                if log_to_db:
                    ErrorLog.result_to_db()
                if log_to_txt:
                    pass

            return run_testcases

        return inner_method
