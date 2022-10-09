from enum import Enum


class databases(Enum):
    VENY = "veny"
    MEDCENT = "medcent"


class testcase_fields(Enum):
    TULAJDONSAGOK = "tulajdonsagok"
    ADATOK = "adatok"
    ID = "_id"
    POZITIVITAS = "pozitivitas"
    TERULET = "terulet"
    POSITIVITY_POSITIVE = "pozitív"
    POSITIVITY_NEGATIVE = "negatív"
