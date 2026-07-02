"""
Defensive wrappers around the web-search tools.

Why this file exists:
The raw DuckDuckGoSearchRun / WikipediaQueryRun tools from
langchain_community can raise uncaught exceptions (e.g. the `wikipedia`
package failing to parse a non-JSON response from Wikipedia's API, or
DuckDuckGo rate-limiting). When that happens inside a LangGraph tool node,
the exception propagates all the way up and kills the whole agent run —
the user sees a raw error instead of a graceful message. Wrapping each
call in try/except keeps a single flaky search from taking down the
entire response.
"""
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper

_ddg = DuckDuckGoSearchRun()
_wiki_wrapper = WikipediaAPIWrapper()


@tool
def duckduckgo_search(query: str) -> str:
    """Search the live web via DuckDuckGo. Use this for current events,
    recent news, or anything time-sensitive. Do NOT use this for general
    knowledge that doesn't change — use wikipedia for that instead."""
    try:
        result = _ddg.run(query)
        return result if result else "No web results found for that query."
    except Exception as e:
        return f"Web search is temporarily unavailable ({e}). Try rephrasing, or answer from general knowledge if appropriate and say so."


@tool
def wikipedia(query: str) -> str:
    """Search Wikipedia for general knowledge, historical facts, or
    background info on a well-established topic. Do NOT use this for
    current events or breaking news — use duckduckgo_search for that."""
    try:
        result = _wiki_wrapper.run(query)
        return result if result else "No Wikipedia article found for that query."
    except Exception as e:
        return f"Wikipedia lookup is temporarily unavailable ({e}). Try rephrasing, or answer from general knowledge if appropriate and say so."