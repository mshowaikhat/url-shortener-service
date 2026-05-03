"""Short code generation utilities."""

import secrets
import string

BASE62_ALPHABET = string.ascii_letters + string.digits  # 62 chars: a-zA-Z0-9
SHORT_CODE_LENGTH = 8


def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """
    Generate a cryptographically secure random base62 string.

    With 62^8 ≈ 2.18 × 10^14 possible codes, collision probability for our
    project's scale is effectively zero. We still check for collisions on
    write to handle the theoretical edge case.
    """
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
