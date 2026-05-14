import base64
import importlib.util
import os
import requests


def _load_credentials() -> tuple[str, str]:
    key_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "private", "api-key.py")
    )
    spec = importlib.util.spec_from_file_location("_t212_api_key", key_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.api.strip(), mod.secret.strip()


def _basic_auth_header() -> str:
    api_key, secret = _load_credentials()
    token = base64.b64encode(f"{api_key}:{secret}".encode()).decode()
    return f"Basic {token}"


class T212Client:
    LIVE_URL = "https://live.trading212.com/api/v0"
    DEMO_URL = "https://demo.trading212.com/api/v0"

    def __init__(self, mode: str = "live"):
        self._base = self.LIVE_URL if mode == "live" else self.DEMO_URL
        self._session = requests.Session()
        self._session.headers["Authorization"] = _basic_auth_header()

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        r = self._session.get(f"{self._base}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def _paginate(self, path: str) -> list:
        """Fetch all pages from a paginated endpoint.

        nextPagePath from T212 is relative to the domain root (e.g.
        /api/v0/equity/history/dividends?cursor=...), so we build URLs
        from the domain base, not the /api/v0 base.
        """
        domain = self._base.split("/api/")[0]  # https://live.trading212.com
        items: list = []
        url: str | None = f"{self._base}{path}?limit=50"
        while url:
            r = self._session.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            batch = data.get("items", [])
            items.extend(batch)
            next_path = data.get("nextPagePath")
            url = f"{domain}{next_path}" if next_path and batch else None
        return items

    def account_summary(self) -> dict:
        return self._get("/equity/account/cash")

    def portfolio(self) -> list:
        data = self._get("/equity/portfolio")
        if isinstance(data, list):
            return data
        return data.get("items", [])

    def orders(self) -> list:
        return self._paginate("/equity/history/orders")

    def dividends(self) -> list:
        return self._paginate("/equity/history/dividends")

    def pies(self) -> list:
        data = self._get("/equity/pies")
        if isinstance(data, list):
            return data
        return data.get("items", [])
