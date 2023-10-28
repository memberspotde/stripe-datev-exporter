

class Abc():

  def __init__(self):
    self.a = 1
    self.b = 2

  def add(self):
    return self.a + self.b


abc = Abc()

print("A", abc.a, abc["a"])
