import base64
import hashlib
import json
from typing import Any, Dict
from cryptography.fernet import Fernet
from app.core.config import get_settings


def _build_fernet(secret_key: str) -> Fernet:
    try:
        raw = base64.urlsafe_b64decode(secret_key.encode("utf-8"))
        if len(raw) == 32:
            return Fernet(secret_key.encode("utf-8"))
    except Exception:
        pass
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    valid_key = base64.urlsafe_b64encode(digest)
    return Fernet(valid_key)


class TokenVault:
    """Fernet symmetric encryption wrapper for offline OAuth refresh/access tokens."""

    def __init__(self, secret_key: str | None = None):
        key = secret_key or get_settings().FERNET_SECRET_KEY
        self._fernet = _build_fernet(key)

    def encrypt_str(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt_str(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    def encrypt_dict(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, ensure_ascii=False)
        return self.encrypt_str(serialized)

    def decrypt_dict(self, ciphertext: str) -> Dict[str, Any]:
        decrypted = self.decrypt_str(ciphertext)
        return json.loads(decrypted)
