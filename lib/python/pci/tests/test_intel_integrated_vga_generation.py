import json
import pathlib
import unittest

from lib.python.pci import IntelIntegratedVgaGeneration, PciVidPid


class UnitTest_IntelIntegratedVgaGeneration(unittest.TestCase):
    ENCODING = "utf-8"

    TEST_DATA_DIR_NAME = "test_generation"
    INPUT_FILE_NAME = "input.json"
    EXPECTED_RESULT_FILE_NAME = "expected_result.json"
    DESCRIPTION_FILE_NAME = "description.txt"

    def test_generation(self):
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

                generation = IntelIntegratedVgaGeneration.from_device_id(PciVidPid(input_model["device_id"]))
                result = {"generation": str(generation),
                          "number": generation.get_generation(),
                          "upt_supported": generation.is_upt_supported(),
                          "legacy_supported": generation.is_legacy_supported(),
                          "stolen_memory_size_supported": generation.is_stolen_memory_size_supported()}

                self.assertEqual(result, expected_result)
