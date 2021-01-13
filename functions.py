def compDistance(coord1,coord2):
    return abs(coord2[0] - coord1[0]) + abs(coord2[1] - coord1[1])

def updateDict(dict_,key,value, ftype=None):
    if (key in dict_):
        if (ftype is "inp" and isinstance(value, list)):
            dict_[key] = dict_[key] + value
        else:
            dict_[key].append(value)
    else:
        if isinstance(value, list):
            dict_.update({key : value})
        else:
            dict_.update({key : [value]})

def printDict(dictry):
    for key, value in dictry.items():
        print(key, ' ---> ', value)