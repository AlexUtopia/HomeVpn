

def get_all_subclasses(cls):
    result = cls.__subclasses__().copy()
    for sub_cls in cls.__subclasses__():
        for sub_sub_cls in get_all_subclasses(sub_cls):
            if not sub_sub_cls in result:
                result.append(sub_sub_cls)
    result.reverse()
    return result
