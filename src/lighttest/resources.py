from enum import Enum


class Security(Enum):
    get_prelogin_token = 'security-global/auth/get-prelogin-token'
    get_true_login_token = 'security-global/auth/get-truelogin-token/servicepoint/'
    get_permission = "security-global"


class PatientController(Enum):
    find_by_genkod = "patient-admission/patient/find-by-genkod/"  # param: genkod
    patient_search = "patient-admission/patient/patient-search"
    patient_save = "patient-admission/patient/save"
    patient_update = "patient-admission/patient/save/"  # param: genkod
