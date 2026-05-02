import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import Header, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.core.settings import Settings, get_settings


class SupabaseConfigurationError(RuntimeError):
    pass


class SupabaseRequestError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    access_token: str


class SupabaseRestClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.supabase_url:
            raise SupabaseConfigurationError("SUPABASE_URL is not configured.")
        if not self._settings.supabase_publishable_key:
            raise SupabaseConfigurationError(
                "SUPABASE_PUBLISHABLE_KEY is not configured."
            )

        self._base_url = self._settings.supabase_url.rstrip("/")
        self._api_key = self._settings.supabase_publishable_key

    async def get_user(self, access_token: str) -> AuthenticatedUser:
        data = await self.request(
            "GET",
            "/auth/v1/user",
            access_token=access_token,
        )
        user_id = data.get("id") if isinstance(data, dict) else None
        if not user_id:
            raise SupabaseRequestError(status.HTTP_401_UNAUTHORIZED, "Invalid session.")
        return AuthenticatedUser(id=user_id, access_token=access_token)

    async def request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        query: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> Any:
        return await run_in_threadpool(
            self._request_sync,
            method,
            path,
            access_token,
            query,
            json_body,
            prefer,
        )

    def _request_sync(
        self,
        method: str,
        path: str,
        access_token: str,
        query: dict[str, str] | None,
        json_body: dict[str, Any] | None,
        prefer: str | None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, safe='.,():*{}')}"

        body = None
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")

        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer

        request = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(request, timeout=10) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8") or "Supabase request failed."
            raise SupabaseRequestError(exc.code, detail) from exc
        except URLError as exc:
            raise SupabaseRequestError(
                status.HTTP_502_BAD_GATEWAY,
                "Supabase request failed.",
            ) from exc

        if not response_body:
            return None

        try:
            return json.loads(response_body)
        except ValueError as exc:
            raise SupabaseRequestError(
                status.HTTP_502_BAD_GATEWAY,
                "Supabase returned invalid JSON.",
            ) from exc


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None

    return token.strip()


def get_supabase_rest_client() -> SupabaseRestClient:
    return SupabaseRestClient()


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    access_token = _extract_bearer_token(authorization)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Supabase session.",
        )

    try:
        return await get_supabase_rest_client().get_user(access_token)
    except SupabaseConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SupabaseRequestError as exc:
        if exc.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase session.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase request failed.",
        ) from exc
