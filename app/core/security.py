from datetime import datetime, timezone
import jwt
from app.core.config import settings


def key(kind):
    secrets = (settings.signup_token_secret, settings.access_token_secret)
    if any(len(s.encode()) < 32 for s in secrets) or secrets[0] == secrets[1]:
        raise RuntimeError("Configure distinct signing secrets of at least 32 bytes")
    return secrets[0 if kind == "signup" else 1]


def issue(kind, subject, **claims):
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = getattr(settings, f"{kind}_token_ttl_seconds")
    if ttl <= 0:
        raise RuntimeError("Token lifetime must be positive")
    return jwt.encode(dict(claims, sub=str(subject), purpose=kind, aud=f"jjo-{kind}",
                           iss=settings.auth_issuer, iat=now, exp=now + ttl), key(kind), algorithm="HS256")


def verify(kind, token):
    data = jwt.decode(token, key(kind), algorithms=["HS256"], audience=f"jjo-{kind}",
                      issuer=settings.auth_issuer, options={"require": ["sub", "exp", "iat", "aud", "iss", "purpose"]})
    if kind == "signup" and any(not isinstance(data.get(field), str) or not data[field] for field in ("email", "name")):
        raise jwt.InvalidTokenError("Missing signup profile")
    if data["purpose"] != kind:
        raise jwt.InvalidTokenError()
    return data
