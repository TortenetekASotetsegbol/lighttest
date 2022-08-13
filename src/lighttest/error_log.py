'''
Create and buffer errors into an error log record in the prefered format. Currently only available the mongodb document
format, which is create and send a json object to the specified database's collection
'''
import datetime
import json
from lighttest import datashare
from dtools_supplies import timers
from lighttest import error_log

teststart: float
time_consumed: datetime = 0
total_testcase_count: int = 0
succesful_testcase_count: int = 0
error_count: int = 0
errors: list = []
statistics: str = "statistics"


def add_error(error: json):
    '''
    :param error: a json object, which is contains the necessary information about the error
    :return:
    '''
    global errors
    errors.append(error)


def error_count_inc():
    global error_count
    error_count += 1


def total_case_count_inc():
    '''Increase the current case-count by one'''
    global total_testcase_count
    total_testcase_count += 1


def result_to_db():
    '''Send the collected error records to the mongodb database'''
    result: json = {
        "time_consumed_in_seconds": time_consumed,
        "test_start": teststart,
        "total_testcase_count": total_testcase_count,
        "error_count": error_count,
        "succesful_testcase_count": total_testcase_count - error_count,
        "errors": errors
    }
    datashare.insert_one(result, collection=statistics)


def worktime(testcontroller_fun):
    def run_testcases(*args, **kwargs):
        global time_consumed
        global teststart
        teststart = datetime.datetime.now()
        timer = timers.Utimer()
        timer.set_start()
        testcontroller_fun(*args, **kwargs)
        timer.set_end()
        time_consumed = timer.elapsed_time()

    return run_testcases


def create_log(log_to_db=False):
    def inner_method(testcontroller_fun):
        def run_testcases(*args, **kwargs):
            global time_consumed
            global teststart
            teststart = datetime.datetime.now()
            timer = timers.Utimer()
            timer.set_start()
            testcontroller_fun(*args, **kwargs)
            timer.set_end()
            time_consumed = timer.elapsed_time()

            if log_to_db:
                error_log.result_to_db()

        return run_testcases

    return inner_method
