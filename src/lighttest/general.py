def boolsum(booleans):
    formated_bools = booleans.values()
    only_true = sum(formated_bools) == len(formated_bools)
    return only_true
