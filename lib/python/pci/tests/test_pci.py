import pathlib
import unittest

from lib.python.pci import Pci


class UnitTest_Pci(unittest.TestCase):
    ENCODING = "utf-8"

    def test_lspci_output_parse(self):
        for path in (pathlib.Path(__file__).resolve() / self.__class__.__name__ / "test_lspci_output_parse").iterdir():
            lspci_output_mock = (path / "lspci_output.txt").read_text(encoding=self.ENCODING)
            expected_result = Pci.PciList.from_string(
                (path / "expected_result.json").read_text(encoding=self.ENCODING))

            result = Pci.get_list(lspci_output_mock=lspci_output_mock)
            self.assertEqual(result, expected_result)
            self.assertEqual(str(result.to_sorted_list()), str(expected_result.to_sorted_list()))
