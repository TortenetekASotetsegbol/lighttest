"""
Create and buffer backend_errors into an error log record in the prefered format. Currently only available the mongodb document
format, which is create and send a json object to the specified database's collection
"""

import datetime
import json

import pandas
from lighttest import mongo_datashare
from lighttest_supplies import timers, date_methods
from lighttest_supplies.general import create_logging_directory, create_logging_structure
from lighttest_supplies.date_methods import get_current_time
from src.lighttest.charts import generate_figure_from_array, generate_pie_chart_from_simple_dict, \
    generate_bar_chart_from_simple_dict
from src.lighttest.charts import Orientation
from pathlib import Path

from src.lighttest.datacollections import TestTypes, BackendPerformanceStatisticPost, PerformancePost


class SumDatabaseTests:
    successful_queries: int = 0
    failed_queries: int = 0
    inefficient_queries: int = 0

    @staticmethod
    def get_sum_database_test_result() -> dict:
        return {"failed_queries": SumDatabaseTests.failed_queries,
                "inefficient_queries": SumDatabaseTests.inefficient_queries,
                "successful_queries": SumDatabaseTests.successful_queries}


class ErrorLog:
    teststart: float
    time_consumed: datetime = 0
    total_testcase_count: int = 0
    succesful_testcase_count: int = 0
    error_count: int = 0
    error_per_frontend_case: dict = {}
    backend_errors: list = []
    frontend_errors: list = []
    statistics: str = "statistics"
    errors_directory: str = "C:\Logs"
    charts_directory: str = "C:\Figures"
    backend_performance_datas: list[BackendPerformanceStatisticPost] = []
    database_errors: list = []
    query_performance_statistics: list[PerformancePost] = []

    @staticmethod
    def get_error_numbers_in_dict():
        error_statistic: dict = {TestTypes.FRONTEND.value: len(ErrorLog.frontend_errors),
                                 TestTypes.BACKEND.value: len(ErrorLog.backend_errors),
                                 TestTypes.DATABASE.value: len(ErrorLog.database_errors),
                                 "successful_testcases": ErrorLog.total_testcase_count - ErrorLog.error_count
                                 }
        return error_statistic

    @staticmethod
    def add_error(error: dict) -> None:
        """
        Arguments:
            error: a json object, which is contains the necessary information about the error
        """

        ErrorLog.backend_errors.append(error)

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
    def __create_dictionary_log_post() -> dict:
        result: dict = {
            "time_consumed_in_seconds": ErrorLog.time_consumed,
            "test_start": ErrorLog.teststart,
            "total_testcase_count": ErrorLog.total_testcase_count,
            "error_count": ErrorLog.error_count,
            "succesful_testcase_count": ErrorLog.total_testcase_count - ErrorLog.error_count,
            "API_call_errors": ErrorLog.backend_errors,
            "frontend_errors": ErrorLog.frontend_errors

        }
        return result

    @staticmethod
    def __create_text_log_post(log_directory: str):
        create_logging_directory(log_directory)

        file_name: str = f'{date_methods.get_current_time()}.txt'
        with open(create_logging_structure(log_directory) / file_name, "w", encoding="utf-8") as create:
            create.write(f"\nLOG {datetime.datetime.now()}")
            create.write(f"\n")
            create.write(f"\nSUMMARY")
            create.write(f"\n-------------------------------------")
            create.write(f"\ntime_consumed_in_seconds: {ErrorLog.time_consumed}")
            create.write(f"\ntest_start: {ErrorLog.teststart}")
            create.write(f"\ntotal_testcase_count: {ErrorLog.total_testcase_count}")
            create.write(f"\nerror_count: {ErrorLog.error_count}")
            create.write(f"\nsuccesful_testcase_count: {ErrorLog.succesful_testcase_count}")
            create.write(f"\n")
            create.write(f"\nAPI_CALL_ERRORS")
            create.write(f"\n-------------------------------------")
            for error in ErrorLog.backend_errors:
                create.write(f"\n********************")
                create.write(f"\n\n{json.dumps(error, indent=4, default=str, ensure_ascii=False)}")
                create.write(f"\n********************")
            create.write(f"\n")
            create.write(f"\nFRONTEND_ERRORS")
            create.write(f"\n-------------------------------------")
            for error in ErrorLog.frontend_errors:
                create.write(f"\n********************")
                create.write(f"\n\n{json.dumps(error, indent=4, default=str)}")
                create.write(f"\n********************")
            create.write(f"\n")
            create.write(f"\nDATABASE_ERRORS")
            create.write(f"\n-------------------------------------")
            for error in ErrorLog.database_errors:
                create.write(f"\n********************")
                create.write(f"\n\n{json.dumps(error, indent=4, default=str)}")
                create.write(f"\n********************")

    @staticmethod
    def result_to_mongo_db() -> None:
        """Send the collected error records to the mongodb database"""

        mongo_datashare.insert_one(ErrorLog.__create_dictionary_log_post(), collection=ErrorLog.statistics)

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
    def create_log(log_to_mongo_db: bool = False, log_to_txt: bool = False, log_to_console: bool = False,
                   log_directory: str = errors_directory, show_chart_summary: bool = False, save_charts: bool = False,
                   charts_directory: str = charts_directory):
        def inner_method(testcontroller_fun):
            def run_testcases(*args, **kwargs):

                ErrorLog.teststart = datetime.datetime.now()
                timer = timers.Utimer()
                timer.set_start()
                testcontroller_fun(*args, **kwargs)
                timer.set_end()
                ErrorLog.time_consumed = timer.elapsed_time()

                if log_to_mongo_db:
                    ErrorLog.result_to_mongo_db()
                if log_to_txt:
                    ErrorLog.__create_text_log_post(log_directory)
                if log_to_console:
                    print(ErrorLog.__create_dictionary_log_post())
                if show_chart_summary or save_charts:
                    fig_directory: Path = create_logging_structure(ErrorLog.charts_directory)
                    create_logging_directory(ErrorLog.charts_directory)
                    dataframe = pandas.DataFrame.from_dict(ErrorLog.backend_performance_datas)
                    generate_figure_from_array(data=dataframe, grouping_column=None, x_label="response_times",
                                               y_label="endpoints",
                                               title="response time/endpoint", x_axis_column="response_time",
                                               y_axis_column="request_url", size_width=10, size_height=10,
                                               orientation=Orientation.HORIZONTAL.value, show_fig=show_chart_summary,
                                               save_fig=save_charts,
                                               fig_directory=fig_directory / f'{get_current_time()}.svg')
                    generate_pie_chart_from_simple_dict(
                        title="FRONTEND ERRORS/BACKEND ERRORS/SUCCESSFUL TESTCASE RATIO",
                        data=ErrorLog.get_error_numbers_in_dict(),
                        show_fig=show_chart_summary,
                        save_fig=save_charts,
                        fig_directory=fig_directory / f'{get_current_time()}.svg')
                    generate_bar_chart_from_simple_dict(title="FRONTEND ERORRS PER TESTCASE",
                                                        data=ErrorLog.error_per_frontend_case,
                                                        show_fig=show_chart_summary,
                                                        save_fig=save_charts,
                                                        fig_directory=fig_directory / f'{get_current_time()}.svg')
                    generate_bar_chart_from_simple_dict(title="DATABASE-TEST SUMMARY",
                                                        data=SumDatabaseTests.get_sum_database_test_result(),
                                                        show_fig=show_chart_summary,
                                                        save_fig=save_charts,
                                                        fig_directory=fig_directory / f'{get_current_time()}.svg')
                    db_dataframe = pandas.DataFrame.from_dict(ErrorLog.query_performance_statistics)
                    generate_figure_from_array(data=db_dataframe, title="QUERY/RESPONSE TIME",
                                               x_label="required_time (s)", y_label="queries",
                                               x_axis_column="required_time",
                                               y_axis_column="name", show_fig=show_chart_summary,
                                               save_fig=save_charts,
                                               fig_directory=fig_directory / f'{get_current_time()}.svg')

            return run_testcases

        return inner_method


