import sqlalchemy
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql import select
from sqlalchemy import text
from lighttest_supplies.general_datas import TestType as tt
from lighttest_supplies.timers import Utimer
from sqlalchemy.exc import ProgrammingError, TimeoutError, DatabaseError
from functools import wraps
from lighttest.test_summary import ErrorLog, SumDatabaseTests, PerformancePost, new_testresult
import inspect

from lighttest.datacollections import QueryResult, QueryErrorPost, TestTypes, ResultTypes


# decorator
def execute_query(sql_query):
    @wraps(sql_query)
    def query_method(*args, **kwargs):
        con = None
        connection_object: SqlConnection = args[0]
        measure_performance = Utimer()
        query = str(sql_query(*args, **kwargs))
        error: str = ""
        measure_performance.set_start()
        try:
            con = connection_object.cursor

        except (ProgrammingError, TimeoutError, DatabaseError) as sql_error:
            error = sql_error
        result: CursorResult = con.execute(text(query))
        measure_performance.set_end()
        query_result = QueryResult(required_time=measure_performance.elapsed_time(), result=result, error_message=error,
                                   query=query, alias=kwargs["alias"])
        return query_result

    return query_method


# decorator
def assertion(assertion_fun):
    signature_test = inspect.signature(obj=assertion_fun).bind_partial()
    signature_test.apply_defaults()

    @wraps(assertion_fun)
    def assertion_method(*args, **kwargs):
        completed_kwargs: dict = signature_test.arguments
        completed_kwargs.update(kwargs)

        expected_result: set = set(completed_kwargs["expected_result"])
        perf_l = signature_test.args
        acceptable_performance: bool = performance_check(sql_result=completed_kwargs["result_informations"],
                                                         timelimit_in_seconds=completed_kwargs[
                                                             "performance_limit_in_seconds"])
        errors = assertion_fun(*args, **kwargs)
        match: bool = len(errors) == 0
        positivity: str = signature_test.kwargs["properties"][tt.POSITIVITY.value]
        found_error: bool = (positivity == tt.POSITIVE.value and (not match or not acceptable_performance)) or (
                positivity == tt.NEGATIVE.value and match)
        alias: str = completed_kwargs["result_informations"].alias
        if found_error:
            if not match:
                new_testresult(name=alias, result=ResultTypes.FAILED.value,
                               required_time=completed_kwargs["result_informations"].required_time,
                               test_type=TestTypes.DATABASE.value)
            else:
                new_testresult(name=alias, result=ResultTypes.SLOW.value,
                               required_time=completed_kwargs["result_informations"].required_time,
                               test_type=TestTypes.DATABASE.value)

            error_post = QueryErrorPost(alias=alias,
                                        required_time=completed_kwargs["result_informations"].required_time,
                                        error_message=completed_kwargs["result_informations"].error_message,
                                        query=completed_kwargs["result_informations"].query,
                                        expected_query_timelimit=completed_kwargs["performance_limit_in_seconds"],
                                        missing_or_invalid_elements=errors, expected_result=expected_result,
                                        assertion_type=assertion_fun.__name__)
            ErrorLog.database_errors.append(vars(error_post))
        else:
            new_testresult(name=alias, result=ResultTypes.SUCCESSFUL.value,
                           required_time=completed_kwargs["result_informations"].required_time,
                           test_type=TestTypes.DATABASE.value)

        kwargs["result_informations"].result.close()

    return assertion_method


class SqlConnection:

    def __init__(self, username, password, dbname, host, dialect_driver, port):
        self.engine = sqlalchemy.create_engine(f'{dialect_driver}://{username}:{password}@{host}:{port}/{dbname}')
        self.cursor = self.engine.connect()

    def connect(self, username, password, dbname, host, dialect_driver, port):
        self.engine = sqlalchemy.create_engine(f'{dialect_driver}://{username}:{password}@{host}:{port}/{dbname}')
        self.cursor = self.engine.connect()

    @execute_query
    def sql_query_by_text(self, text_query: str, alias: str):
        """
        Create a query on the specified engine.

        Arguments:
            text_query: the whole query in string format.

        Return:
            QueryResult object
        """
        query: object = text(text_query)
        return query

    @execute_query
    def sql_select_by_param(self, *params, alias: str, table_params=None, select_param=None):
        """
        Create a query on the specified engine.

        Arguments:
            params: the query param that you want to filtering with.
            table_params: list of colummns that are necessary in the result_informations.
            format must be the following: table_name.c.column_name
            select_param: the name of the collumn where the filterparam is.
            format must be the following: table_name.c.column_name

        Return: the result_informations-list of the query

        """
        query: object = select(table_params).where(select_param.in_(tuple(params)))
        return query

    @assertion
    def identical_match_assertion(self, result_informations: QueryResult, expected_result: list[tuple],
                                  performance_limit_in_seconds: float = 1,
                                  properties: dict = {tt.POSITIVITY.value: tt.POSITIVE.value}) -> set[tuple]:
        result = result_informations.result.fetchall()
        identical_match = result == expected_result
        errors: set = {}
        if not identical_match:
            result_set = set(result)
            expected_result_set = set(expected_result)
            errors = expected_result_set.symmetric_difference(result_set)
        return errors

    @assertion
    def subset_match_assertion(self, result_informations: QueryResult, expected_result: list[tuple],
                               fetch_size: int = 1000,
                               performance_limit_in_seconds: float = 1,
                               properties: dict = {tt.POSITIVITY.value: tt.POSITIVE.value}) -> set[tuple]:
        query_result = result_informations.result
        unmatched_rows: set = set(expected_result)
        there_is_row_left_to_check: bool = True
        while there_is_row_left_to_check:
            partial_result_set: set = set(query_result.fetchmany(fetch_size))
            unmatched_rows.difference_update(partial_result_set)
            there_is_row_left_to_check = len(partial_result_set) != 0
        return unmatched_rows

    @assertion
    def unique_match_assertion(self, unique_assertion, result_informations: QueryResult,
                               expected_result: list[tuple] = [],
                               performance_limit_in_seconds: float = 1,
                               properties: dict = {tt.POSITIVITY.value: tt.POSITIVE.value}) -> set[tuple]:
        query_result = result_informations.result
        errors: set = {}
        try:
            unique_assertion(query_result)
        except AssertionError as error:
            errors = {error.args}
        return errors


def performance_check(sql_result: QueryResult, timelimit_in_seconds: float) -> bool:
    performance_check_result = sql_result.required_time < timelimit_in_seconds
    return performance_check_result

# TODO change the ploting. It must contains automatic size-calibration
# TODO change the datacollecting method by make them universal.
#  Before Plotting, the universal informations must be filtered.
# TODO extract form error_log modul all the statistic class to a new statistics module
# TODO rename the error_log module to logging
