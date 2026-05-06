import unittest

from lib.python.utils import get_all_subclasses


class UnitTest_get_all_subclasses(unittest.TestCase):
    class Foo(object): pass

    class Bar(Foo): pass

    class Baz(Foo): pass

    class Bing(Bar): pass

    def test(self):
        subclass_name_list = []
        for sub_cls in get_all_subclasses(UnitTest_get_all_subclasses.Foo):
            subclass_name_list.append(sub_cls.__name__)

        self.assertEqual(subclass_name_list, ["Bing", "Baz", "Bar"])
