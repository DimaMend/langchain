"""Tool for the OpenWeatherMap API."""

from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from langchain_community.utilities.openweathermap import OpenWeatherMapAPIWrapper


class OpenWeatherMapQueryRunToolInput(BaseModel):
    """Input for the OpenWeatherMapQueryRunTool tool."""

    location: str = Field(
        description="""Location String to be used for 
                          OpenWeatherMap API"""
    )


class OpenWeatherMapQueryRun(BaseTool):
    """Tool that queries the OpenWeatherMap API."""

    api_wrapper: OpenWeatherMapAPIWrapper = Field(
        default_factory=OpenWeatherMapAPIWrapper
    )

    name: str = "open_weather_map"
    description: str = (
        "A wrapper around OpenWeatherMap API. "
        "Useful for fetching current weather information for a specified location. "
        "Input should be a location string (e.g. London,GB)."
    )
    args_schema: Type[BaseModel] = OpenWeatherMapQueryRunToolInput

    def _run(
        self, location: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the OpenWeatherMap tool."""
        return self.api_wrapper.run(location)
