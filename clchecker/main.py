from clchecker.visitor import Visitor
from clchecker.checker import CLchecker
from clchecker.store import Store

store = Store(db='clchecker')
clchecker = CLchecker(store)
visitor = Visitor(clchecker)

