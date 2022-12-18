import inspect
from dataclasses import dataclass
from enum import Enum, unique
from functools import wraps

from lighttest.test_summary import ErrorLog
from lighttest_supplies import date_methods
from lighttest_supplies.timers import Utimer

from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common import exceptions, WebDriverException
from lighttest_supplies.general import create_logging_structure, create_logging_directory
import lighttest.test_summary as ts
from lighttest.datacollections import TestTypes, ResultTypes, CaseStep
from faker import Faker
from lighttest.datacollections import CaseStep
from lighttest.light_exceptions import NoneAction

fake = Faker()


def collect_data(mimic_fun):
    signature = inspect.signature(obj=mimic_fun).bind_partial()
    signature.apply_defaults()

    @wraps(mimic_fun)
    def collecting_data(*args, step_positivity: str = Values.POSITIVE.value, major_bug: bool = False,
                        step_description: str = "", skip: bool = False, data: str = "", xpath: str = "",
                        identifier: str = "", **kwargs):
        completed_kwargs: dict = dict(signature.arguments)
        completed_kwargs.update(kwargs)

        case_object: MiUsIn = args[0]
        if case_object.casebreak or skip:
            return None

        step_failed: bool = False
        new_error: str = ""
        try:
            mimic_fun(*args, **kwargs)

        except NoneAction:
            return None
        except (exceptions.WebDriverException, ValueError) as error:
            new_error = str(error)
            step_failed = True

        step_datas = CaseStep(step_description=step_description, step_positivity=step_positivity, fatal_bug=major_bug,
                              identifier=identifier, xpath=xpath, step_failed=step_failed, step_type=mimic_fun.__name__,
                              data=data, step_error=new_error)
        return step_datas

    return collecting_data


def testcase_logging(testcase_step) -> None:
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
                not step_datas.step_failed and step_datas.step_positivity == Values.NEGATIVE.value):
            case_object.error_count += 1
            case_object.casebreak_alarm(major_bug=step_datas.fatal_bug)
            MiUsIn._take_a_screenshot(case_object)

            case_object.error_in_case = True
            ts.new_testresult(test_type=TestTypes.FRONTEND.value, result=ResultTypes.FAILED.value,
                              required_time=0, name=case_object.case_name)
        else:
            ts.new_testresult(test_type=TestTypes.FRONTEND.value, result=ResultTypes.SUCCESSFUL.value,
                              required_time=0, name=case_object.case_name)

        return step_datas

    return asert


class CaseManagement:
    def __init__(self, case_name: str, screenshots_container_directory: str = "C:\Screenshots"):
        self.local_click_xpaths: set[str] = {}
        self.local_field_xpaths: set[str] = {}
        self.teststep_count = 0
        self.testcase_failed: bool = False
        self.error_count: int = 0
        self.screenshots_container_directory: str = screenshots_container_directory
        self.case_name = case_name
        self.steps_of_reproduction: dict = {}
        self.casebreak = False
        self.combobox_parent_finding_method_by_xpaths: set[str] = {}
        self.error_in_case = False

    def close_case(self):
        """
        This method must to be on the end of every testcase. it send the collected
        frontend_errors - and the steps led to the error - into the log.
        """
        if self.error_in_case:
            ErrorLog.add_frontend_error({self.case_name: self.steps_of_reproduction})

        del self

    def set_combobox_parent_finding_method_by_xpath(self, *xpaths: str):
        """
        @param: global_combobox_parent_finding_method_by_xpath the value of this param determinate
                how to find combobox parent webelement
        """
        self.combobox_parent_finding_method_by_xpaths = set(xpaths)

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
        MiUsIn.global_field_xpaths = set(xpaths)

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
        self.local_field_xpaths = set(xpaths)

    @staticmethod
    def set_global_click_xpaths(*xpaths: str):
        """
        placeholder

        Arguments:
            *xpaths: the value of this param determinate
                    how to find clickable webelements in global.

        Format:
            the paramter in the xpath need to be the following: __param__

        Example:
            set_case_field_xpath("//*[text()='__param__']/parent::*/descendant::fa-icon",
            "//*[text()='__param__']/parent::*/descendant::button")

        """
        MiUsIn.global_click_xpaths = set(xpaths)

    def set_case_click_xpaths(self, *xpaths: str):
        """
        placeholder

        Arguments:
            *xpaths: the value of this param determinate
                    how to find clickable webelements in the level of testcase.

        Format:
            the paramter in the xpath need to be the following: __param__

        Example:
            set_case_field_xpath("//*[text()='__param__']/parent::*/descendant::fa-icon",
            "//*[text()='__param__']/parent::*/descendant::button")

        """
        self.local_click_xpaths = set(xpaths)

    @staticmethod
    def set_global_combobox_parent_finding_method_by_xpath(*xpaths: str):
        '''
        field_xpath : it set the global_combobox_parent_finding_method_by_xpath class variable
        '''
        MiUsIn.global_combobox_parent_finding_method_by_xpaths = set(xpaths)


@unique
class Values(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@unique
class InnerStatics(Enum):
    PARAM: str = "__param__"
    FIND_LABEL_BY_PARAM: str = "//*[text()='__param__']"
    IN_PARENT_FIND_LABEL_BY_PARAM: str = ".//*[contains(text(), '__param__')]"


@dataclass(kw_only=True)
class TestStep:
    case_object: CaseStep
    xpath: str
    step_data: str = ""


class ClickMethods:
    global_click_xpaths: set[str] = {}

    def __init__(self):
        pass

    @testcase_logging
    @collect_data
    def click(self, xpath: str = None, identifier: str = None, contains: bool = True) -> CaseStep | None:
        """
        Mimic a mouse click event as a case-step.

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            xpath: a clickable webelement's xpath expression
            identifier: a visible static text(label) on the website
            contains: if true and  the identifier field is used,
                than it accept any webelement which is contains the identifier

        examples:

        """
        match (identifier is not None, contains):
            case (True, False):
                xpath = f"//*[text()='{identifier}']"
            case (True, True):
                xpath = f"//*[contains(text(),'{identifier}')]"
        clickable_webelement = MiUsIn.driver.find_element(by=By.XPATH, value=xpath)
        clickable_webelement.click()

    @testcase_logging
    @collect_data
    def click_by_param(self, identifier: str, xpath: str = None) -> CaseStep | None:
        """
        Mimic a mouse click.

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.


        Arguments:
            xpath: a clickable webelement's parametric xpath expression
            identifier: the paramteric indetifier in the click_xpath expression


        examples:

        """
        created_click_xpath: str = self._create_click_xpath(identifier)
        if xpath is not None:
            created_click_xpath = xpath.replace(InnerStatics.PARAM.value, identifier)
        elif created_click_xpath == "" and xpath is None:
            raise TypeError("None value in argument: 'parametric_xpath'")
        clickable_webelement = MiUsIn.driver.find_element(by=By.XPATH, value=created_click_xpath)
        clickable_webelement.click()

    @testcase_logging
    @collect_data
    def double_click(self, xpath: str = None, identifier: str = None) -> CaseStep | None:
        """
        Mimic a mouse click event as a case-step.

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            xpath: a clickable webelement's xpath
            identifier: a visible static text(label) on the website


        examples:

        """

        if identifier is not None:
            xpath = f"//*[text()='{identifier}']"
        clickable_webelement = MiUsIn.driver.find_element(by=By.XPATH, value=xpath)
        MiUsIn.action_driver.double_click(on_element=clickable_webelement).perform()

    def _create_click_xpath(self, param: str):
        if len(self.local_click_xpaths) != 0:
            field_xpaths: set[str] = set(
                parametric_xpath.replace(InnerStatics.PARAM.value, param) for parametric_xpath in
                self.local_click_xpaths)
            return "|".join(field_xpaths)

        elif len(MiUsIn.global_click_xpaths) != 0:
            field_xpaths: set[str] = set(
                parametric_xpath.replace(InnerStatics.PARAM.value, param) for parametric_xpath in
                MiUsIn.global_click_xpaths)
            return "|".join(field_xpaths)

        else:
            return ""


class FieldMethods:
    global_field_xpaths: set[str] = {}

    def __init__(self):
        pass

    @testcase_logging
    @collect_data
    def fill_field(self, xpath: str, data: str) -> CaseStep | None:
        """
        Mimic the event of filling a field on a webpage.

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            xpath: The field webelement's xpath
            data: the string you want to put into the specified field.
        """

        if data is None:
            raise NoneAction
        field = MiUsIn.driver.find_element(by=By.XPATH, value=xpath)
        field.click()
        field.clear()
        field.send_keys(data)

    @testcase_logging
    @collect_data
    def fill_field_by_param(self, identifier: str, xpath: str = None, data="") -> CaseStep | None:
        """
        Mimic the event of filling a field on a webpage.

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            xpath: The field webelement's parametric xpath
            data: the string you want to put into the specified field.
            identifier: the paramteric indetifier in the field_xpath expression
        """
        if data is None:
            raise NoneAction
        created_field_xpath: str = self._create_field_xpath(identifier)
        if xpath is not None:
            created_field_xpath = xpath.replace(InnerStatics.PARAM.value, identifier)
        elif created_field_xpath == "" and xpath is None:
            raise TypeError("None value in field: 'field_xpath'")
        field = MiUsIn.driver.find_element(by=By.XPATH, value=created_field_xpath)
        field.click()
        field.clear()
        field.send_keys(data)

    def fill_form(self, **kwargs):
        """
        this function is useful when want to comletea form with many input fields.
        Just add kw names as fieldnames and kw values as input datas.
        if the field's name contains spaces, replace those with '_'

        Example:
            fill_form(Name='John Doe', Date_of_birth='1992.01.20')
        """
        for key, value in kwargs.items():
            self.fill_field_by_param(identifier=str(key).replace("_", " "), data=value)
        return kwargs

    def _create_field_xpath(self, param: str):
        if len(self.local_field_xpaths) != 0:
            field_xpaths = [field_findig_method.replace(InnerStatics.PARAM.value, param) for field_findig_method in
                            self.local_field_xpaths]
            return "|".join(field_xpaths)

        elif len(MiUsIn.global_field_xpaths) != 0:
            field_xpaths = [field_findig_method.replace(InnerStatics.PARAM.value, param) for field_findig_method in
                            MiUsIn.global_field_xpaths]
            return "|".join(field_xpaths)
        else:
            return ""


class ValueValidation(FieldMethods):
    global_webalert_xpath: str = None

    def __init__(self):
        pass

    @staticmethod
    def _create_alert_xpath(alert_message: str):
        if MiUsIn.global_webalert_xpath is None:
            created_alert_xpath = f"//*[contains(text(),'{alert_message}')]"
        else:
            created_alert_xpath = MiUsIn.global_webalert_xpath

        return created_alert_xpath

    @testcase_logging
    @collect_data
    def expected_condition(self, timeout_in_seconds: float, expected_condition: expected_conditions = None,
                           until_not: bool = False, webelement_is_visible=False, webelement_is_clickable=False,
                           alert: str = None, xpath=None):
        """

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

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
            xpath = MiUsIn._create_alert_xpath(alert)
            chosen_expected_condition = expected_conditions.visibility_of_element_located((By.XPATH, xpath))

        if not until_not:
            WebDriverWait(driver=MiUsIn.driver, timeout=timeout_in_seconds).until(chosen_expected_condition)

        elif until_not:
            WebDriverWait(driver=MiUsIn.driver, timeout=timeout_in_seconds).until_not(chosen_expected_condition)

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

    @testcase_logging
    @collect_data
    def match_style(self, xpath: str, identifier: str, data: str) -> object:
        """
        check a style param like color, font type, style, etc.

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            xpath: the visible website element's xpath expresion
            data: the expected style parameter's value
            identifier: the style attribute's name in the css
        """
        actual_value: str = MiUsIn.get_css_attribute(xpath=xpath, attribute=identifier)
        if actual_value != data:
            raise ValueError({"Expected_value": data, "actual_value": actual_value})

    def check_style(self, xpath: str, attribute: str, expected_value: str):
        if self.casebreak:
            return None
        try:
            actual_value: str = MiUsIn.get_css_attribute(xpath=xpath, attribute=attribute)
            if actual_value != expected_value:
                raise ValueError
        except (exceptions.WebDriverException, ValueError):
            return False

        if actual_value == expected_value:
            return True

    @staticmethod
    def get_static_text(xpath: str = None, by_label: str = None):

        if by_label is not None:
            xpath = f"//*[text()='{by_label}']"

        text: str = MiUsIn.driver.find_element(By.XPATH, value=xpath).text

        return text

    @staticmethod
    def get_field_text(xpath: str = None, by_label: str = None):

        if by_label is not None:
            xpath = f"//*[text()='{by_label}']"

        text: str = MiUsIn.driver.find_element(By.XPATH, value=xpath).get_property("value")

        return text

    def check_text(self, expected_value: str, xpath: str = None, by_label: str = None):
        if self.casebreak:
            return None
        try:
            actual_value = MiUsIn.get_static_text(xpath=xpath, by_label=by_label)
            if actual_value != expected_value:
                raise ValueError
        except (exceptions.WebDriverException, ValueError):
            return False

        return True

    @testcase_logging
    @collect_data
    def match_text(self, data: str, xpath: str = None, identifier: str = None) -> object:
        """
        check a style param like color, font type, style, etc.

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            xpath: a label or an inputfield's xpath expresion
            data: the expected text value
            identifier: if it is a static text (a label) can use only the label instead of the full xpath expression
        """
        actual_value: str = MiUsIn.get_static_text(xpath=xpath, by_label=identifier)
        if data is None:
            data = ""
        if actual_value != data:
            raise ValueError({"Expected_value": data, "actual_value": actual_value})

    @testcase_logging
    @collect_data
    def parametric_field_value_match(self, data: str, identifier: str, xpath: str = None):
        """

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        """
        created_field_xpath: str = self._create_field_xpath(identifier)
        if xpath is not None:
            created_field_xpath = xpath.replace(InnerStatics.PARAM.value, identifier)
        elif created_field_xpath == "" and xpath is None:
            raise TypeError("None value in field: 'field_xpath'")
        actual_value: str = MiUsIn.get_field_text(xpath=created_field_xpath, by_label=None)
        if data is None:
            data = ""
        if actual_value != data:
            raise ValueError({"Expected_value": data, "actual_value": actual_value})

    def match_form_field_values(self, **kwargs):
        """
        this function is useful when want to check a full form with loaded inputfield values.
        Just add kw names as fieldnames and kw values as expexted values.
        if the field's name contains spaces, replace those with '_'

        Example:
            match_form_field_values(Name='John Doe', Date_of_birth='1992.01.20')
        """
        for key, value in kwargs.items():
            self.parametric_field_value_match(identifier=str(key).replace("_", " "), data=value)

    @testcase_logging
    @collect_data
    def wait_till_website_ready(self, timeout=10, identifier: str = "Not specified"):
        @Utimer.bomb(timeout_in_seconds=timeout)
        def get_ready_state():
            state: bool = self.driver.execute_script("return document.readyState") == "complete"
            return state

        try:
            get_ready_state()
        except TimeoutError:
            raise WebDriverException("Website not fully loaded within the specified timeout period")


class DropDownMethods:
    global_combobox_parent_finding_method_by_xpaths: set[str] = {}

    def _find_combobox_list_element(self, input_field_xpath: str, dropdown_element_text: str):
        if len(self.combobox_parent_finding_method_by_xpaths) > 0:
            parent_webelement_xpaths: set = self.combobox_parent_finding_method_by_xpaths
        elif len(MiUsIn.global_combobox_parent_finding_method_by_xpaths) > 0:
            parent_webelement_xpaths: set = MiUsIn.global_combobox_parent_finding_method_by_xpaths

        parent_webelement = MiUsIn.driver.find_element(by=By.XPATH,
                                                       value=self._combobox_parent_xpath(input_field_xpath,
                                                                                         parent_webelement_xpaths))
        list_element = parent_webelement.find_element(by=By.XPATH,
                                                      value=InnerStatics.IN_PARENT_FIND_LABEL_BY_PARAM.value.replace(
                                                          InnerStatics.PARAM.value, dropdown_element_text))

        return list_element

    @testcase_logging
    @collect_data
    def select_combobox_element(self, xpath: str, data: str = "") -> CaseStep | None:
        """
        click on a combobox elements.


        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            xpath: the combobox's input-field xpath expression
            data: an element in the dropdown you want to click
        """

        self.fill_field(xpath=xpath, data=data)

        list_element = self._find_combobox_list_element(xpath, data)
        list_element.click()

    @testcase_logging
    @collect_data
    def select_combobox_element_by_param(self, identifier: str, xpath: str = None,
                                         data: str = "") -> CaseStep | None:
        """
        use the combobox_parent_finding_method to click on a combobox elements

        Special Keywords:
            major_bug: if true and this case-step fail, the remain case-steps will be skipped

            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful

            step_description: optional. You can write a description, what about this step.

            skip: if true, the method return without any action.

        Arguments:
            data: an element in the dropdown you want to click
            identifier: the paramteric indetifier in the field_xpath expression
            xpath: the paramteric parametric representation of the input-field xpath.
                    It can use only with the identifier argument.
        """

        self.fill_field_by_param(xpath=xpath, data=data, identifier=identifier)

        if xpath is None:
            xpath = self._create_field_xpath(identifier)

        list_element = self._find_combobox_list_element(xpath, data)
        list_element.click()

    def _combobox_parent_xpath(self, input_field_xpath: str, parent_webelement_xpaths: list):
        field_list: list = input_field_xpath.split("|")
        all_parent_xpaths: list = []
        for field_xpath in field_list:
            parent_webelement_xpaths = tuple(
                f"{field_xpath}{find_parent_parameter}" for find_parent_parameter in parent_webelement_xpaths)

            all_parent_xpaths.append("|".join(parent_webelement_xpaths))
        return "|".join(all_parent_xpaths)


class NavigationMethods:
    bomb_timeout: float = 1

    def __init__(self):
        pass

    @staticmethod
    def jump_webpage(url: str) -> None:
        """
        the browser navigate to the desired url.
        """
        MiUsIn.driver.get(url)

    @staticmethod
    def set_bomb_timeout(timeout: float) -> None:
        """
        Set the timeout value for the bomb decorator.
        """
        MiUsIn.bomb_timeout = timeout

    @Utimer.bomb(timeout_in_seconds=bomb_timeout)
    def jump_to_recent_window_base(self) -> bool:
        if self.casebreak:
            return

        current_window_handle = MiUsIn.driver.current_window_handle
        recent_window = MiUsIn.driver.window_handles[-1]
        if current_window_handle != recent_window:
            MiUsIn.driver.switch_to.window(recent_window)

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


class DriverManagement:
    driver: webdriver.Chrome = None

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


class MiUsIn(CaseManagement, ValueValidation, ClickMethods, DropDownMethods, NavigationMethods, DriverManagement):
    """
    MiUsIn stand for Mimic User interactions.
    Variables:
        driver: this is the google chrome's webdriver. Every browser interaction use this particular driver.
        bomb_timeout: Its defining how much time need the @bomb decorator to raise timeout error
        global_combobox_parent_finding_method_by_xpath: the value of this param determinate
                how to find combobox parent webelement
    """
    action_driver: ActionChains = None

    def __init__(self, case_name: str, fullsize_windows=True,
                 screenshots_container_directory: str = "C:\Screenshots"):
        """
        placeholder

        Arguments:
            fullsize_windows: If true, the browser's windows will b full-sized
            screenshots_container_directory: If during a testcase it find an error
                    the screenshot taken of the error will be stored and catalogised in that directory
        """
        super().__init__(case_name, screenshots_container_directory)

        if MiUsIn.driver is None:
            MiUsIn.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            MiUsIn.action_driver = ActionChains(MiUsIn.driver)
        MiUsIn.driver.implicitly_wait(time_to_wait=5)

        if fullsize_windows:
            MiUsIn.driver.maximize_window()

    def __del__(self):
        pass

    def stack_dict_item(self, updater: dict, current_dict: dict):

        if list(updater.keys())[0] not in list(current_dict.keys()):
            current_dict.update(updater)
        else:
            current_dict[list(updater.keys())[0]] += updater[list(updater.keys())[0]]

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

    def casebreak_alarm(self, major_bug: bool):
        if major_bug:
            self.casebreak = True

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

    def _get_input_field_xpath(self, find_by_label: str):
        return f"//*[text()='{find_by_label}']{self._create_field_xpath()}"

    @testcase_logging
    @collect_data
    def press_key(self, identifier: str) -> CaseStep | None:
        """
        Mimic a key peress.

        Arguments:
            identifier: a key-code whics is identifie a key
            major_bug: if true and this case-step fail, the remain case-steps will be skipped
            step_positivity: determine what is the expected outcome of the step. If positive, it must be successful
            step_description: optional. You can write a description, what about this step.

        Identifiers:
            ENTER: 'enter',
            TAB: 'tab',
            ESCAPE: 'esc'

        Examples:

        """
        match identifier:
            case "enter":
                MiUsIn.action_driver.send_keys(Keys.ENTER).perform()
            case "tab":
                MiUsIn.action_driver.send_keys(Keys.TAB).perform()
            case "esc":
                MiUsIn.action_driver.send_keys(Keys.ESCAPE).perform()
            case _:
                raise KeyError(f"Unknown key: '{identifier}'")
