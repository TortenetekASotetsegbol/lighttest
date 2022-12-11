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
from decimal import Decimal

from lighttest.datacollections import QueryResult, QueryErrorPost, TestTypes, ResultTypes, QueryAssertionResult


# decorator
def execute_query(sql_query):
    """
    It's a decorator. Use for methods that execute a query.
    """

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
    """
    It's a decorator. Use with methods that do assertion.
    """
    signature_test = inspect.signature(obj=assertion_fun).bind_partial()
    signature_test.apply_defaults()

    @wraps(assertion_fun)
    def assertion_method(*args, show_actual_result: bool = True, **kwargs):
        completed_kwargs: dict = signature_test.arguments
        completed_kwargs.update(kwargs)

        expected_result: list = _ensure_mongodb_compatible(*completed_kwargs["expected_result"])
        perf_l = signature_test.args
        acceptable_performance: bool = performance_check(sql_result=completed_kwargs["result_informations"],
                                                         timelimit_in_seconds=completed_kwargs[
                                                             "performance_limit_in_seconds"])

        assertion_result: QueryAssertionResult = assertion_fun(*args, **kwargs)
        errors = _ensure_mongodb_compatible(*assertion_result.errors)

        actual_result: list[str] = []
        if show_actual_result:
            actual_result = _ensure_mongodb_compatible(*assertion_result.query_result)

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
                                        assertion_type=assertion_fun.__name__, actual_result=actual_result)
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
    def sql_query_by_text(self, text_query: str, alias: str) -> QueryResult:
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
            alias: use this keyword to add this query a name/id

        Return: the result_informations-list of the query

        """
        query: object = select(table_params).where(select_param.in_(tuple(params)))
        return query

    @assertion
    def identical_match_assertion(self, result_informations: QueryResult, expected_result: list[dict],
                                  performance_limit_in_seconds: float = 1,
                                  properties: dict = {tt.POSITIVITY.value: tt.POSITIVE.value}) -> set[tuple]:
        """
        Check weather the result's and the expected result's length and the contained datas are exactly the same.

        Special keyword arguments:
            show_actual_result: If true, the error-logpost will contains the full result of the query.
                Default value: True

        Arguments:
             result_informations: an object which contains the result datas.
             expected_result: a list that contains table-rows as tuples.
             performance_limit_in_seconds: Add a limit to query-response.
                If it cost more time than that, evaluated as failed query.
             properties: a dictionary, that contains other aspect of the query. Default contained value:
                {positivity: positive}
        """
        result = result_informations.result.mappings().fetchall()
        identical_match = result == expected_result
        errors: set = {}
        if not identical_match:
            result_set = set({tuple(result_row.items()) for result_row in result})
            expected_result_set = set({tuple(result_row.items()) for result_row in expected_result})
            errors = expected_result_set.symmetric_difference(result_set)
        return QueryAssertionResult(errors=errors, query_result=result)

    @assertion
    def subset_match_assertion(self, result_informations: QueryResult, expected_result: list[dict],
                               fetch_size: int = 1000,
                               performance_limit_in_seconds: float = 1,
                               properties: dict = {tt.POSITIVITY.value: tt.POSITIVE.value}) -> set[tuple]:

        """
        Check weather the expected result is the subset of the actual result.

        Special keyword arguments:
            show_actual_result: If true, the error-logpost will contains the full result of the query.
                Default value: True

        Arguments:
             fetch_size: it set the pagesize of the resultcheck method. default: 1000/page
             result_informations: an object which contains the result datas.
             expected_result: a list that contains table-rows as tuples.
             performance_limit_in_seconds: Add a limit to query-response.
                If it cost more time than that, evaluated as failed query.
             properties: a dictionary, that contains other aspect of the query. Default contained value:
                {positivity: positive}
        """
        query_result = result_informations.result
        unmatched_rows: set = set({tuple(result_row.items()) for result_row in expected_result})
        there_is_row_left_to_check: bool = True
        result_copy: set = set({})
        while there_is_row_left_to_check:
            partial_result_set: set = set(
                {tuple(result_row.items()) for result_row in query_result.mappings().fetchmany(fetch_size)})
            result_copy.update(partial_result_set)
            unmatched_rows.difference_update(partial_result_set)
            there_is_row_left_to_check = len(partial_result_set) != 0
        return QueryAssertionResult(errors=unmatched_rows, query_result=result_copy)

    @assertion
    def unique_match_assertion(self, unique_assertion, result_informations: QueryResult,
                               expected_result: list[tuple] = [],
                               performance_limit_in_seconds: float = 1,
                               properties: dict = {tt.POSITIVITY.value: tt.POSITIVE.value}) -> set[tuple]:
        """
            Check weather the expected result is accepted by a custom assertion.

            Special keyword arguments:
                show_actual_result: If true, the error-logpost will contains the full result of the query.
                    Default value: True

            Arguments:
                 result_informations: an object which contains the result datas.
                 expected_result: a list that contains table-rows as tuples.
                 performance_limit_in_seconds: Add a limit to query-response.
                    If it cost more time than that, evaluated as failed query.
                 properties: a dictionary, that contains other aspect of the query. Default contained value:
                    {positivity: positive}
        """

        query_result = result_informations.result.fetchall()
        errors: set = {}
        try:
            unique_assertion(query_result)
        except AssertionError as error:
            errors = {error.args}
        return QueryAssertionResult(errors={"error": errors}, query_result=query_result)

    @assertion
    def deep_subset_match_assertion(self, column_name: str, result_informations: QueryResult,
                                    expected_result: list[dict],
                                    fetch_size: int = 1000,
                                    performance_limit_in_seconds: float = 1,
                                    properties: dict = {
                                        tt.POSITIVITY.value: tt.POSITIVE.value}) -> QueryAssertionResult:
        """
            Check weather the expected result is the subset of the actual result.
            If the expected row doesn't match with the actual result's row,
            compare and find which columns are different. Only the different columns appear in the error-logpost.

            Special keyword arguments:
                show_actual_result: If true, the error-logpost will contains the full result of the query.
                    Default value: True

            Arguments:
                 column_name: the column's name that will be used as an id to identify rows in the result
                    and compare it with the expected result's rows.
                 fetch_size: it set the pagesize of the resultcheck method. default: 1000/page
                 result_informations: an object which contains the result datas.
                 expected_result: a list that contains table-rows as tuples.
                 performance_limit_in_seconds: Add a limit to query-response.
                    If it cost more time than that, evaluated as failed query.
                 properties: a dictionary, that contains other aspect of the query. Default contained value:
                    {positivity: positive}
        """
        result_copy: set = set({})
        query_result = result_informations.result
        there_is_row_left_to_check: bool = True
        errors: list[dict] = []
        partial_result_set: set = set(query_result.mappings().fetchmany(fetch_size))
        while there_is_row_left_to_check:

            for expected_row in expected_result:
                actual_row = find_row_by_id(collumn_name=column_name, expexted_row=expected_row,
                                            result=partial_result_set)
                compare_rows(expected_row=expected_row, actual_row=actual_row, error_container=errors,
                             column_name=column_name)
                if actual_row is not None:
                    result_copy.update(set(partial_result_set))
                    partial_result_set.remove(actual_row)

            partial_result_set = set(query_result.mappings().fetchmany(fetch_size))
            there_is_row_left_to_check = len(partial_result_set) != 0
        return QueryAssertionResult(errors=errors, query_result=result_copy)


def performance_check(sql_result: QueryResult, timelimit_in_seconds: float) -> bool:
    performance_check_result = sql_result.required_time < timelimit_in_seconds
    return performance_check_result


def find_row_by_id(collumn_name: str, expexted_row: dict, result: set[dict]) -> dict | None:
    """
    return a row from the actual result which identified by an id-column in the expected result.
    """
    id: object = expexted_row[collumn_name]
    for row in result:
        if row[collumn_name] == id:
            return row
    return None


def compare_rows(expected_row: dict, actual_row: dict, error_container: list[dict], column_name: str) -> None:
    """
    compare a row from the expected result with a row from the actual result.
    """
    errors_in_row: set = {}
    if actual_row is None:
        error_container.append({"error_in_row": tuple(expected_row.items()), "id": "Match not found!"})
        return
    row_data = set(expected_row.items())
    row_data.difference_update(set(actual_row.items()))
    errors_in_row = row_data
    if len(errors_in_row) != 0:
        formatted_errors: tuple[tuple] = tuple(errors_in_row, )
        error_container.append(
            {"error_in_row": formatted_errors, "id": {column_name: actual_row[column_name]}})


def _ensure_mongodb_compatible(*args):
    formatted_list: list = []
    for element in args:
        formatted_element: dict = _format_list_element(element)
        formatted_list.append(formatted_element)
    return formatted_list


def _decimals_in_dict_to_int(dictionary: dict):
    for key in dictionary.keys():
        if type(dictionary[key]) == Decimal:
            dictionary[key] = int(dictionary[key])


def _format_list_element(element):
    if type(element) == dict:
        for key, value in element.items():
            if type(element[key]) == tuple:
                element[key] = _format_list_element(element[key])

    new_dict = dict(element)
    _decimals_in_dict_to_int(new_dict)

    return new_dict
