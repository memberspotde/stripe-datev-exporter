

list1 = {"a": 1, "b": 2, "c": 3}
list2 = list1
list3 = {**list1}

# list2["d"] = 4

print(list1)
print(list2)
print(list3)
print(list1 == list3)
