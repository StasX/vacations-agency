from base64 import b64encode
from hashlib import pbkdf2_hmac, sha512
from hmac import compare_digest, new as hmac_new
from flask import current_app
from secrets import token_urlsafe

from .app_config import AppConfig


class Security:
    iterations = 1_000_000

    @staticmethod
    def password_fingerprint(stored_hash):
        # Sessions are signed but readable: never put the password hash in them.
        key = current_app.secret_key
        if isinstance(key, str):
            key = key.encode('utf-8')
        return hmac_new(key, ('flask-session-password:' + stored_hash).encode('utf-8'), 'sha256').hexdigest()

    @staticmethod
    def hash(plain_text):
        salt = token_urlsafe(16)
        digest = pbkdf2_hmac("sha256", plain_text.encode("utf-8"), salt.encode("ascii"), Security.iterations)
        return f"pbkdf2_sha256${Security.iterations}${salt}${b64encode(digest).decode('ascii')}"

    @staticmethod
    def verify(plain_text, stored_hash):
        if not isinstance(plain_text, str) or not isinstance(stored_hash, str):
            return False
        if len(stored_hash) == 128 and all(c in "0123456789abcdef" for c in stored_hash):
            # Compatibility only: replace this legacy hash after successful login.
            salt = AppConfig.passwords_salt
            if not isinstance(salt, str):
                return False
            legacy = sha512((plain_text + salt).encode("utf-8")).hexdigest()
            return compare_digest(legacy, stored_hash)
        try:
            algorithm, rounds, salt, expected = stored_hash.split("$")
            iterations = int(rounds)
            if algorithm != "pbkdf2_sha256" or not 1 <= iterations <= 10_000_000 or not salt:
                return False
            digest = pbkdf2_hmac("sha256", plain_text.encode("utf-8"), salt.encode("ascii"), iterations)
            return compare_digest(b64encode(digest), expected.encode("ascii"))
        except (ValueError, TypeError, UnicodeError):
            return False

    @staticmethod
    def needs_rehash(stored_hash):
        try:
            algorithm, rounds, _, _ = stored_hash.split("$")
            return algorithm != "pbkdf2_sha256" or int(rounds) < Security.iterations
        except (ValueError, AttributeError):
            return True
