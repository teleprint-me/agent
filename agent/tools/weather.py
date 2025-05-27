"""
agent.tools.weather
"""

from time import sleep

from agent.backend.wttr import Weather


def get_weather(location: str, units: str = "metric") -> str:
    """
    Get the current weather in a given location.
    Parameters:
    location (str): The city and state, e.g. San Francisco, CA
    unit (str): The unit system, can be either 'metric' or 'uscs'. Default is 'metric'.
    Returns:
    str: A string that describes the current weather.
    """
    # Set the API response formatting
    wx = Weather()
    result = wx.get_custom(location, fmt="%l+%T+%S+%s+%C+%w+%t", unit=units)
    return wx.denormalize(result)


if __name__ == "__main__":
    __timeout__ = 1 / (1000 / 3600)  # be kind to beautiful services like wttr!
    locations = [
        "",
        "New York City, New York",
        "Paris, France",
        "Tokyo, Japan",
        "London",
    ]
    print(f"Timeout per cycle: {__timeout__}")
    for location in locations:
        sleep(__timeout__)
        print(get_weather(location))
