import json
import pathlib
import unittest

from lib.python.pci import IntelIntegratedVgaGeneration, IntelIntegratedVgaStolenMemorySize, PciVidPid


class UnitTest_IntelIntegratedVgaStolenMemorySize(unittest.TestCase):
    ENCODING = "utf-8"

    TEST_DATA_DIR_NAME = "test_stolen_memory_size"
    INPUT_FILE_NAME = "input.json"
    INPUT_CONFIG_FILE_NAME = "input_config.bin"
    EXPECTED_RESULT_FILE_NAME = "expected_result.json"
    DESCRIPTION_FILE_NAME = "description.txt"

    def test_stolen_memory_size(self):
        test_data_dir_path = pathlib.Path(__file__).resolve().parent / \
                             self.__class__.__name__ / self.TEST_DATA_DIR_NAME

        for case_dir_path in sorted(test_data_dir_path.iterdir()):
            with self.subTest(case=case_dir_path.name):
                description_file_path = case_dir_path / self.DESCRIPTION_FILE_NAME
                self.assertTrue(description_file_path.exists())
                self.assertTrue(description_file_path.read_text(encoding=self.ENCODING).strip())

                input_model = json.loads(
                    (case_dir_path / self.INPUT_FILE_NAME).read_text(encoding=self.ENCODING))
                expected_result = json.loads(
                    (case_dir_path / self.EXPECTED_RESULT_FILE_NAME).read_text(encoding=self.ENCODING))

                config = (case_dir_path / self.INPUT_CONFIG_FILE_NAME).read_bytes()
                ggc_begin = IntelIntegratedVgaStolenMemorySize.GGC_OFFSET
                ggc_end = ggc_begin + IntelIntegratedVgaStolenMemorySize.GGC_SIZE
                self.assertGreaterEqual(len(config), ggc_end)
                ggc = int.from_bytes(config[ggc_begin:ggc_end], byteorder="little")

                generation = IntelIntegratedVgaGeneration.from_device_id(PciVidPid(input_model["device_id"]))

                if expected_result.get("exception"):
                    self.assertRaises(Exception, IntelIntegratedVgaStolenMemorySize.from_ggc, ggc, generation)
                    continue

                size = IntelIntegratedVgaStolenMemorySize.from_ggc(ggc, generation)
                result = {"gms": size.get_gms(),
                          "size_in_bytes": size.get_size_in_bytes(),
                          "size_in_mib": size.get_size_in_mib()}

                self.assertEqual(result, expected_result)
