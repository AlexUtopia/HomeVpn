import unittest

from lib.python.pci import PciAddress


class UnitTest_PciAddress(unittest.TestCase):
    class PciAddressTest(PciAddress):
        pass

    class UnknownClass:
        pass

    def test(self):
        ref_table = [
            (PciAddress, "",
             {"is_exception": True}),
            (PciAddress, "Hello world",
             {"is_exception": True}),
            (PciAddress, 17,
             {"is_exception": True}),
            (PciAddress, UnitTest_PciAddress.UnknownClass,
             {"is_exception": True}),
            (PciAddress, "0000:00:00.0",
             {"expected": "0000:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, "0000:00:02.0",
             {"expected": "0000:00:02.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 2, "func": 0}}),
            (PciAddress, "0000:00:1F.1",
             {"expected": "0000:00:1f.1", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0x1F, "func": 1}}),
            (PciAddress, "00:1F.1",
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:1f.1", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0x1F, "func": 1}}),
            (PciAddress, None,
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, {"bus": 1, "slot": 2, "func": 3},
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:01:02.3", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 1, "slot": 2, "func": 3}}),
            (PciAddress, {"bus0": 1, "slot": 0xFF, "func_": 3},
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:ff.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0xFF, "func": 0}}),
            (PciAddress, {},
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, PciAddress(),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:00:00.0", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0, "slot": 0, "func": 0}}),
            (PciAddress, PciAddress("AA:BB.255"),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:aa:bb.255", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0xAA, "slot": 0xBB, "func": 255}}),
            (PciAddress, UnitTest_PciAddress.PciAddressTest("AA:BB.255"),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:aa:bb.255", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0xAA, "slot": 0xBB, "func": 255}}),
            (UnitTest_PciAddress.PciAddressTest, PciAddress("AA:BB.255"),
             {"expected": f"{PciAddress.DOMAIN_DEFAULT}:aa:bb.255", "is_exception": False,
              "expected_dict": {"domain": 0, "bus": 0xAA, "slot": 0xBB, "func": 255}}),
        ]

        for pci_address_type, initiate, test_data in ref_table:
            pci_address = None
            try:
                pci_address = pci_address_type(initiate)
                self.assertFalse(test_data["is_exception"], f"No exception for \"{initiate}\"")
            except Exception as ex:
                self.assertTrue(test_data["is_exception"], f"Exception for \"{initiate}\": {ex}")

            if pci_address is not None:
                self.assertEqual(pci_address.get_fields_as_dict(), test_data["expected_dict"])
                self.assertEqual(str(pci_address_type(initiate)), test_data["expected"])
