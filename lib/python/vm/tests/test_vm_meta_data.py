import netaddr
import pathlib
import tempfile
import unittest

from lib.python.network import TcpPort

from lib.python.vm import VmMetaData


class UnitTest_VmMetaData(unittest.TestCase):
    def test_mac_address(self):
        vm_name = "test"

        with tempfile.TemporaryDirectory() as temp_dir_path:
            vm_meta_data = VmMetaData(vm_name, temp_dir_path)

            self.assertEqual(vm_meta_data.get_name(), vm_name)
            self.assertIsInstance(vm_meta_data.get_name(), str)
            self.assertEqual(vm_meta_data.get_hostname(), DnsDhcpProvider.get_hostname(vm_name))
            self.assertIsInstance(vm_meta_data.get_hostname(), str)

            self.assertEqual(vm_meta_data.get_image_path(),
                             pathlib.Path(temp_dir_path) / f"{vm_name}.{VmMetaData.IMAGE_EXTENSION}")
            self.assertIsInstance(vm_meta_data.get_image_path(), pathlib.Path)
            self.assertFalse(vm_meta_data.image_exists())
            self.assertIsInstance(vm_meta_data.image_exists(), bool)

            self.assertRaises(Exception, vm_meta_data.check_image_exists)

            # MAC адрес генерируется и сохраняется на диске, поэтому повторный вызов get_mac_address()
            # вернёт тот же результат что и первый вызов
            mac_address1 = vm_meta_data.get_mac_address()
            mac_address2 = vm_meta_data.get_mac_address()
            self.assertEqual(mac_address1, mac_address2)
            self.assertEqual(netaddr.EUI(vm_meta_data.get_mac_address_as_string()), mac_address1)
            self.assertIsInstance(vm_meta_data.get_mac_address(), netaddr.EUI)
            self.assertIsInstance(vm_meta_data.get_mac_address_as_string(), str)

            self.assertEqual(vm_meta_data.get_ssh_forward_port(), None)
            self.assertEqual(vm_meta_data.get_rdp_forward_port(), None)

            self.assertTrue(vm_meta_data.get_working_dir_path().exists())
            self.assertIsInstance(vm_meta_data.get_working_dir_path(), pathlib.Path)

            mac_address_expected = "fd:63:8b:12:6f:5b"
            vm_meta_data.get_mac_address_path().store(mac_address_expected)
            self.assertEqual(vm_meta_data.get_mac_address(), netaddr.EUI(mac_address_expected))

            ssh_forward_port_expected = 111
            vm_meta_data.set_ssh_forward_port(ssh_forward_port_expected)
            self.assertEqual(vm_meta_data.get_ssh_forward_port(), TcpPort(ssh_forward_port_expected))
            self.assertIsInstance(vm_meta_data.get_ssh_forward_port(), TcpPort)

            rdp_forward_port_expected = 222
            vm_meta_data.set_rdp_forward_port(rdp_forward_port_expected)
            self.assertEqual(vm_meta_data.get_rdp_forward_port(), TcpPort(rdp_forward_port_expected))
            self.assertIsInstance(vm_meta_data.get_rdp_forward_port(), TcpPort)

    def test_equal(self):
        with tempfile.TemporaryDirectory() as temp_dir_path:
            vm_meta_data1 = VmMetaData("test", temp_dir_path)
            self.assertEqual(vm_meta_data1, vm_meta_data1)

            vm_meta_data2 = VmMetaData("test", temp_dir_path)
            self.assertEqual(vm_meta_data1, vm_meta_data2)

            vm_meta_data3 = VmMetaData("test3", temp_dir_path)
            self.assertNotEqual(vm_meta_data1, vm_meta_data3)
            self.assertNotEqual(vm_meta_data2, vm_meta_data3)

            vm_meta_data_set = {vm_meta_data1, vm_meta_data2, vm_meta_data3}
            self.assertEqual(len(vm_meta_data_set), 2)

            self.assertTrue(vm_meta_data1 in vm_meta_data_set)
            self.assertTrue(vm_meta_data2 in vm_meta_data_set)
            self.assertTrue(vm_meta_data3 in vm_meta_data_set)