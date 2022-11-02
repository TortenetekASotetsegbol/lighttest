import datetime
from dataclasses import dataclass
from dataclasses import KW_ONLY
from enum import Enum, unique
from os import makedirs

from lighttest.error_log import ErrorLog
from lighttest_supplies import date_methods
from lighttest_supplies.timers import Utimer

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, \
    ElementClickInterceptedException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import color
from selenium.common import exceptions
from inspect import signature
from lighttest_supplies.general import create_logging_structure, create_logging_directory, create_directory
from pathlib import Path


def collect_data(mimic_type: str):
    def mimicing_function(mimic_fun):

        def collecting_data(*args, **kwargs):

            case_object: MiUsIn = args[0]
            if case_object.casebreak:
                return None

            if "step_description" not in kwargs.keys():
                kwargs.update({"step_description": ""})
            if "step_positivity" not in kwargs.keys():
                kwargs.update({"step_positivity": Values.POSITIVE.value})
            if "webelement_name" not in kwargs.keys():
                kwargs.update({"webelement_name": ""})
            if "major_bug" not in kwargs.keys():
                kwargs.update({"major_bug": False})

            step_failed: bool = False
            new_error: str = ""
            try:
                mimic_fun(*args, **kwargs)

            except (exceptions.WebDriverException, ValueError) as error:
                # case_object.casebreak_alarm(major_bug=kwargs["major_bug"])
                new_error = error
                # ErrorLog.error_count_inc()
                step_failed = True

            if "xpath" not in kwargs.keys():
                kwargs.update({"xpath": ""})
            if "data" not in kwargs.keys():
                kwargs.update({"data": ""})
            step_datas = CaseStep(step_description=kwargs['step_description'],
                                  step_positivity=kwargs['step_positivity'],
                                  webelement_name=kwargs['webelement_name'], fatal_bug=kwargs['major_bug'],
                                  xpath=kwargs['xpath'], step_failed=step_failed, step_type=mimic_type,
                                  data=kwargs['data'], step_error=new_error)
            return step_datas

        return collecting_data

    return mimicing_function


@unique
class Values(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

    CLICK = "click"
    DOUBLE_CICK = "double click"
    PRESS_KEY = "press key"
    PRESS_ENTER = "press enter"
    PRESS_TAB = "press tab"
    PRESS_ESC = "press escape"
    READ = "read"
    SEND_KEYS = "send keys"
    COMBOBOX = "combobox"
    ACCESSIBILITY = "accessibility"
    CONDITION_CHECK = "condition check"
    CHECK_STYLE = "check style"
    CHECK_TEXT = "check text"


@unique
class InnerStatics(Enum):
    PARAM: str = "__param__"
    FIND_LABEL_BY_PARAM: str = "//*[text()='__param__']"
    IN_PARENT_FIND_LABEL_BY_PARAM: str = ".//*[text()='__param__']"


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


@dataclass(kw_only=True)
class TestStep:
    case_object: CaseStep
    xpath: str
    step_data: str = ""


class MiUsIn:
    """
    MiUsIn stand for Mimic User interactions.
    Variables:
        driver: this is the google chrome's webdriver. Every browser interaction use this particular driver.
        bomb_timeout: Its defining how much time need the @bomb decorator to raise timeout error
        global_combobox_parent_finding_method_by_xpath: the value of this param determinate
                how to find combobox parent webelement
    """
    driver: webdriver.Chrome = None
    action_driver: ActionChains = None
    bomb_timeout: float = 1
    global_combobox_parent_finding_method_by_xpath: [str] = []
    global_field_xpath: [str] = []
    global_webalert_xpath: str = None

    def __init__(self, case_name: str, fullsize_windows=True,
                 screenshots_container_directory: str = "C:\Screenshots", ):
        """
        placeholder

        Arguments:
            fullsize_windows: If true, the browser's windows will b full-sized
            screenshots_container_directory: If during a testcase it find an error
                    the screenshot taken of the error will be stored and catalogised in that directory
        """
        if MiUsIn.driver is None:
            MiUsIn.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            MiUsIn.action_driver = ActionChains(MiUsIn.driver)
        MiUsIn.driver.implicitly_wait(time_to_wait=5)
        self.case_name = case_name
        self.casebreak = False
        self.steps_of_reproduction: dict = {}
        self.testcase_failed: bool = False
        self.teststep_count = 0
        self.error_in_case = False
        self.error_count: int = 0
        self.screenshots_container_directory: str = screenshots_container_directory
        self.combobox_parent_finding_method_by_xpath: [str] = []
        self.local_field_xpath: str = None

        ErrorLog.total_case_count_inc()

        if fullsize_windows:
            MiUsIn.driver.maximize_window()

    def __del__(self):
        pass

    def close_case(self):
        """
        This method must to be on the end of every testcase. it send the collected
        frontend_errors - and the steps led to the error - into the log.
        """
        if self.error_in_case:
            ErrorLog.add_frontend_error(self.steps_of_reproduction)
            self.stack_dict_item(updater={self.case_name: self.error_count}, current_dict=ErrorLog.error_per_frontend_case)
            ErrorLog.error_count_inc()

            del self

    def stack_dict_item(self, updater: dict, current_dict: dict):

        if list(updater.keys())[0] not in list(current_dict.keys()):
            current_dict.update(updater)
        else:
            current_dict[list(updater.keys())[0]] += updater[list(updater.keys())[0]]

    def set_combobox_parent_finding_method_by_xpath(self, *xpaths: str):
        """
        @param: global_combobox_parent_finding_method_by_xpath the value of this param determinate
                how to find combobox parent webelement
        """
        self.combobox_parent_finding_method_by_xpath: [str] = xpaths

    @staticmethod
    def set_global_field_xpath(*xpaths: str):
        """
        placeholder

        Arguments:
            *xpaths: the value of this param determinate
                    how to find fields in global.

        Format:
            the paramter in the xpath need to be the following: __param__

        Example:
            set_case_field_xpath("//*[text()='__param__']/parent::*/descendant::input",
            "//*[text()='__param__']/parent::*/descendant::textarea")

        """
        MiUsIn.global_field_xpath = xpaths

    def set_case_field_xpath(self, *xpaths: str):
        """
        placeholder

        Arguments:
            *xpaths: the value of this param determinate
                    how to find fields in the level of testcase.

        Format:
            the paramter in the xpath need to be the following: __param__

        Example:
            set_case_field_xpath("//*[text()='__param__']/parent::*/descendant::input",
            "//*[text()='__param__']/parent::*/descendant::textarea")

        """
        self.local_field_xpath = xpaths

    @staticmethod
    def set_global_combobox_parent_finding_method_by_xpath(*xpaths: str):
        '''
        field_xpath : it set the global_combobox_parent_finding_method_by_xpath class variable
        '''
        MiUsIn.global_combobox_parent_finding_method_by_xpath = xpaths

    @staticmethod
    def __create_alert_xpath(alert_message: str):
        if MiUsIn.global_webalert_xpath is None:
            created_alert_xpath = f"//*[contains(text(),'{alert_message}')]"
        else:
            created_alert_xpath = MiUsIn.global_webalert_xpath

        return created_alert_xpath

    @staticmethod
    def jump_webpage(url: str) -> None:
        """
        the browser navigate to the desired url.
        """
        MiUsIn.driver.get(url)

    @staticmethod
    def end() -> None:
        """
        It close the webdriver session, close every windows.
        """
        MiUsIn.driver.quit()

    @staticmethod
    def set_implicitly_wait(time_to_wait: float) -> None:
        """
        for every event (example: find a webelement), the webdriver will wait till maximum the value of the time_to_wait
        """
        MiUsIn.driver.implicitly_wait(time_to_wait=time_to_wait)

    @staticmethod
    def set_bomb_timeout(timeout: float) -> None:
        """
        Set the timeout value for the bomb decorator.
        """
        MiUsIn.bomb_timeout = timeout

    @staticmethod
    def __testcase_logging(testcase_step) -> None:
        """
        It is a decorator. It can be use with webdriver interactions that return a CaseStep object.
        This method does the preparation of the log comment from the Testcase. This makes part of the assertion,
        it analising that the teststep and the testcase weather failed or not and takes screenshots of the error.
        """

        def asert(*args, **kwargs):
            case_object: MiUsIn = args[0]
            step_datas: CaseStep = testcase_step(*args, **kwargs)
            if step_datas is None:
                return
            case_object.teststep_count += 1

            new_step: dict = {
                f'step {case_object.teststep_count}': step_datas.__dict__}

            case_object.steps_of_reproduction.update(new_step)

            if (step_datas.step_failed and step_datas.step_positivity == Values.POSITIVE.value) or (
                    step_datas.step_failed and step_datas.step_positivity == Values.NEGATIVE.value):
                case_object.error_count += 1
                case_object.casebreak_alarm(major_bug=step_datas.fatal_bug)
                MiUsIn._take_a_screenshot(case_object)

                case_object.error_in_case = True

        return asert

    @staticmethod
    def _take_a_screenshot(testcase: object):
        """
        Take a screenshot and save it in a directory structure.

        directory structure:
            C:/screenshots/automatically generated project directory from the webpage URL/
            generated date directory/generated hour directory/screenshot.png
        """
        project_name = MiUsIn.driver.current_url \
            .split("//")[-1] \
            .split("/")[0] \
            .replace(".", "_") \
            .replace("www_", "")

        file_name: str = f'{date_methods.get_current_time()}.png'
        create_logging_directory(testcase.screenshots_container_directory, project_name)
        screenshot_path = create_logging_structure(testcase.screenshots_container_directory, project_name)
        MiUsIn.driver.save_screenshot(f"{screenshot_path.absolute()}/{file_name}")

    @__testcase_logging
    @collect_data(mimic_type=Values.CONDITION_CHECK.value)
    def expected_condition(self, timeout_in_seconds: float, expected_condition: expected_conditions = None,
                           until_not: bool = False, webelement_is_visible=False, webelement_is_clickable=False,
                           alert: str = None, webelement_name: str = "", major_bug: bool = False,
                           step_positivity: str = Values.POSITIVE.value,
                           step_description: str = "", xpath=None):
        """
        Arguments:
           timeout_in_seconds: Set the timer. If the expected condition is not happening under that timeperiod,
                               the test-step failed
           expected_condition: the condition, you waiting for.
           until_not: it negate the condition. for example: if you were waited for the appearence of an element,
                       with the until_not = true setting you wait for the disappearence of the element
           webelement_is_visible: set the expected condition for the visibility of an element.
                                   if the webelement described by the field_xpath is not appearing before the timeout,
                                   the step failed
           webelement_is_clickable: set the expected condition to clickability of an element.
                                   if the webelement described by the field_xpath is not became clickable before the timeout,
                                   the step failed
           expected_condition: It can be anything. It is a unique condition
                                bordered by the webdriver expected_conditions options

       """

        chosen_expected_condition = None

        if expected_condition is not None:
            chosen_expected_condition = expected_condition
        elif webelement_is_visible:
            chosen_expected_condition = expected_conditions.visibility_of_element_located((By.XPATH, xpath))
        elif webelement_is_clickable:
            chosen_expected_condition = expected_conditions.element_to_be_clickable((By.XPATH, xpath))
        elif alert is not None:
            xpath = MiUsIn.__create_alert_xpath(alert)
            chosen_expected_condition = expected_conditions.visibility_of_element_located((By.XPATH, xpath))

        if not until_not:
            WebDriverWait(driver=MiUsIn.driver, timeout=timeout_in_seconds).until(chosen_expected_condition)

        elif until_not:
            WebDriverWait(driver=MiUsIn.driver, timeout=timeout_in_seconds).until_not(chosen_expected_condition)

    def casebreak_alarm(self, major_bug: bool):
        if major_bug:
            self.casebreak = True

    @__testcase_logging
    @collect_data(mimic_type=Values.CLICK.value)
    def click(self, xpath: str = None, webelement_name: str = "", major_bug: bool = False,
              step_positivity: str = Values.POSITIVE.value,
              step_description: str = "", find_by_label: str = None) -> CaseStep | None:
        """
        Mimic a mouse click event as a case-step.

        Arguments:
            xpath: a clickable webelement's field_xpath
            webelement_name: optional. You can name the webelement. This parameter is part of the step-log
            minor_bug: if it true and the case-step failed, the testcase will be continued.
                If false and the case-step failed, the testcase following steps will be skipped.
            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful
            step_description: optional. You can write a description, what about this step.

        examples:

        """
        if find_by_label is not None:
            xpath = f"//*[text()='{find_by_label}']"
        clickable_webelement = MiUsIn.driver.find_element(by=By.XPATH, value=xpath)
        clickable_webelement.click()

    @__testcase_logging
    @collect_data(mimic_type=Values.DOUBLE_CICK.value)
    def double_click(self, xpath: str = None, webelement_name: str = "", major_bug: bool = False,
                     step_positivity: str = Values.POSITIVE.value,
                     step_description: str = "", find_by_label: str = None) -> CaseStep | None:
        """
        Mimic a mouse click event as a case-step.

        Arguments:
            xpath: a clickable webelement's field_xpath
            webelement_name: optional. You can name the webelement. This parameter is part of the step-log
            minor_bug: if it true and the case-step failed, the testcase will be continued.
                If false and the case-step failed, the testcase following steps will be skipped.
            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful
            step_description: optional. You can write a description, what about this step.

        examples:

        """

        if find_by_label is not None:
            xpath = f"//*[text()='{find_by_label}']"
        clickable_webelement = MiUsIn.driver.find_element(by=By.XPATH, value=xpath)
        MiUsIn.action_driver.double_click(on_element=clickable_webelement).perform()

    @__testcase_logging
    @collect_data(mimic_type=Values.SEND_KEYS.value)
    def fill_field(self, field_xpath: str, data: str, webelement_name: str = "", major_bug: bool = False,
                   step_positivity: str = Values.POSITIVE.value,
                   step_description: str = "") -> CaseStep | None:
        """
        Mimic the event of filling a field on a webpage.

        Arguments:
            field_xpath: The field webelement's xpath
            webelement_name: optional. You can name the webelement. This parameter is part of the step-log
            minor_bug: if it true and the case-step failed, the testcase will be continued.
                   If false and the case-step failed, the testcase following steps will be skipped.
            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful
            step_description: optional. You can write a description, what about this step.
            data: the string you want to put into the specified field.
        """
        field = MiUsIn.driver.find_element(by=By.XPATH, value=field_xpath)
        field.clear()
        field.send_keys(data)

    @__testcase_logging
    @collect_data(mimic_type=Values.SEND_KEYS.value)
    def fill_field_by_param(self, param: str, find_field_xpath: str = None, data="", webelement_name: str = "empty",
                            major_bug: bool = False,
                            step_positivity: str = Values.POSITIVE.value,
                            step_description: str = "") -> CaseStep | None:
        """
        Mimic the event of filling a field on a webpage.

        Arguments:
            field_xpath: The field webelement's xpath
            webelement_name: optional. You can name the webelement. This parameter is part of the step-log
            minor_bug: if it true and the case-step failed, the testcase will be continued.
                   If false and the case-step failed, the testcase following steps will be skipped.
            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful
            step_description: optional. You can write a description, what about this step.
            data: the string you want to put into the specified field.
        """
        created_field_xpath: str = self.__create_field_xpath(param)
        if find_field_xpath is not None:
            created_field_xpath = find_field_xpath.replace(InnerStatics.PARAM.value, param)
        elif created_field_xpath == "" and find_field_xpath is None:
            raise TypeError("None value in field: 'field_xpath'")
        field = MiUsIn.driver.find_element(by=By.XPATH, value=created_field_xpath)
        field.clear()
        field.send_keys(data)
        xpath = created_field_xpath

    def __create_field_xpath(self, param: str):
        if self.local_field_xpath is not None:
            field_xpaths = [field_findig_method.replace(InnerStatics.PARAM.value, param) for field_findig_method in
                            self.local_field_xpath]
            return "|".join(field_xpaths)

        elif MiUsIn.global_field_xpath is not None:
            field_xpaths = [field_findig_method.replace(InnerStatics.PARAM.value, param) for field_findig_method in
                            MiUsIn.global_field_xpath]
            return "|".join(field_xpaths)
        else:
            return ""

    def __add_default_field_xpaths(self, label: str, xpaths: list) -> None:
        """
        extend the received list with the default field xpaths.
        These xpaths containing the currently searched field's param

        Arguments:
            label: the currently searched field's param
            xpaths: a list of field_xpaths

        Examples:

        """
        default_filed_xpaths: [str] = [f"//*[@*='{label}']"]
        xpaths.extend(default_filed_xpaths)

    @__testcase_logging
    @collect_data(Values.COMBOBOX.value)
    def select_combobox_element(self, input_field_xpath: str, dropdown_element_text: str = "",
                                webelement_name: str = "",
                                major_bug: bool = False,
                                step_positivity: str = Values.POSITIVE.value,
                                step_description: str = "") -> CaseStep | None:

        self.fill_field(field_xpath=input_field_xpath, data=dropdown_element_text,
                        webelement_name=webelement_name,
                        major_bug=major_bug,
                        step_positivity=step_positivity,
                        step_description=step_description)

        list_element = self.__find_combobox_list_element(input_field_xpath, dropdown_element_text)
        list_element.click()

    @__testcase_logging
    @collect_data(mimic_type=Values.COMBOBOX.value)
    def select_combobox_element_by_param(self, param: str, input_field_xpath: str = None,
                                         dropdown_element_text: str = "",
                                         webelement_name: str = "",
                                         major_bug: bool = False,
                                         step_positivity: str = Values.POSITIVE.value,
                                         step_description: str = "") -> CaseStep | None:

        self.fill_field_by_param(find_field_xpath=input_field_xpath, data=dropdown_element_text,
                                 webelement_name=webelement_name,
                                 major_bug=major_bug,
                                 step_positivity=step_positivity,
                                 step_description=step_description, param=param)

        if input_field_xpath is None:
            input_field_xpath = self.__create_field_xpath(param)

        list_element = self.__find_combobox_list_element(input_field_xpath, dropdown_element_text)
        list_element.click()

    def __find_combobox_list_element(self, input_field_xpath: str, dropdown_element_text: str):
        if self.combobox_parent_finding_method_by_xpath is not None:
            parent_webelement_xpaths: list = self.combobox_parent_finding_method_by_xpath
        elif MiUsIn.global_combobox_parent_finding_method_by_xpath is not None:
            parent_webelement_xpaths: list = MiUsIn.global_combobox_parent_finding_method_by_xpath

        parent_webelement = MiUsIn.driver.find_element(by=By.XPATH,
                                                       value=self.__combobox_parent_xpath(input_field_xpath,
                                                                                          parent_webelement_xpaths))
        list_element = parent_webelement.find_element(by=By.XPATH,
                                                      value=InnerStatics.IN_PARENT_FIND_LABEL_BY_PARAM.value.replace(
                                                          InnerStatics.PARAM.value, dropdown_element_text))

        return list_element

    def __get_input_field_xpath(self, find_by_label: str):
        return f"//*[text()='{find_by_label}']{self.__create_field_xpath()}"

    def __combobox_parent_xpath(self, input_field_xpath: str, parent_webelement_xpaths: list):
        field_list: list = input_field_xpath.split("|")
        all_parent_xpaths: list = []
        for field_xpath in field_list:
            parent_webelement_xpaths = tuple(
                f"{field_xpath}{find_parent_parameter}" for find_parent_parameter in parent_webelement_xpaths)

            all_parent_xpaths.append("|".join(parent_webelement_xpaths))
        return "|".join(all_parent_xpaths)

    @Utimer.bomb(timeout_in_seconds=bomb_timeout)
    def jump_to_recent_window_base(self) -> bool:
        if self.casebreak:
            return

        driver = MiUsIn.driver
        current_window_handle = driver.current_window_handle
        recent_window = driver.window_handles[-1]
        if current_window_handle != recent_window:
            driver.switch_to.window(recent_window)

            return True
        return False

    def jump_to_recent_window(self, timeout: float = 1) -> None:
        if self.casebreak:
            return

        if timeout != 1:
            MiUsIn.set_bomb_timeout(timeout)
        try:
            self.jump_to_recent_window_base()
            print("switched to the recent window")
        except TimeoutError:
            print("failed to switch to the recent windows")

        if timeout != 1:
            MiUsIn.set_bomb_timeout(1)

    @__testcase_logging
    @collect_data(mimic_type=Values.PRESS_KEY.value)
    def press_key(self, key_to_press: str, webelement_name: str = "", major_bug: bool = False,
                  step_positivity: str = Values.POSITIVE.value, step_description: str = "") -> CaseStep | None:
        """
        Mimic a mouse click event as a case-step.

        Arguments:
            xpath: a clickable webelement's field_xpath
            webelement_name: optional. You can name the webelement. This parameter is part of the step-log
            minor_bug: if it true and the case-step failed, the testcase will be continued.
                If false and the case-step failed, the testcase following steps will be skipped.
            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful
            step_description: optional. You can write a description, what about this step.

        examples:

        """
        match key_to_press:
            case "enter":
                MiUsIn.action_driver.send_keys(Keys.ENTER).perform()
                action_type = Values.PRESS_ENTER.value
            case "tab":
                MiUsIn.action_driver.send_keys(Keys.TAB).perform()
                action_type = Values.PRESS_TAB.value
            case "esc":
                MiUsIn.action_driver.send_keys(Keys.ESCAPE).perform()
                action_type = Values.PRESS_ESC.value
            case _:
                raise KeyError(f"Unknown key: '{key_to_press}'")

    @staticmethod
    def get_css_attribute(xpath: str, attribute: str) -> str:
        """
        return a selected attribute of a webelement

        Arguments:
            xpath: the webelement's xpath
            attribute: teh attribute of the webelement you want to get
        """
        atr_value = None

        webelement = MiUsIn.driver.find_element(By.XPATH, value=xpath)
        atr_value = webelement.value_of_css_property(attribute)

        return atr_value

    @__testcase_logging
    @collect_data(mimic_type=Values.CHECK_STYLE.value)
    def match_style(self, xpath: str, attribute: str, expected_value: str, webelement_name: str = "",
                    major_bug: bool = False,
                    step_positivity: str = Values.POSITIVE.value, step_description: str = "") -> object:
        """

        """
        real_value: str = MiUsIn.get_css_attribute(xpath=xpath, attribute=attribute)
        if real_value != expected_value:
            raise ValueError

    def check_style(self, xpath: str, attribute: str, expected_value: str):
        if self.casebreak:
            return None
        try:
            real_value: str = MiUsIn.get_css_attribute(xpath=xpath, attribute=attribute)
            if real_value != expected_value:
                raise ValueError
        except (exceptions.WebDriverException, ValueError):
            return False

        if real_value == expected_value:
            return True

    @staticmethod
    def get_text(xpath: str = None, by_label: str = None):

        if by_label is not None:
            xpath = f"//*[text()='{by_label}']"

        text: str = MiUsIn.driver.find_element(By.XPATH, value=xpath).text
        if text is None:
            text = MiUsIn.driver.find_element(By.XPATH, value=xpath).get_property("value")

        return text

    def check_text(self, expected_value: str, xpath: str = None, by_label: str = None):
        if self.casebreak:
            return None
        try:
            real_value = MiUsIn.get_text(xpath=xpath, by_label=by_label)
            if real_value != expected_value:
                raise ValueError
        except (exceptions.WebDriverException, ValueError):
            return False

        return True

    @__testcase_logging
    @collect_data(mimic_type=Values.CHECK_TEXT.value)
    def match_text(self, expected_value: str, xpath: str = None, webelement_name: str = "", major_bug: bool = False,
                   step_positivity: str = Values.POSITIVE.value, step_description: str = "",
                   by_label: str = None) -> object:

        real_value: str = MiUsIn.get_text(xpath=xpath, by_label=by_label)
        if real_value != expected_value:
            raise ValueError

# TODO complite the documentation in sphinx style
# TODO extend the logging decorator with logging to txt and logging to only the console
# TODO extend the logging docirator with optional charts of the result_informations
