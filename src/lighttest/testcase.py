class Testcase:
    global_step_counter: int
    global_case_name: str
    global_case_steps: list[object] = list()

    def __init__(self, case_name: str):
        self.case_name: str = case_name
        self.step_counter: int = 0
        self.case_steps: list[object] = list()

    def add_case_step(self, case_step: object):
        self.step_counter += 1
        case_step.step_counter = self.step_counter
        self.case_steps.append(vars(case_step))

    @staticmethod
    def add_global_case_step(case_step: object):
        Testcase.global_step_counter += 1
        case_step.step_counter = Testcase.global_step_counter
        Testcase.global_case_steps.append(vars(case_step))
