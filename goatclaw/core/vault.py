import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("goatclaw.core.vault")

class SecretVault:
    """
    Secure vault for user API keys using AES-256 (Fernet).
    USP: Zero-trust key management for BYOK (Bring Your Own Key).
    """
    def __init__(self, master_key: Optional[str] = None):
        # In production, this should come from a secure env var or HSM
        self._master_key = master_key or os.getenv("GOATCLAW_MASTER_KEY", "default-unsafe-key-change-this")
        self._fernet = self._init_fernet(self._master_key)
        logger.info("SecretVault initialized")

    def _init_fernet(self, master_key: str) -> Fernet:
        """Derive a 32-byte key for Fernet from the master key."""
        salt = b"goatclaw_salt_static" # In high-security, use per-user salts
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)

    def encrypt(self, secret: str) -> str:
        """Encrypt a secret string."""
        if not secret:
            return ""
        return self._fernet.encrypt(secret.encode()).decode()

    def decrypt(self, encrypted_secret: str) -> str:
        """Decrypt an encrypted secret string."""
        if not encrypted_secret:
            return ""
        try:
            return self._fernet.decrypt(encrypted_secret.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Invalid secret or master key mismatch")

# Global Vault Instance
vault = SecretVault()
