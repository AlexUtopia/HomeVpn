"""Тесты PCI устройств."""

import pathlib
import unittest

from lib.python.pci import Pci


class UnitTest_Pci(unittest.TestCase):  # pylint: disable=invalid-name
    """Проверка разбора ``lspci`` и значений по умолчанию полей"""

    ENCODING = "utf-8"

    def test_iommu_group_default(self) -> None:
        """Поле iommu_group по умолчанию None, а 0 остаётся валидной группой"""
        pci = Pci()

        self.assertIsNone(pci.iommu_group)
        self.assertEqual(pci.get_regex_for("iommu_group", is_capture=False), "[0-9]{1,3}")
        self.assertIn('"iommu_group": null', str(pci))

        pci["iommu_group"] = "3"
        self.assertEqual(pci.iommu_group, 3)
        self.assertIn('"iommu_group": 3', str(pci))

        pci["iommu_group"] = None
        self.assertIsNone(pci.iommu_group)

    def test_lspci_output_parse(self) -> None:
        """Разбор вывода ``lspci`` совпадает с эталонным JSON"""
        test_dir_path = pathlib.Path(__file__).resolve().parent / self.__class__.__name__ / "test_lspci_output_parse"
        for path in test_dir_path.iterdir():
            lspci_output_mock = (path / "lspci_output.txt").read_text(encoding=self.ENCODING)
            expected_result = Pci.PciList.from_string(
                (path / "expected_result.json").read_text(encoding=self.ENCODING))

            result = Pci.get_list(lspci_output_mock=lspci_output_mock)
            self.assertEqual(result, expected_result)
            self.assertEqual(str(result.to_sorted_list()), str(expected_result.to_sorted_list()))
