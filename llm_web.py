import llm
import click
import os
from typing import Optional
from pydantic import field_validator, Field

from langchain.agents.agent_types import AgentType
from langchain.agents.initialize import initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.utilities.tavily_search import TavilySearchAPIWrapper
from langchain.tools.tavily_search import TavilySearchResults
from langchain.memory import ConversationBufferMemory
from langchain.agents import load_tools
from langchain.callbacks import get_openai_callback
from langchain.tools import tool

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

DEFAULT_MODEL = "gpt-3.5-turbo-1106"
DEFAULT_TEMP = 0


@llm.hookimpl
def register_models(register):
    register(WebSearch())


class WebSearch(llm.Model):
    VERSION = 0.1
    model_id = "web_search"
    can_stream = False

    class Options(llm.Options):
        quiet: Optional[bool] = Field(
                description="Turn off verbosity of the agent",
                default=False)
        openaimodel: Optional[str] = Field(
                description="OpenAI model to use",
                default=DEFAULT_MODEL,
                )
        temperature: Optional[float] = Field(
                description="Model temperature",
                default=DEFAULT_TEMP)

        @field_validator("quiet")
        def validate_quiet(cls, quiet):
            assert isinstance(quiet, bool), "Invalid type for quiet"

        @field_validator("temperature")
        def validate_temperature(cls, temperature):
            assert isinstance(temperature, float), "Invalid type for temperature"

    def __init__(self, openaimodel=DEFAULT_MODEL, temperature=DEFAULT_TEMP, quiet=False):
        self.verbose = not quiet

        openai_key = llm.get_key(None, "openai", env_var="OPENAI_API_KEY")
        if not openai_key:
            raise click.ClickException(
                "Store a 'openai' key."
            )
        os.environ["OPENAI_API_KEY"] = openai_key
        tavily_key = llm.get_key(None, "tavily", env_var="TAVILY_API_KEY")
        if not tavily_key:
            print("No Tavily API key given, will only use duckduckgo for search.")
        os.environ["TAVILY_API_KEY"] = tavily_key

        chatgpt = ChatOpenAI(
                model_name=openaimodel,
                temperature=temperature,
                verbose=True,
                streaming=False,
                )
        self.tools = load_tools(
                [
                    "ddg-search",
                    # "wikipedia",
                    "llm-math",
                    ],
                llm=chatgpt)
        self.tools.append(userinput)
        try:
            # can only be loaded after the API key was set
            tavily_search = TavilySearchAPIWrapper()
            tavily_tool = TavilySearchResults(api_wrapper=tavily_search)
            self.tools.append(tavily_tool)
        except Exception:
            pass

        # setup agent
        self.agent = initialize_agent(
                self.tools,
                chatgpt,
                verbose=self.verbose,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                memory=memory,
                handle_parsing_errors=True,
                )

        print("I'm an Agent based on OpenAI models. Ask your question and I'll search the internet for you.")

    def execute(self, prompt, stream, response, conversation):
        question = prompt.prompt
        with get_openai_callback() as cb:
            try:
                answer = self.agent.run(question)
            except AskUser as err:
                answer = err.message

            print(f"\nToken so far: {cb.total_tokens} or ${cb.total_cost}")
        return answer


@tool
def userinput(question: str) -> str:
    "Talk with the user if no other tool is currently needed."
    raise AskUser(question)


class AskUser(Exception):
    def __init__(self, message):
        self.message = message
