import unittest

from ..linux_kernel_version import LinuxKernelVersion


class UnitTest_LinuxKernelVersion(unittest.TestCase):
    class LinuxKernelVersionTest(LinuxKernelVersion):
        pass

    class UnknownClass:
        pass

    def test(self):
        ref_table = [
            (LinuxKernelVersion, "",
             {"is_exception": True}),
            (LinuxKernelVersion, "Hello world",
             {"is_exception": True}),
            (LinuxKernelVersion, 17,
             {"is_exception": True}),
            (LinuxKernelVersion, UnitTest_LinuxKernelVersion.UnknownClass,
             {"is_exception": True}),
            (LinuxKernelVersion, "5",
             {"is_exception": True}),
            (LinuxKernelVersion, "5.",
             {"is_exception": True}),
            (LinuxKernelVersion, "5.0-",
             {"is_exception": True}),
            (LinuxKernelVersion, "6.14.0-1-liquorix-amd64",
             {"expected": "6.14-1-liquorix-amd64", "is_exception": False, "is_liquorix": True, "is_rc": False,
              "expected_dict": {"major": 6, "minor": 14, "revision": 0, "release_candidate": 0, "patch": 1,
                                "variant": "liquorix-amd64"}}),
            (LinuxKernelVersion, "/boot/vmlinuz-5.15.0-91-generic",
             {"expected": "5.15-91-generic", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 5, "minor": 15, "revision": 0, "release_candidate": 0, "patch": 91,
                                "variant": "generic"}}),
            (LinuxKernelVersion, "6.14-rc15",
             {"expected": "6.14-rc15", "is_exception": False, "is_liquorix": False, "is_rc": True,
              "expected_dict": {"major": 6, "minor": 14, "revision": 0, "release_candidate": 15, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, "6.14.9999-rc15",
             {"expected": "6.14.9999-rc15", "is_exception": False, "is_liquorix": False, "is_rc": True,
              "expected_dict": {"major": 6, "minor": 14, "revision": 9999, "release_candidate": 15, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, "6.14.9999-rc15fff",
             {"expected": "6.14.9999-rc15fff", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 6, "minor": 14, "revision": 9999, "release_candidate": 0, "patch": 0,
                                "variant": "rc15fff"}}),
            (LinuxKernelVersion, "6.14-012345ggg",
             {"expected": "6.14-012345ggg", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 6, "minor": 14, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": "012345ggg"}}),
            (LinuxKernelVersion, {"major": 1, "minor": 2},
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, {"major1": 1, "minor": 2},
             {"expected": f"0.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, None,
             {"expected": f"0.0", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 0, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, {},
             {"expected": f"0.0", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 0, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, LinuxKernelVersion(),
             {"expected": f"0.0", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 0, "minor": 0, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, LinuxKernelVersion("1.2"),
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (LinuxKernelVersion, UnitTest_LinuxKernelVersion.LinuxKernelVersionTest("1.2"),
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}}),
            (UnitTest_LinuxKernelVersion.LinuxKernelVersionTest, LinuxKernelVersion("1.2"),
             {"expected": f"1.2", "is_exception": False, "is_liquorix": False, "is_rc": False,
              "expected_dict": {"major": 1, "minor": 2, "revision": 0, "release_candidate": 0, "patch": 0,
                                "variant": ""}})
        ]

        for class_type, initiate, test_data in ref_table:
            target = None
            try:
                target = class_type(initiate)
                self.assertFalse(test_data["is_exception"], f"No exception for \"{initiate}\"")
            except Exception as ex:
                self.assertTrue(test_data["is_exception"], f"Exception for \"{initiate}\": {ex}")

            if target is not None:
                self.assertEqual(target.get_fields_as_dict(), test_data["expected_dict"])
                self.assertEqual(str(class_type(initiate)), test_data["expected"])
                self.assertEqual(target.is_liquorix(), test_data["is_liquorix"])
                self.assertEqual(target.is_rc(), test_data["is_rc"])

    def test_compare(self):
        ref_table = [
            {"first": "6.12", "second": "6.12.0-0", "compare":
                {"==": True, "!=": False, ">": False, ">=": True, "<": False, "<=": True}},
            {"first": "6.15", "second": "6.12", "compare":
                {"==": False, "!=": True, ">": True, ">=": True, "<": False, "<=": False}},
            {"first": "6.15.1", "second": "6.15", "compare":
                {"==": False, "!=": True, ">": True, ">=": True, "<": False, "<=": False}},
            {"first": "6.15-rc1", "second": "6.15.1", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}},
            {"first": "6.15.1-rc1", "second": "6.15.1", "compare":
                {"==": False, "!=": True, ">": True, ">=": True, "<": False, "<=": False}},
            {"first": "6.15.1", "second": "6.15.1-1", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}},
            {"first": "6.15.1-generic", "second": "6.15.1-liquorix", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}},
            {"first": "5.15-133-generic", "second": "6.5-35-generic", "compare":
                {"==": False, "!=": True, ">": False, ">=": False, "<": True, "<=": True}}
        ]

        for item in ref_table:
            first = LinuxKernelVersion(item["first"])
            second = LinuxKernelVersion(item["second"])
            for operation, expected in item["compare"].items():
                if operation == "==":
                    self.assertEqual(first == second, expected, f"{first} {operation} {second}")
                elif operation == "!=":
                    self.assertEqual(first != second, expected, f"{first} {operation} {second}")
                elif operation == ">":
                    self.assertEqual(first > second, expected, f"{first} {operation} {second}")
                elif operation == ">=":
                    self.assertEqual(first >= second, expected, f"{first} {operation} {second}")
                elif operation == "<":
                    self.assertEqual(first < second, expected, f"{first} {operation} {second}")
                elif operation == "<=":
                    self.assertEqual(first <= second, expected, f"{first} {operation} {second}")

    def test_sort(self):
        test_data = [LinuxKernelVersion("6.14-1-liquorix-amd64"), LinuxKernelVersion("5.15-133-generic"),
                     LinuxKernelVersion("5.15-134-generic"), LinuxKernelVersion("5.15-136-generic"),
                     LinuxKernelVersion("6.5-35-generic"), LinuxKernelVersion("6.8-50-generic"),
                     LinuxKernelVersion("6.8-52-generic"), LinuxKernelVersion("6.8-57-generic"),
                     LinuxKernelVersion("5.15-91-generic")]
        expected_data = [LinuxKernelVersion("5.15-91-generic"), LinuxKernelVersion("5.15-133-generic"),
                         LinuxKernelVersion("5.15-134-generic"), LinuxKernelVersion("5.15-136-generic"),
                         LinuxKernelVersion("6.5-35-generic"), LinuxKernelVersion("6.8-50-generic"),
                         LinuxKernelVersion("6.8-52-generic"), LinuxKernelVersion("6.8-57-generic"),
                         LinuxKernelVersion("6.14-1-liquorix-amd64")]
        test_data.sort()
        self.assertEqual(test_data, expected_data)
