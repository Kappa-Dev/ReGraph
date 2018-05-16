def number_of_DbHits(profile, nb=0):
    # print(profile[4])
    nb += profile[4]
    children = profile[3]
    if len(children) == 0:
        return nb
    else:
        for child in children:
            return number_of_DbHits(child, nb)
