import json
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
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_ITER = 10
DEFAULT_TREE = False


@llm.hookimpl
def register_models(register):
    register(WebSearch())


class WebSearch(llm.Model):
    VERSION = 0.2
    model_id = "web"
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
        timeout: Optional[int] = Field(
                description="Agent timeout",
                default=DEFAULT_TIMEOUT)
        max_iter: Optional[int] = Field(
                description="Agent max iteration",
                default=DEFAULT_MAX_ITER)
        tree: Optional[bool] = Field(
                description="True to use tree of thoughts",
                default=DEFAULT_TREE)

        @field_validator("quiet")
        def validate_quiet(cls, quiet):
            assert isinstance(quiet, bool), "Invalid type for quiet"

        @field_validator("temperature")
        def validate_temperature(cls, temperature):
            assert isinstance(temperature, float), "Invalid type for temperature"

        @field_validator("timeout")
        def validate_timeout(cls, timeout):
            assert isinstance(timeout, int), "Invalid type for timeout"

        @field_validator("max_iter")
        def validate_max_iter(cls, max_iter):
            assert isinstance(max_iter, int), "Invalid type for max_iter"

        @field_validator("tree")
        def validate_tree(cls, tree):
            assert isinstance(tree, bool), "Invalid type for tree"

    def __init__(self):
        self.previous_options = json.dumps({})

    def _configure(
            self,
            quiet,
            openaimodel,
            temperature,
            timeout,
            max_iter,
            tree,
            ):
        self.verbose = not quiet
        self.tree = tree

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
                verbose=self.verbose,
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
                max_execution_time=DEFAULT_TIMEOUT,
                max_iterations=DEFAULT_MAX_ITER
                )

    def execute(self, prompt, stream, response, conversation):
        question = prompt.prompt
        options = {
                "quiet": prompt.options.quiet or False,
                "openaimodel": prompt.options.openaimodel or DEFAULT_MODEL,
                "temperature": prompt.options.temperature or DEFAULT_TEMP,
                "timeout": prompt.options.timeout or DEFAULT_TIMEOUT,
                "max_iter": prompt.options.max_iter or DEFAULT_MAX_ITER,
                "tree": prompt.options.tree or DEFAULT_TREE,
                }
        if json.dumps(options) != json.dumps(self.previous_options):
            self._configure(**options)
        with get_openai_callback() as cb:
            try:
                if self.tree:
                    pass
                else:
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
