from google.oauth2 import id_token
from google.auth.transport.requests import Request
from google.auth.exceptions import TransportError, GoogleAuthError
import jwt
from requests.exceptions import RequestException
from app.core.config import settings
from app.domains.auth.service import GoogleIdentity


def verify_google(token):
    if not settings.google_client_ids:
        raise RuntimeError("GOOGLE_CLIENT_IDS is required")
    try:
        claims = id_token.verify_oauth2_token(token, Request(), audience=settings.google_client_ids)
    except (TransportError, RequestException) as exc:
        raise ConnectionError() from exc
    except (GoogleAuthError, jwt.InvalidTokenError) as exc:
        raise ValueError("Invalid Google credential") from exc
    for field in ("sub", "email", "name"):
        if not isinstance(claims.get(field), str) or not claims[field]:
            raise ValueError("Missing Google profile")
    if len(claims['sub']) > 255 or len(claims['email']) > 255 or len(claims['name']) > 50:
        raise ValueError("Invalid Google profile length")
    image = claims.get('picture')
    if image is not None and (not isinstance(image, str) or len(image) > 500):
        raise ValueError("Invalid profile image")
    return GoogleIdentity(claims['sub'], claims['email'], claims['name'], image)
