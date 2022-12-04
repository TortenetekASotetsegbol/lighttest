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

import lighttest.test_summary
from lighttest.charts import generate_figure_from_array, generate_pie_chart_from_simple_dict, \
    generate_bar_chart_from_simple_dict, DataFrame, generate_bar_chart_from_dataframe, pd
from lighttest.charts import Orientation
from pathlib import Path
from lighttest.datacollections import UniversalPerformancePost

from lighttest.datacollections import TestTypes, BackendPerformanceStatisticPost, PerformancePost, ResultTypes


def get_statistic(test_type: str, *result_types: str) -> DataFrame:
    statistics: DataFrame = get_statistics()
    query_result: DataFrame = DataFrame()
    for result_type in result_types:
        query: str = f'(test_type == "{test_type}") and (result == "{result_type}")'
        query_result = pd.concat([query_result, statistics.query(query)], ignore_index=True)
    return query_result


class SumDatabaseTests:
    successful_queries: int = 0
    failed_queries: int = 0
    inefficient_queries: int = 0

    @staticmethod
    def get_sum_database_test_result() -> dict:
        return {"failed_queries": SumDatabaseTests.failed_queries,
                "inefficient_queries": SumDatabaseTests.inefficient_queries,
                "successful_queries": SumDatabaseTests.successful_queries}


def new_testresult(name: str, result: str, test_type: str, required_time: float):
    result = UniversalPerformancePost(name=name, result=result, test_type=test_type, required_time=required_time)
    ErrorLog.result_summary.append(result)


def get_statistics() -> DataFrame:
    return DataFrame.from_dict(ErrorLog.result_summary)


def get_global_stats() -> DataFrame:
    statistics = get_statistics()
    global_stats: DataFrame = statistics[["test_type", "result"]].groupby(["test_type", "result"], as_index=False).agg(
        sum=("result", "count"))

    return global_stats


class ErrorLog:
    project_name: str = ""
    teststart: float
    time_consumed: datetime = 0
    backend_errors: list = []
    frontend_errors: list = []
    errors_directory: str = "C:\Logs"
    charts_directory: str = "C:\Figures"
    database_errors: list = []
    result_summary: list[UniversalPerformancePost] = []

    @staticmethod
    def get_error_numbers_in_dict():
        statistics: DataFrame = get_statistics()

        error_statistic: dict = {
            TestTypes.FRONTEND.value: len(get_statistic(TestTypes.FRONTEND.value, ResultTypes.FAILED.value,
                                                        ResultTypes.SLOW.value)),
            TestTypes.BACKEND.value: len(get_statistic(TestTypes.BACKEND.value, ResultTypes.FAILED.value,
                                                       ResultTypes.SLOW.value)),
            TestTypes.DATABASE.value: len(get_statistic(TestTypes.DATABASE.value, ResultTypes.FAILED.value,
                                                        ResultTypes.SLOW.value)),
            "successful_testcases": len(statistics.query(f'result == "{ResultTypes.SUCCESSFUL.value}"'))
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
    def __create_dictionary_log_post() -> dict:
        statistics: DataFrame = get_statistics()
        result: dict = {
            "project_name": ErrorLog.project_name,
            "time_consumed_in_seconds": ErrorLog.time_consumed,
            "test_start": ErrorLog.teststart,
            "total_testcase_count": len(statistics),
            "error_count": len(statistics.query(f'result == "{ResultTypes.FAILED.value}"')),
            "succesful_testcase_count": len(statistics.query(f'result == "{ResultTypes.SUCCESSFUL.value}"')),
            "API_call_errors": ErrorLog.backend_errors,
            "frontend_errors": ErrorLog.frontend_errors,
            "database_errors": ErrorLog.database_errors

        }
        return result

    @staticmethod
    def __create_text_log_post(log_directory: str):
        create_logging_directory(log_directory)
        statistics: DataFrame = get_statistics()
        successful_testcase_count = len(statistics.query(f'result == "{ResultTypes.SUCCESSFUL.value}"'))
        total_testcase_count = len(statistics)
        error_count = len(statistics.query(f'result == "{ResultTypes.FAILED.value}"'))

        file_name: str = f'{date_methods.get_current_time()}.txt'
        with open(create_logging_structure(log_directory) / file_name, "w", encoding="utf-8") as create:
            create.write(f"\nLOG {datetime.datetime.now()}")
            create.write(f"\n")
            create.write(f"\nSUMMARY")
            create.write(f"\n-------------------------------------")
            create.write(f"\ntime_consumed_in_seconds: {ErrorLog.time_consumed}")
            create.write(f"\ntest_start: {ErrorLog.teststart}")
            create.write(f"\ntotal_testcase_count: {total_testcase_count}")
            create.write(f"\nerror_count: {error_count}")
            create.write(f"\nsuccessful_testcase_count: {successful_testcase_count}")
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
                create.write(f"\n\n{json.dumps(error, indent=4, default=str, ensure_ascii=False)}")
                create.write(f"\n********************")
            create.write(f"\n")
            create.write(f"\nDATABASE_ERRORS")
            create.write(f"\n-------------------------------------")
            for error in ErrorLog.database_errors:
                create.write(f"\n********************")
                create.write(f"\n\n{json.dumps(error, indent=4, default=str, ensure_ascii=False)}")
                create.write(f"\n********************")

    @staticmethod
    def result_to_mongo_db() -> None:
        """Send the collected error records to the mongodb database"""

        mongo_datashare.insert_one(ErrorLog.__create_dictionary_log_post())

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
    def get_errors_per_frontendcases():
        """

        Collumns:
            name, result, errors_count
        Return:
            A Dataframe that show how many errors occured per testcase

        """
        frontend_errors: DataFrame = get_statistic(TestTypes.FRONTEND.value, ResultTypes.FAILED.value)
        frontend_statistic: DataFrame = frontend_errors[["name", "result"]].groupby("name", as_index=False).agg(
            errors_count=("result", "count"))
        return frontend_statistic

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
                    response_stats: DataFrame = get_statistic(TestTypes.BACKEND.value, ResultTypes.SLOW.value,
                                                              ResultTypes.SUCCESSFUL.value)
                    generate_bar_chart_from_dataframe(
                        data=response_stats, key_collumn="name",
                        value_collumn="required_time", title="response time/endpoint",
                        show_fig=show_chart_summary,
                        save_fig=save_charts,
                        fig_directory=fig_directory / f'{get_current_time()}.svg', x_label="timecost(sec)",
                        y_label="endpoint")
                    generate_pie_chart_from_simple_dict(
                        title="ERRORS/SUCCESSFUL TESTCASE RATIO",
                        data=ErrorLog.get_error_numbers_in_dict(),
                        show_fig=show_chart_summary,
                        save_fig=save_charts,
                        fig_directory=fig_directory / f'{get_current_time()}.svg')
                    generate_bar_chart_from_dataframe(title="FRONTEND ERORRS PER TESTCASE",
                                                      data=ErrorLog.get_errors_per_frontendcases(),
                                                      show_fig=show_chart_summary, key_collumn="name",
                                                      value_collumn="errors_count",
                                                      save_fig=save_charts,
                                                      fig_directory=fig_directory / f'{get_current_time()}.svg',
                                                      y_label="testcase", x_label="error count")
                    generate_figure_from_array(title="FULL-TEST SUMMARY",
                                               data=get_global_stats(),
                                               show_fig=show_chart_summary, x_axis_column="sum", x_label="quantity",
                                               y_axis_column="test_type", y_label="types", grouping_column="result",
                                               save_fig=save_charts,
                                               fig_directory=fig_directory / f'{get_current_time()}.svg')
                    generate_bar_chart_from_dataframe(
                        data=get_statistic(TestTypes.DATABASE.value, ResultTypes.FAILED.value,
                                           ResultTypes.SUCCESSFUL.value, ResultTypes.SLOW.value), key_collumn="name",
                        value_collumn="required_time", title="QUERY TIMES",
                        show_fig=show_chart_summary,
                        save_fig=save_charts,
                        fig_directory=fig_directory / f'{get_current_time()}.svg', x_label="required time",
                        y_label="query's name")

            return run_testcases

        return inner_method
