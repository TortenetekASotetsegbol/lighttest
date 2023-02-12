from functools import wraps


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

    @staticmethod
    def add_global_case_step(case_step: object):
        Testcase.global_step_counter += 1
        case_step.step_counter = Testcase.global_step_counter
        Testcase.global_case_steps.append(vars(case_step))

    def add_case_step(self, case_step: dict):
        self.step_counter += 1
        case_step.update({"step_id": self.step_counter})
        self.case_steps.append(vars(case_step))

    def close_case(self):
        if self.error_counter > 0:
            ErrorLog.errors.append({self.case_name: self.case_steps})
        del self

    @staticmethod
    def case_step(case_method):
        # decorator
        @wraps(case_method)
        def method(*args, **kwargs):
            testcase_object: Testcase = args[0].testcase
            if testcase_object.critical_error:
                return

            case_method(*args, *kwargs)

            return None

        return method
