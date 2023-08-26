# encoding=utf-8


def new_from_dict(class_, dict_value):
    obj = class_()
    obj.update(dict_value)
    return obj
