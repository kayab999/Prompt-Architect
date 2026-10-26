import hashlib
import hmac
import json
import os
import secrets
from typing import Dict, Optional

class QuestSigner:
    def __init__(self, secret_key: Optional[str] = None):
        # Prefer explicit key, then PA_SYSTEM_KEY, then runtime settings
        if secret_key:
            self.secret_key = secret_key
        else:
            env_key = os.getenv("PA_SYSTEM_KEY") or os.getenv("SYSTEM_KEY")
            if env_key:
                self.secret_key = env_key
            else:
                try:
                    from ..config import settings

                    self.secret_key = settings.SYSTEM_KEY
                except Exception:
                    # Last resort for isolated unit tests only
                    self.secret_key = secrets.token_urlsafe(32)

    def sign(self, data: Dict) -> str:
        """Signs the data dictionary using HMAC-SHA256."""
        # Ensure consistent sorting for signing
        data_json = json.dumps(data, sort_keys=True)
        return hmac.new(self.secret_key.encode(), data_json.encode(), hashlib.sha256).hexdigest()

    def verify(self, data: Dict, signature: str) -> bool:
        """Verifies the signature."""
        return hmac.compare_digest(self.sign(data), signature)
