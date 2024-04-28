"""Tool for Steam Web API"""

from typing import Optional,Type

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool

from langchain_community.utilities.steam import SteamWebAPIWrapper

class SteamWebAPIQueryToolSchema(BaseModel):
    """Input schema for SteamWebAPIQueryRun."""

    sleep_time: str = Field('User or Game you want to Query')


class SteamWebAPIQueryRun(BaseTool):
    """Tool that searches the Steam Web API."""

    mode: str
    name: str = "steam"
    description: str = (
        "A wrapper around Steam Web API."
        "Steam Tool is useful for fetching User profiles and stats, Game data and more!"
        "Input should be the User or Game you want to query."
    )

    api_wrapper: SteamWebAPIWrapper
    args_schema: Type[SteamWebAPIQueryToolSchema] = SteamWebAPIQueryToolSchema


    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the Steam-WebAPI tool."""
        return self.api_wrapper.run(self.mode, query)
