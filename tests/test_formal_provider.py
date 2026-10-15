"""Provider isolation checks use dummy credentials, never the user's profile."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from llm4or.gateway import Stopped
from llm4or import formal_provider as provider
from llm4or.formal_gateway import wire_body


class FormalProviderTests(unittest.TestCase):
    def profile(self, directory, **updates):
        path = Path(directory)/'profile.json'
        value = {'base_url':provider.BASE_URL,'model':provider.MODEL,'api_key':'dummy-test-only'}
        value.update(updates)
        path.write_text(json.dumps(value));path.chmod(0o600)
        return path

    def test_wire_selects_flash_without_changing_legacy_pilot(self):
        from llm4or.live import MODEL as old_model
        self.assertEqual(wire_body({'instruction':'test'},8192)['model'],'DeepSeek-V4-Flash')
        self.assertEqual(old_model,'DeepSeek-V4-Pro-0813')

    def test_loads_only_explicit_private_profile(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.profile(d)
            with patch.object(provider,'PROFILE',p):
                self.assertEqual(provider.load_credential(),'dummy-test-only')

    def test_metadata_check_never_reads_secret(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.profile(d)
            with patch.object(Path,'read_text',side_effect=AssertionError('secret read')),patch('builtins.open',side_effect=AssertionError('secret read')):
                provider.check_profile_metadata(p)

    def test_wrong_endpoint_or_model_fails_without_fallback(self):
        for change in [{'base_url':'https://invalid.example/v1'},{'model':'DeepSeek-V4-Pro-0813'}]:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as d:
                p=self.profile(d,**change)
                with patch.object(provider,'PROFILE',p),self.assertRaisesRegex(Stopped,'endpoint_or_model_mismatch'):
                    provider.load_credential()

    def test_public_permissions_or_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.profile(d);p.chmod(0o644)
            with self.assertRaises(Stopped):provider.check_profile_metadata(p)
            p.chmod(0o600);link=Path(d)/'link.json';link.symlink_to(p)
            with self.assertRaises(Stopped):provider.check_profile_metadata(link)

    def test_header_injection_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.profile(d,api_key='dummy\r\nInjected: true')
            with patch.object(provider,'PROFILE',p),self.assertRaisesRegex(Stopped,'invalid_key'):
                provider.load_credential()


if __name__=='__main__':unittest.main()
