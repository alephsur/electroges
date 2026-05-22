import httpx


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class ElectroGesClient:
    """HTTP client for the ElectroGes FastAPI backend.

    Handles cookie-based auth (HttpOnly JWT). Login is lazy — it happens
    on the first request and retries once on 401.
    """

    def __init__(self, base_url: str, email: str, password: str) -> None:
        self._email = email
        self._password = password
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        self._authenticated = False

    async def _login(self) -> None:
        resp = await self._http.post(
            "/api/v1/auth/token",
            json={"email": self._email, "password": self._password},
        )
        if not resp.is_success:
            raise ApiError(resp.status_code, "Login failed — check ELECTROGES_EMAIL and ELECTROGES_PASSWORD")
        self._authenticated = True

    async def _ensure_auth(self) -> None:
        if not self._authenticated:
            await self._login()

    async def _request(self, method: str, path: str, **kwargs) -> object:
        await self._ensure_auth()
        resp = await self._http.request(method, path, **kwargs)
        if resp.status_code == 401:
            self._authenticated = False
            await self._login()
            resp = await self._http.request(method, path, **kwargs)
        if not resp.is_success:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise ApiError(resp.status_code, str(detail))
        if resp.status_code == 204:
            return None
        return resp.json()

    async def get(self, path: str, params: dict | None = None) -> object:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, data: dict | None = None) -> object:
        return await self._request("POST", path, json=data)

    async def patch(self, path: str, data: dict | None = None) -> object:
        return await self._request("PATCH", path, json=data)

    async def delete(self, path: str) -> object:
        return await self._request("DELETE", path)

    async def close(self) -> None:
        await self._http.aclose()
