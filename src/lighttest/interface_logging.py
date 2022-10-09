import dataclasses

from lighttest.core_interface_methods import Values, CaseStep, MiUsIn
from lighttest_supplies import date_methods
from os import makedirs
import datetime
from selenium.common.exceptions import WebDriverException
from src.lighttest.error_log import ErrorLog
from src.lighttest.core_interface_methods import CaseStep
from dataclasses import KW_ONLY


@KW_ONLY
class TestStep:
    case_object: CaseStep
    step_data: str = ""
    xpath: str


# currently it's not working
class Logging():

    @staticmethod
    def __testcase_logging(testcase_step) -> None:
        def asert(*args, **kwargs):
            step_datas: CaseStep = testcase_step(*args, **kwargs)
            step_datas.testcase.teststep_count += 1
            print(step_datas.__dict__)
            new_step: dict = {
                f'step {step_datas.testcase.teststep_count}': step_datas.__dict__}

            step_datas.testcase.steps_of_reproduction.update(new_step)

            if (step_datas.step_failed and step_datas.step_positivity == Values.POSITIVE.value) or (
                    step_datas.step_failed and step_datas.step_positivity == Values.NEGATIVE.value):
                MiUsIn._take_a_screenshot(step_datas.testcase)
                step_datas.testcase.error_in_case = True

        return asert

    @staticmethod
    def _take_a_screenshot(testcase: object):
        project_name = MiUsIn.driver.current_url \
            .split("//")[-1] \
            .split("/")[0] \
            .replace(".", "_") \
            .replace("www_", "")
        today = datetime.datetime.today()
        date_directory_name: str = f'{today.year}_{today.month}_{today.day}'
        hour_name: str = today.hour
        file_name: str = f'{date_methods.get_curent_time()}.png'

        file_path = fr"{testcase.screenshots_container_directory}\{project_name}\{date_directory_name}\{hour_name}"
        try:
            makedirs(file_path)
        except FileExistsError as error:
            print("multiple errors in the same hour. What an amazing day!")

        MiUsIn.driver.save_screenshot(fr'{file_path}\{file_name}')


def collect_data(mimic_type: str):
    def mimicing_function(mimic_fun):
        def collecting_data(*args, **kwargs):
            step_failed: bool = False
            new_error: str = ""
            try:
                case_object: TestStep = mimic_fun(*args, **kwargs)
            except WebDriverException as error:
                new_error = error
                ErrorLog.error_count_inc()
                step_failed = True

            step_datas = CaseStep(step_description=kwargs["step_description"], step_positivity="step_positivity",
                                  webelement_name="webelement_name", fatal_bug="major_bug", xpath=case_object.xpath,
                                  step_failed=step_failed, step_type=mimic_type, testcase=case_object.case_object,
                                  data=case_object.step_data, step_error=new_error)
            return step_datas

        return collecting_data

    return mimicing_function
