import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from phonedrive import credentials
from phonedrive.background import BackgroundService
from phonedrive.config import Config, SavedDevice
from phonedrive.discovery import DeviceDiscovery, DeviceInfo, SERVICE_TYPE
from phonedrive.mount_manager import MountInfo, MountManager


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.saved = SavedDevice("Phone", "192.0.2.1", 2222, "phone", "encrypted", "P")
        self.config = Mock(auto_mount=True, saved_devices=[self.saved])
        self.config.decrypt_password.return_value = "password"
        self.mm = MountManager()
        self.mapping = patch.object(self.mm, "get_mapping", return_value=None).start()
        self.mount = patch.object(self.mm, "mount", return_value=(True, "Mounted")).start()
        self.unmount = patch.object(self.mm, "unmount", return_value=True).start()
        self.addCleanup(patch.stopall)
        self.probe = Mock(return_value=True)
        self.service = BackgroundService(self.config, self.mm, Mock(), self.probe)
        self.remote = self.mm.remote_path(self.saved.ip, 2222, "phone")

    def test_discovery_loss_preserves_live_mount(self):
        self.mapping.return_value = MountInfo("P", self.remote, "OK")
        self.service.reconcile(now=0)
        self.service.on_device_lost("Phone")
        self.service.reconcile(now=65)
        self.unmount.assert_not_called()
        self.mount.assert_not_called()
        self.assertEqual(self.service.mounted_devices["Phone"], "P")

    def test_disconnected_mapping_recovers_without_new_advertisement(self):
        self.mapping.return_value = MountInfo("P", self.remote, "Disconnected")
        self.service.reconcile(now=0)
        self.unmount.assert_called_once_with("P", self.remote)
        self.mount.assert_called_once_with("192.0.2.1", 2222, "phone", "password", "P")

    def test_busy_mapping_is_retained_and_retried(self):
        self.service.track(self.saved)
        self.mapping.return_value = MountInfo("P", self.remote, "Disconnected")
        self.unmount.side_effect = [False, True]
        self.service.reconcile(now=0)
        self.assertEqual(self.service.mounted_devices["Phone"], "P")
        self.mount.assert_not_called()
        self.service.reconcile(now=1)
        self.assertEqual(self.unmount.call_count, 1)
        self.service.reconcile(now=5)
        self.mount.assert_called_once()

    def test_automount_off_does_not_mount_saved_device(self):
        self.config.auto_mount = False
        self.service.on_device_found(DeviceInfo("Phone", "192.0.2.1", 2222, "", 0))
        self.service.reconcile(now=100)
        self.mount.assert_not_called()
        self.probe.assert_not_called()

    def test_manual_mount_recovers_even_when_automount_off(self):
        self.config.auto_mount = False
        self.service.track(self.saved)
        self.service.reconcile(now=0)
        self.mount.assert_called_once()

    def test_explicit_unmount_suppresses_automatic_recreation(self):
        self.service.track(self.saved)
        self.service.untrack_drive("P")
        self.service.reconcile(now=0)
        self.mount.assert_not_called()

    def test_unrelated_mapping_is_never_removed(self):
        self.mapping.return_value = MountInfo("P", r"\\fileserver\work", "Disconnected")
        self.service.reconcile(now=0)
        self.unmount.assert_not_called()
        self.mount.assert_not_called()

    def test_failed_mount_retries_without_discovery(self):
        self.mount.side_effect = [(False, "Unavailable"), (True, "Mounted")]
        self.service.reconcile(now=0)
        self.service.reconcile(now=1)
        self.assertEqual(self.mount.call_count, 1)
        self.service.reconcile(now=5)
        self.assertEqual(self.mount.call_count, 2)

    def test_ip_change_replaces_only_our_old_mapping(self):
        self.mapping.return_value = MountInfo("P", self.remote, "Disconnected")
        self.service.on_device_found(DeviceInfo("Phone", "192.0.2.2", 2222, "", 0))
        self.service.reconcile(now=0)
        self.unmount.assert_called_once_with("P", self.remote)
        self.mount.assert_called_once_with("192.0.2.2", 2222, "phone", "password", "P")
        self.assertEqual(self.saved.ip, "192.0.2.2")

    def test_endpoint_outage_does_not_unmount_until_return(self):
        self.mapping.return_value = MountInfo("P", self.remote, "OK")
        self.probe.return_value = False
        for now in (0, 5, 15):
            self.service.reconcile(now=now)
        self.unmount.assert_not_called()
        self.probe.return_value = True
        self.service.reconcile(now=35)
        self.unmount.assert_called_once_with("P", self.remote)
        self.mount.assert_called_once()


class DiscoveryTests(unittest.TestCase):
    def test_refresh_cancels_browser_before_closing_zeroconf(self):
        discovery = DeviceDiscovery()
        events = []
        discovery.browser = Mock(cancel=lambda: events.append("cancel"))
        discovery.zeroconf = Mock(close=lambda: events.append("close"))
        discovery.scanning = True
        discovery.stop_scanning()
        self.assertEqual(events, ["cancel", "close"])

    def test_obsolete_browser_callback_cannot_remove_new_device(self):
        discovery = DeviceDiscovery()
        discovery.scanning = True
        discovery.zeroconf = Mock()
        discovery.devices["Phone"] = DeviceInfo("Phone", "192.0.2.1", 2222, "", 0)
        discovery.on_device_lost = Mock()
        discovery.remove_service(Mock(), SERVICE_TYPE, "Phone." + SERVICE_TYPE)
        self.assertIn("Phone", discovery.devices)
        discovery.on_device_lost.assert_not_called()


class MountTests(unittest.TestCase):
    def test_disconnected_entry_is_not_mounted(self):
        manager = MountManager()
        with patch.object(manager, "get_mapping", return_value=MountInfo("P", r"\\sshfs\phone@192.0.2.1!2222", "Disconnected")):
            self.assertFalse(manager.is_mounted("P"))

    def test_wrong_remote_is_not_mounted(self):
        manager = MountManager()
        with patch.object(manager, "get_mapping", return_value=MountInfo("P", r"\\other\share", "OK")):
            self.assertFalse(manager.is_mounted("P", r"\\sshfs\phone@192.0.2.1!2222"))

    def test_unmount_refuses_changed_owner(self):
        manager = MountManager()
        with patch.object(manager, "get_mapping", return_value=MountInfo("P", r"\\sshfs\other@192.0.2.5!2222", "OK")), patch.object(manager, "_disconnect") as disconnect:
            self.assertFalse(manager.unmount("P", r"\\sshfs\phone@192.0.2.1!2222"))
            disconnect.assert_not_called()


class CredentialTests(unittest.TestCase):
    def test_dpapi_roundtrip_and_tamper_rejection(self):
        try:
            protected = credentials.protect("test-only-s3cret")
        except OSError as exc:
            self.skipTest(f"Windows DPAPI unavailable in this test environment: {exc}")
        self.assertTrue(protected.startswith(credentials.PREFIX))
        self.assertNotIn("test-only-s3cret", protected)
        self.assertEqual(credentials.unprotect(protected), "test-only-s3cret")
        corrupted = credentials.PREFIX + base64.b64encode(b"invalid DPAPI blob").decode()
        with self.assertRaises(OSError):
            credentials.unprotect(corrupted)

    def test_legacy_config_migrates_atomically(self):
        legacy = base64.b64encode(bytes(b ^ 0xAA for b in b"old-password")).decode()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, APPDATA=folder):
            Config._instance = None
            self.addCleanup(setattr, Config, "_instance", None)
            appdir = Path(folder) / "PhoneDrive"
            appdir.mkdir()
            path = appdir / "config.json"
            path.write_text(json.dumps({"saved_devices": [dict(name="Phone", ip="192.0.2.1", port=2222,
                username="phone", password_encrypted=legacy, drive_letter="P")]}))
            config = Config()
            stored = json.loads(path.read_text())["saved_devices"][0]["password_encrypted"]
            if not stored.startswith(credentials.PREFIX):
                self.skipTest("Windows DPAPI unavailable in this test environment")
            self.assertTrue(stored.startswith(credentials.PREFIX))
            self.assertEqual(config.decrypt_password(stored), "old-password")

    def test_failed_encryption_preserves_original_config(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, APPDATA=folder):
            Config._instance = None
            self.addCleanup(setattr, Config, "_instance", None)
            config = Config()
            config.save()
            before = Path(config.config_path).read_bytes()
            legacy = base64.b64encode(bytes(b ^ 0xAA for b in b"old-password")).decode()
            config.saved_devices = [SavedDevice("Phone", "192.0.2.1", 2222, "phone", legacy, "P")]
            with patch.object(credentials, "protect", side_effect=OSError("DPAPI unavailable")):
                with self.assertRaises(OSError):
                    config.save()
            self.assertEqual(Path(config.config_path).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
