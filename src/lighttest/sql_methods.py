import sqlalchemy
from sqlalchemy.sql import select
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, DateTime, column, table, text


class SqlConnection:
    username: str = ""
    password: str = ""
    dbname: str = ""
    host: str = ""
    dialect_driver: str = ""
    port: str = ""

    db = f'{dialect_driver}://{username}:{password}@{host}:{port}/{dbname}'

    @staticmethod
    def connect(username, password, dbname, host, dialect_driver, port):

        SqlConnection.db = sqlalchemy.create_engine(f'{dialect_driver}://{username}:{password}@{host}:{port}/{dbname}')
        SqlConnection.cursor = SqlConnection.db.connect()

    @staticmethod
    def sql_select(*params, table_params=None, select_param=None, type: str = "param", text_query=""):
        """
        Create a query on the specified db.

        Arguments:
            params: the query param that you want to filtering with.
            table_params: list of colummns that are necessary in the result.
            format must be the following: table_name.c.column_name
            select_param: the name of the collumn where the filterparam is.
            format must be the following: table_name.c.column_name
            text_query: the whole query in string format. it only availabel if type value is "text"
            type: its value can be "param" or "text"
                if use "param", the *params, table_params and the select-params are required arguments
                if you use "text", the text_query param is required

        Return: the result-list of the query

        """
        s: object

        if type == "param":
            if params == () or table_params == None or select_param == None:
                raise Exception(
                    f"Missing required argument(s) in sql_select: {params=}, {table_params=}, {select_param=}")
            s = select(table_params).where(select_param.in_(tuple(params)))

        elif type == "text":
            if text_query == "" or None:
                raise Exception(f"Missing required argument(s) in sql_select: {text_query=}")
            s = text(text_query)

        con = SqlConnection.cursor
        result = con.execute(s)

        return result.fetchall()
