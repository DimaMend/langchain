"""Tool for the Wolfram Alpha API."""

from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from langchain_community.utilities.wolfram_alpha import WolframAlphaAPIWrapper


class WolframAlphaQueryRunRunToolSchema(BaseModel):
    """Input schema for WolframAlphaQueryRun."""

    query: str = Field('Search Query')


class WolframAlphaQueryRun(BaseTool):
    """Tool that queries using the Wolfram Alpha SDK."""

    name: str = "wolfram_alpha"
    description: str = (
        "A wrapper around Wolfram Alpha. "
        "Useful for when you need to answer questions about Math, "
        "Science, Technology, Culture, Society and Everyday Life. "
        "Input should be a search query."
    )
    api_wrapper: WolframAlphaAPIWrapper
    args_schema: Type[WolframAlphaQueryRunRunToolSchema] = WolframAlphaQueryRunRunToolSchema

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the WolframAlpha tool."""
        return self.api_wrapper.run(query)
