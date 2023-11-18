from tqdm import tqdm
from textwrap import dedent
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
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

DEFAULT_MODEL = "gpt-3.5-turbo-1106"
DEFAULT_TEMP = 0
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_ITER = 10
DEFAULT_TASKS = True


@llm.hookimpl
def register_models(register):
    register(WebSearch())

class WebSearch(llm.Model):
    VERSION = 0.3
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
        tasks: Optional[bool] = Field(
                description="True to use subtasks",
                default=DEFAULT_TASKS)

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

        @field_validator("tasks")
        def validate_tasks(cls, tasks):
            assert isinstance(tasks, bool), "Invalid type for tasks"

    def __init__(self):
        self.previous_options = json.dumps({})

    def _configure(
            self,
            quiet,
            openaimodel,
            temperature,
            timeout,
            max_iter,
            tasks,
            ):
        self.verbose = not quiet
        self.tasks = True #tasks

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

        if self.tasks:
            template = dedent("""
            I want to answer the question '{question}'. Please generate up to 5 steps needed to answer that question.
            Don't worry about intermediate steps seeming too complicated, we can subdivide them later on.
            If the question is already phrased as a series of steps, just rewrite into the appropriate format.
            ALWAYS answer using the appropriate format.

            APPROPRIATE FORMAT: one step per line, without enumeration.
            """)
            prompt = PromptTemplate(
                input_variables=["question"],
                template=template,
            )
            subtasker = LLMChain(
                llm=chatgpt,
                prompt=prompt,
                output_key="steps",
                verbose=self.verbose,
            )

            @tool
            def complicated(question: str) -> str:
                " If you have a task requiring multiple steps, use this tool and I'll give you the final answer."
                question = question.replace("The end goal it to answer this:", "").strip()
                steps = subtasker.run(question).splitlines()

                header = f"The end goal it to answer this: '{question}'.\n\n"
                header += "Here is the step planning:"
                print("Steps:")
                for i, step in enumerate(steps):
                    step = f"\n{i}. {step}. Answer: STEPANSWER"
                    header += step
                    print(step).strip()

                answers = []
                for i, step in tqdm(enumerate(steps), desc="Executing complicated task", unit="step"):
                    stepprompt = header
                    for ans in answers:
                        stepprompt = stepprompt.replace("Answer: STEPANSWER", ans, 1)
                    stepprompt = stepprompt.replace(" Answer: STEPANSWER", "").strip()

                    stepprompt += f"\n\nYour current task is '{step}'"

                    intermediate_answer = self.sub_agent.run(stepprompt)
                    answers.append(intermediate_answer)

                prompt = header
                for ans in answers:
                    prompt = prompt.replace("Answer: STEPANSWER", ans, 1)
                prompt += "\n\nNow please answer the initial question."
                final_answer = self.sub_agent.run(prompt)

                return final_answer

            self.sub_agent = initialize_agent(
                    self.tools,
                    chatgpt,
                    verbose=self.verbose,
                    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                    memory=memory,
                    handle_parsing_errors=True,
                    max_execution_time=DEFAULT_TIMEOUT,
                    max_iterations=DEFAULT_MAX_ITER
                    )
            additionnal_tools = [complicated]
        self.agent = initialize_agent(
                self.tools + additionnal_tools,
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
                "tasks": prompt.options.tasks or DEFAULT_TASKS,
                }
        if json.dumps(options) != json.dumps(self.previous_options):
            self._configure(**options)
        with get_openai_callback() as cb:
            try:
                answer = self.agent.run(question)
            except AskUser as err:
                answer = err.message

            print(f"\nToken so far: {cb.total_tokens} or ${cb.total_cost}")
        return answer

@tool
def userinput(question: str) -> str:
    "Talk with the user if no other tool is currently needed. Don't use it to ask question that could be answered using the search tools."
    raise AskUser(question)


class AskUser(Exception):
    def __init__(self, message):
        self.message = message
