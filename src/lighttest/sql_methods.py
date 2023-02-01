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
# decorator
def assertion(assertion_fun):
    """
    It's a decorator. Use with methods that do assertion.
    """
    signature = inspect.signature(obj=assertion_fun).bind_partial()
    signature.apply_defaults()

    @wraps(assertion_fun)
    def assertion_method(*args, show_actual_result: bool = True, show_expected_result: bool = True,
                         performance_limit_in_seconds: float = 1,
                         attributes: dict = dict(), positivity: str = tt.POSITIVE.value,
                         **kwargs) -> QueryAssertionResult:
        actual_result: list[dict] = []
        expected_result: list[dict] = []

        completed_kwargs: dict = signature.arguments
        completed_kwargs.update(kwargs)

        perf_l = signature.args
        acceptable_performance: bool = performance_check(sql_result=completed_kwargs["result_informations"],
                                                         timelimit_in_seconds=performance_limit_in_seconds)

        assertion_result: QueryAssertionResult = assertion_fun(*args, **kwargs)
        errors = _ensure_mongodb_compatible(*assertion_result.errors)
        not_found_rows = _ensure_mongodb_compatible(*assertion_result.not_found_rows)

        if show_expected_result:
            expected_result = _ensure_mongodb_compatible(*completed_kwargs["expected_result"])
        if show_actual_result:
            actual_result = _ensure_mongodb_compatible(*assertion_result.query_result)

        match: bool = len(errors) + len(not_found_rows) == 0
        error_detected: bool = (positivity == tt.POSITIVE.value and (not match or not acceptable_performance)) or (
                positivity == tt.NEGATIVE.value and match)
        alias: str = completed_kwargs["result_informations"].alias

        if error_detected:
            error_post = QueryErrorPost(alias=alias,
                                        required_time=completed_kwargs["result_informations"].required_time,
                                        error_message=completed_kwargs["result_informations"].error_message,
                                        query=completed_kwargs["result_informations"].query,
                                        expected_query_timelimit=performance_limit_in_seconds,
                                        errors=errors, not_found_rows=not_found_rows,
                                        expected_result=expected_result,
                                        assertion_type=assertion_fun.__name__, actual_result=actual_result)
            ErrorLog.database_errors.append(vars(error_post))
        new_testresult(name=alias, result=_get_testresult_type(error_detected, match),
                       required_time=completed_kwargs["result_informations"].required_time,
                       test_type=TestTypes.DATABASE.value)

        return assertion_result

    return assertion_method


def _get_testresult_type(error_detected: bool, match: bool) -> str:
    """
    Return the type of the testresult. it can be succesful, slow or failed.
    """
    if error_detected and not match:
        return ResultTypes.FAILED.value
    elif error_detected and match:
        return ResultTypes.SLOW.value
    elif not error_detected and match:
        return ResultTypes.SUCCESSFUL.value


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
    def identical_match_assertion(self, result_informations: QueryResult,
                                  expected_result: list[dict]) -> QueryAssertionResult:
        """
        Check weather the result's and the expected result's length and the contained datas are exactly the same.

        Special keyword arguments:
            show_actual_result: If true, the error-logpost will contains the full result of the query.
                Default value: True
            performance_limit_in_seconds: Add a limit to query-response.
                If it cost more time than that, evaluated as failed query. default value: 1 second
            positivity: it determinate how to evaulate the result.
                it can be "positive" or "negative". default value: "positive"
            properties: Optional parameter. A dictionary, that contains other aspect of the query.

        Arguments:
             result_informations: an object which contains the result datas.
             expected_result: a list that contains table-rows as tuples.

        """
        result = result_informations.result.mappings().fetchall()
        identical_match = result == expected_result
        errors: set = {}
        if not identical_match:
            result_set = set({tuple(result_row.items()) for result_row in result})
            expected_result_set = set({tuple(result_row.items()) for result_row in expected_result})
            errors = expected_result_set.symmetric_difference(result_set)
        return QueryAssertionResult(errors=errors, not_found_rows=[], query_result=result)

    @assertion
    def subset_match_assertion(self, result_informations: QueryResult, expected_result: list[dict],
                               fetch_size: int = 1000) -> QueryAssertionResult:

        """
        Check weather the expected result is the subset of the actual result.

        Special keyword arguments:
            show_actual_result: If true, the error-logpost will contains the full result of the query.
                Default value: True
            performance_limit_in_seconds: Add a limit to query-response.
                If it cost more time than that, evaluated as failed query. default value: 1 second
            positivity: it determinate how to evaulate the result.
                it can be "positive" or "negative". default value: "positive"
            properties: Optional parameter. A dictionary, that contains other aspect of the query.

        Arguments:
             fetch_size: it set the pagesize of the resultcheck method. default: 1000/page
             result_informations: an object which contains the result datas.
             expected_result: a list that contains table-rows as tuples.
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
        return QueryAssertionResult(errors=unmatched_rows, not_found_rows=[], query_result=result_copy)

    @assertion
    def unique_match_assertion(self, unique_assertion, result_informations: QueryResult,
                               expected_result: list[dict] = []) -> QueryAssertionResult:
        """
            Check weather the expected result is accepted by a custom assertion.

            Special keyword arguments:
                show_actual_result: If true, the error-logpost will contains the full result of the query.
                    Default value: True
                performance_limit_in_seconds: Add a limit to query-response.
                    If it cost more time than that, evaluated as failed query. default value: 1 second
                positivity: it determinate how to evaulate the result.
                    it can be "positive" or "negative". default value: "positive"
                properties: Optional parameter. A dictionary, that contains other aspect of the query.

            Arguments:
                 result_informations: an object which contains the result datas.
                 expected_result: a list that contains table-rows as tuples.

        """

        query_result = result_informations.result.mappings().fetchall()
        errors: set = {}
        try:
            unique_assertion(query_result)
        except AssertionError as error:
            errors = {error.args}
        return QueryAssertionResult(errors={"error": errors}, not_found_rows=[], query_result=query_result)

    @assertion
    def deep_subset_match_assertion(self, column_name: str, result_informations: QueryResult,
                                    expected_result: list[dict],
                                    fetch_size: int = 1000) -> QueryAssertionResult:
        """
            Check weather the expected result is the subset of the actual result.
            If the expected row doesn't match with the actual result's row,
            compare and find which columns are different. Only the different columns appear in the error-logpost.

            Special keyword arguments:
                show_actual_result: If true, the error-logpost will contains the full result of the query.
                    Default value: True
                performance_limit_in_seconds: Add a limit to query-response.
                    If it cost more time than that, evaluated as failed query. default value: 1 second
                positivity: it determinate how to evaulate the result.
                    it can be "positive" or "negative". default value: "positive"
                properties: Optional parameter. A dictionary, that contains other aspect of the query.

            Arguments:
                 column_name: the column's name that will be used as an id to identify rows in the result
                    and compare it with the expected result's rows.
                 fetch_size: it set the pagesize of the resultcheck method. default: 1000/page
                 result_informations: an object which contains the result datas.
                 expected_result: a list that contains table-rows as tuples.

        """
        result_copy: set = set({})
        query_result = result_informations.result
        there_is_row_left_to_check: bool = True
        errors: list[dict] = []
        not_found_rows: list[dict] = []
        partial_result_set: set = set(query_result.mappings().fetchmany(fetch_size))
        while there_is_row_left_to_check:

            for expected_row in expected_result:
                actual_row = find_row_by_id(collumn_name=column_name, expexted_row=expected_row,
                                            result=partial_result_set)
                compare_rows(expected_row=expected_row, actual_row=actual_row, error_container=errors,
                             column_name=column_name, skipp_empty_row=True)
                if actual_row is not None:
                    result_copy.update(set(partial_result_set))
                    partial_result_set.remove(actual_row)
                else:
                    not_found_rows.append(expected_row)

            partial_result_set = set(query_result.mappings().fetchmany(fetch_size))
            there_is_row_left_to_check = len(partial_result_set) != 0
        return QueryAssertionResult(errors=errors, not_found_rows=not_found_rows, query_result=result_copy)

    @assertion
    def query_result_comparator(self, column_name: str, result_informations: QueryResult,
                                expected_result: QueryResult,
                                fetch_size: int = 1000) -> QueryAssertionResult:
        """
            Check weather the expected result is the subset of the actual result.
            If the expected row doesn't match with the actual result's row,
            compare and find which columns are different. Only the different columns appear in the error-logpost.

            Special keyword arguments:
                show_actual_result: If true, the error-logpost will contains the full actual result of the query. Default value: True \n
                show_expected_result: If true, the error-logpost will contains the expected result of the query. Default value: True
                performance_limit_in_seconds: Add a limit to query-response.
                    If it cost more time than that, evaluated as failed query. default value: 1 second
                positivity: it determinate how to evaulate the result.
                    it can be "positive" or "negative". default value: "positive"
                properties: Optional parameter. A dictionary, that contains other aspect of the query.

            Arguments:
                 column_name: the column's name that will be used as an id to identify rows in the result
                    and compare it with the expected result's rows.
                 fetch_size: it set the pagesize of the resultcheck method. default: 1000/page
                 result_informations: an object which contains the result datas.
                 expected_result: a list that contains table-rows as tuples.
                 full_result_check: If true, iterating through the full query by fetch_size
        """

        result_copy: set = set({})
        actual_result_rows = result_informations.result
        expected_result_rows = expected_result.result

        there_is_row_left_to_check: bool = True
        errors: list[dict] = []
        partial_result_set: set = set(actual_result_rows.mappings().fetchmany(fetch_size))
        expected_result_set: set = set(expected_result_rows.mappings().fetchmany(fetch_size))
        not_found_rows: set = set()
        while there_is_row_left_to_check:

            result_copy.update(partial_result_set)
            sim_dif: set = expected_result_set.symmetric_difference(partial_result_set)
            expected_result_set.intersection_update(sim_dif)
            partial_result_set.intersection_update(sim_dif)
            for expected_row in not_found_rows.copy():
                actual_row = find_row_by_id(collumn_name=column_name, expexted_row=expected_row,
                                            result=partial_result_set)
                compare_rows(expected_row=expected_row, actual_row=actual_row, error_container=errors,
                             column_name=column_name, skipp_empty_row=True)
                if actual_row is not None:
                    not_found_rows.remove(expected_row)
                    partial_result_set.remove(actual_row)

            for expected_row in expected_result_set:
                actual_row = find_row_by_id(collumn_name=column_name, expexted_row=expected_row,
                                            result=partial_result_set)
                compare_rows(expected_row=expected_row, actual_row=actual_row, error_container=errors,
                             column_name=column_name, skipp_empty_row=True)
                if actual_row is not None:
                    partial_result_set.remove(actual_row)
                else:
                    not_found_rows.add(expected_row)

            expected_result_set: set = set(expected_result_rows.mappings().fetchmany(fetch_size))
            partial_result_set = set(actual_result_rows.mappings().fetchmany(fetch_size)).union(partial_result_set)
            there_is_row_left_to_check = (len(expected_result_set) + len(not_found_rows) != 0) and (
                    len(partial_result_set) and len(expected_result_set) != 0)

        return QueryAssertionResult(errors=errors, not_found_rows=list(not_found_rows), query_result=result_copy)


def performance_check(sql_result: QueryResult, timelimit_in_seconds: float) -> bool:
    performance_check_result = sql_result.required_time < timelimit_in_seconds
    return performance_check_result


def find_row_by_id(collumn_name: str, expexted_row: dict, result: set[dict]) -> dict | None:
    """
    return a row from the actual result which identified by an id-column in the expected result.

    Return:
        If there is matching id, return the row with that id. Else, return None.
    """
    try:
        id: object = expexted_row[collumn_name]
        for row in result:
            if row[collumn_name] == id:
                return row
    except KeyError:
        return None
    return None


def compare_rows(expected_row: dict, actual_row: dict, error_container: list[dict], column_name: str,
                 skipp_empty_row: bool = False, complete_expected_row: bool = False) -> None:
    """
    compare a row from the expected result with a row from the actual result.
    """
    errors_in_row: set = {}

    if actual_row is None and not skipp_empty_row:
        error_container.append({"error_in_row": tuple(expected_row.items()), "id": "Match not found!"})
        return
    if actual_row is not None:
        row_data = set(expected_row.items())
        row_data.difference_update(set(actual_row.items()))
        errors_in_row = row_data
        if len(errors_in_row) != 0:
            _add_error_to_container(errors_in_row=errors_in_row, error_container=error_container, actual_row=actual_row,
                                    expected_row=expected_row, complete_expected_row=complete_expected_row,
                                    key_column=column_name)


def _add_error_to_container(errors_in_row: set[tuple], key_column: str, error_container: list[dict], actual_row: dict,
                            expected_row: dict,
                            complete_expected_row: bool = False):
    if complete_expected_row:
        completed_expected_row = dict(actual_row)
        completed_expected_row.update(expected_row)

    else:
        completed_expected_row = expected_row

    actual_data = tuple(set(tuple(actual_row.items())).difference(set(tuple(completed_expected_row.items()))))
    formatted_errors: tuple[tuple] = tuple(errors_in_row, )

    error_container.append(
        {"error_in_row": formatted_errors, "id": {key_column: actual_row[key_column]},
         "actual_datas": actual_data})


def _ensure_mongodb_compatible(*args):
    formatted_list: list = []
    for element in args:
        formatted_element: dict = _format_list_element(element)
        formatted_list.append(formatted_element)
    return formatted_list


def _decimals_in_dict_to_int(dictionary: dict):
    for key in dictionary.keys():
        if isinstance(dictionary[key], Decimal):
            dictionary[key] = int(dictionary[key])


def _format_list_element(element):
    if isinstance(element, dict):
        for key, value in element.items():
            if isinstance(element[key], tuple):
                element[key] = _format_list_element(element[key])

    new_dict = dict(element)
    _decimals_in_dict_to_int(new_dict)

    return new_dict
