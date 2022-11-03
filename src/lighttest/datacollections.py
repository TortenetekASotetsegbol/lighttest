import json
from dataclasses import dataclass
from enum import unique, Enum

from sqlalchemy.engine import CursorResult


@dataclass(kw_only=True)
class TestResult:
    fast: bool
    successful: bool


@unique
class ResultTypes(Enum):
    SUCCESSFUL: str = "successful"
    FAILED: str = "failed"
    SLOW: str = "slow"
    UNRECOGNISABLE = "UNRECOGNISABLE"


@unique
class TestTypes(Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"


@dataclass(kw_only=True)
class BackendPerformanceStatisticPost:
    result: str
    request_url: str
    response_time: float


@dataclass(kw_only=True)
class PerformancePost:
    name: str
    required_time: float


@dataclass(kw_only=True)
class UniversalPerformancePost:
    test_type: str
    name: str
    required_time: float
    result: str


@dataclass(kw_only=True)
class BackendError:
    req_payload: dict
    req_response: dict
    statuscode: int
    performance_in_seconds: float
    properties: dict
    id: str
    error_desc: str
    request_url: str


@dataclass(kw_only=True)
class QueryResult:
    required_time: float
    result: CursorResult
    query: str
    alias: str
    error_message: str = ""


@dataclass(kw_only=True)
class QueryErrorPost:
    alias: str
    expected_query_timelimit: float
    required_time: float
    query: str
    error_message: str
    missing_or_invalid_elements: object
    expected_result: set
    assertion_type: str


@dataclass(kw_only=True)
class CaseStep:
    """
    contains every necessary information about the case's step.
    """
    xpath: str
    webelement_name: str
    fatal_bug: bool
    step_positivity: str
    step_description: str
    step_failed: bool
    step_type: str
    step_error: str

    data: str = ""


@dataclass()
class BackendResultDatas:
    url: str = ""
    response_time: int = 0
    headers: json = None
    request: json = None
    status_code: int = None
    response_json: json = None
