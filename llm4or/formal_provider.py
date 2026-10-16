"""User-selected provider for future formal runs; separate from closed pilots.

Only an authorized transport worker calls load_credential. Imports and offline
preflight never read the secret. No fallback to ARK, Codex or old pilot keys.
"""
import json
import os
from pathlib import Path
import stat
from .gateway import Stopped

BASE_URL = 'https://antchat.alipay.com/v1'
MODEL = 'DeepSeek-V4-Flash'
PROFILE = Path.home() / '.config/llm4or-eaai/antchat-flash.json'


def check_profile_metadata(path=None):
    path = PROFILE if path is None else Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
        raise Stopped('formal_private_profile_permissions_or_owner')
    if not 0 < info.st_size <= 16384:
        raise Stopped('formal_private_profile_size')


def load_credential():
    check_profile_metadata()
    fd = os.open(PROFILE, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
            raise Stopped('formal_private_profile_permissions_or_owner')
        try:
            config = json.loads(stream.read(16385))
        except (ValueError, UnicodeError):
            raise Stopped('formal_private_profile_invalid_json') from None
    if not isinstance(config, dict) or set(config) != {'base_url', 'model', 'api_key'}:
        raise Stopped('formal_private_profile_schema')
    if config['base_url'] != BASE_URL or config['model'] != MODEL:
        raise Stopped('formal_private_profile_endpoint_or_model_mismatch')
    secret = config['api_key']
    if not isinstance(secret, str) or not secret.strip() or len(secret) > 4096 or '\n' in secret or '\r' in secret:
        raise Stopped('formal_private_profile_invalid_key')
    return secret
