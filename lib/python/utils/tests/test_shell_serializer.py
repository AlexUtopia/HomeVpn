import unittest

from lib.python.utils import ShellSerializer


class UnitTest_ShellSerializer(unittest.TestCase):

    def test_serialize(self):
        ref_table = {
            '--device="test_device" key "\\\\\\n\\"hello world!!\\"\\r" key1 --device="test_device" -device2 "test_device2" -device3 "test_device3" --key2=15 --key3=18.7 --key4=True': [
                {"--device": "test_device"},
                {"key": "\\\n\"hello world!!\"\r"},
                "key1",
                {"--device": "test_device", "-device2": "test_device2", "-device3": "test_device3"},
                {"--key2": 15, "--key3": 18.7, "--key4": True},
            ],
            '--device="test_device" --device1="test_device1"':
                {
                    "--device": "test_device",
                    "--device1": "test_device1"
                }
        }

        serializer = ShellSerializer()
        for config_serialized, config in ref_table.items():
            result = serializer.serialize(config)
            self.assertEqual(result, config_serialized, f"\n\nRESULT\n{result}\n\nREF\n{config_serialized}")

    def test_nested_fail(self):
        config = {"-device": {"subdevice": "test_device"}}

        serializer = ShellSerializer()
        self.assertRaises(Exception, serializer.serialize, config)