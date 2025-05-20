"""
agent.api.wttr
"""

from typing import Any, Dict, Optional, Union

import requests


class Weather:
    """
    Minimal wttr.in API wrapper. LLM/tool and REST-friendly.
    """

    BASE_URL = "https://wttr.in"

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: float = 8.0,
    ):
        self.session = session or requests.Session()
        self.timeout = timeout

    @staticmethod
    def normalize(location: str) -> str:
        """
        Prepares a location string for wttr.in path usage.
        - 'Paris, France' -> 'Paris_-France'
        - 'New York City, New York' -> 'New-York-City_-New-York'
        """
        return location.replace(" ", "-").replace(",", "_") if location else ""

    @staticmethod
    def denormalize(result: str) -> str:
        """
        Converts wttr.in-style location back to a natural readable name.
        - 'Paris_-France' -> 'Paris, France'
        - 'New-York-City_-New-York' -> 'New York City, New York'
        NOTE: This is only useful for inline responses and does not account for errors.
        """
        parts = result.split(" ")
        parts[0] = parts[0].replace("-", " ").replace("_", ",")
        return " ".join(parts)

    def get(
        self,
        location: Optional[str] = None,
        format: str = "j1",  # 'j1' for JSON, '3' for single line, etc.
        units: str = "metric",  # 'metric', 'uscs', or None (default by geo)
        lang: Optional[str] = None,  # Language code, e.g. 'en', 'de', etc.
        raw: bool = False,  # If True, return raw response object.
        **extra: Any,
    ) -> Union[str, Dict[str, Any], requests.Response]:
        """
        Query wttr.in for weather.

        Parameters:
            location (str): City, address, or special string (e.g., 'London', 'JFK', '~Eiffel+Tower').
            format (str): Output format (e.g., 'j1', '3', custom percent notation).
            units (str): 'metric', 'uscs', or None for geo default.
            lang (str): Language code.
            raw (bool): Return raw response object instead of parsed result.
            extra: Any other query string params.

        Returns:
            str | dict | requests.Response
        """
        loc = Weather.normalize(location)
        params = {}

        # Handle units as wttr.in expects them
        if units:
            if units.lower() == "metric":
                params["m"] = None
            elif units.lower() == "uscs":
                params["u"] = None
            elif units.lower() == "m/s":
                params["M"] = None

        # Set format
        if format:
            params["format"] = format

        # Set language
        if lang:
            params["lang"] = lang

        # Add any extra query params
        params.update(extra)

        # Build query string
        # Drop params with value=None (becomes just ?m or ?u)
        query = "&".join(k if v is None else f"{k}={v}" for k, v in params.items())

        url = f"{self.BASE_URL}/{loc}"
        if query:
            url += f"?{query}"

        resp = self.session.get(url, timeout=self.timeout)

        if raw:
            return resp
        if resp.status_code != 200:
            return f"Could not get weather for '{location or 'current location'}': {resp.status_code}"

        # If JSON output requested, parse it
        if format == "j1":
            try:
                return resp.json()
            except Exception:
                return resp.text

        return resp.text

    def get_text(self, location: Optional[str] = None, **kwargs) -> str:
        """
        Return plain-text, single-line, or formatted weather string.
        """
        kwargs.setdefault("format", "3")  # Prettiest one-liner by default
        return str(self.get(location, **kwargs)).strip()

    def get_json(self, location: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Return parsed JSON weather info.
        """
        kwargs.setdefault("format", "j1")
        result = self.get(location, **kwargs)
        if isinstance(result, dict):
            return result
        try:
            return requests.models.json.loads(result)
        except Exception:
            return {}

    def get_custom(self, location: Optional[str], fmt: str, **kwargs) -> str:
        """
        Return weather with a custom wttr.in format string.
        Example: fmt = "%l+%C+%t+%w"
        """
        kwargs["format"] = fmt
        return self.get(location, **kwargs)


# USAGE EXAMPLES
if __name__ == "__main__":
    wx = Weather()

    # Get a one-liner (default)
    print(wx.get_text(""))  # Empty string uses current location

    # Get JSON weather
    # for k, v in wx.get_json("San Francisco, CA")["current_condition"][0].items():
    #     print(f"{k}: {v}")

    # Custom format (emoji + temp)
    # print(wx.get_custom("Paris, France", fmt="%l: %C %t"))

    # Raw text (e.g., multi-line ASCII)
    # print(wx.get("New York City, New York", format=None))
