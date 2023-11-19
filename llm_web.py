from bs4 import BeautifulSoup
import time
from tqdm import tqdm
from textwrap import dedent
import json
import llm
import click
import os
from typing import Optional
from pydantic import field_validator, Field

from langchain.globals import set_verbose, set_debug
from langchain.agents import load_tools
from langchain.agents.initialize import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import get_openai_callback
from langchain.tools import tool
from langchain.tools import PubmedQueryRun
from langchain.tools.tavily_search import TavilySearchResults
from langchain.utilities.tavily_search import TavilySearchAPIWrapper

from metaphor_python import Metaphor

memory = ConversationBufferMemory(output_key="output", memory_key="chat_history", return_messages=True)
sub_memory = ConversationBufferWindowMemory(output_key="output", memory_key="chat_history", return_messages=True, k=2)

DEFAULT_MODEL = "gpt-3.5-turbo-1106"
DEFAULT_TEMP = 0
DEFAULT_TIMEOUT = 120
DEFAULT_MAX_ITER = 100
DEFAULT_TASKS = False


@llm.hookimpl
def register_models(register):
    register(WebSearch())

class WebSearch(llm.Model):
    VERSION = 0.7
    model_id = "web"
    can_stream = False

    class Options(llm.Options):
        quiet: Optional[bool] = Field(
                description="Turn off verbosity of the agent",
                default=False)
        debug: Optional[bool] = Field(
                description="Turn on langchain debug mode",
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
            return quiet

        @field_validator("debug")
        def validate_debug(cls, debug):
            assert isinstance(debug, bool), "Invalid type for debug"
            return debug

        @field_validator("temperature")
        def validate_temperature(cls, temperature):
            assert isinstance(temperature, float), "Invalid type for temperature"
            return temperature

        @field_validator("timeout")
        def validate_timeout(cls, timeout):
            assert isinstance(timeout, int), "Invalid type for timeout"
            return timeout

        @field_validator("max_iter")
        def validate_max_iter(cls, max_iter):
            assert isinstance(max_iter, int), "Invalid type for max_iter"
            return max_iter

        @field_validator("tasks")
        def validate_tasks(cls, tasks):
            assert isinstance(tasks, bool), "Invalid type for tasks"
            return tasks

    def __init__(self):
        self.previous_options = json.dumps({})

    def _configure(
            self,
            quiet,
            debug,
            openaimodel,
            temperature,
            timeout,
            max_iter,
            tasks,
            ):
        self.verbose = not quiet
        set_verbose(self.verbose)
        set_debug(debug)

        self.tasks = tasks

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

        metaphor_key = llm.get_key(None, "metaphor", env_var="METAPHOR_API_KEY")
        if not metaphor_key:
            print("No Metaphor API key given, will not use this search engine.")
        os.environ["METAPHOR_API_KEY"] = metaphor_key

        chatgpt = ChatOpenAI(
                model_name=openaimodel,
                temperature=temperature,
                verbose=self.verbose,
                streaming=False,
                )

        self.tools = load_tools(
                [
                    "ddg-search",
                    "wikipedia",
                    "llm-math",
                    "arxiv",
                    # "python_repl",  # part of experimental langchain
                    "requests_get",
                    ],
                llm=chatgpt)

        self.tools.append(PubmedQueryRun())

        # add tavily search to the tools if possible
        try:
            # can only be loaded after the API key was set
            tavily_search = TavilySearchAPIWrapper()
            tavily_tool = TavilySearchResults(api_wrapper=tavily_search)
            self.tools.append(tavily_tool)
        except Exception:
            pass

        # add metaphor only if available
        try:
            mtph = Metaphor(api_key=os.environ["METAPHOR_API_KEY"])
            @tool
            def metaphor_search(query: str) -> str:
                dedent("""Advanced search using Metaphor. Use for advanced
                topics or if the user asks for it.""")
                res = mtph.search(query, use_autoprompt=False, num_results=5)

                output = "Here's the result of the search:"
                for result in res.get_contents().contents:
                    html = result.extract
                    url = result.url
                    text = BeautifulSoup(html).get_text().strip()
                    output += f"\n- {url} :\n'''\n{text}\n'''\n"
                output = output.strip()
                return output

            self.tools.append(metaphor_search)
        except Exception:
            pass

        if self.tasks:
            template = dedent("""
            At the end, I want to answer the question '{question}'. Your task is to generate a few intermediate steps needed to answer that question. Don't create steps that are too vague or that would need to be broken down themselves.
            The number of steps should ideally be 3 to 5, but can be up to 10 if the question specifically asks for an indepth search.
            If the question is already phrased as a series of steps, just rewrite into the appropriate format.
            Use your tools to answer the question.

            ALWAYS answer using the appropriate format.
            APPROPRIATE FORMAT: one step per line, without enumeration.

            Example of format:
            ```
            Find the name of the owner of MacDonald's
            Find his age
            Multiply it by 4
            Return the answer
            ```

            Your turn now:
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
            def BigTask(question: str) -> str:
                dedent("""If you have a task requiring multiple steps, use
                this tool. If the task is directly from the user: give
                me his exact instructions without any reformulation.""")
                question = question.replace("The end goal it to answer this:", "").strip()
                steps = subtasker(question).splitlines()

                header = f"The end goal it to answer this: '{question}'.\n\n"
                header += "Here is the task planning:"
                for i, step in enumerate(steps):
                    step = f"\n{i+1}. {step}. Done: 'STEPANSWER'"
                    header += step

                answers = []
                intermediate_stepanswers = []
                for i, step in tqdm(enumerate(steps), desc="Executing complicated task", unit="step"):
                    stepprompt = header
                    for ans in answers:
                        stepprompt = stepprompt.replace("STEPANSWER", ans, 1)
                    stepprompt = stepprompt.replace("Done: 'STEPANSWER'", "TODO", 1).strip()
                    stepprompt = stepprompt.replace("Done: 'STEPANSWER'", "LATER").strip()

                    stepprompt += f"\n\nYour current task is #{i+1}"
                    print(stepprompt)

                    try:
                        intermediate_answer, intermediate_substeps = self.sub_agent(stepprompt)
                    except Exception as err:
                        print(f"Error {err}, retrying after 2s")
                        time.sleep(2)
                        intermediate_answer, intermediate_substeps = self.sub_agent(stepprompt)
                        # intermediate_answer = self._validate_answer(stepprompt, intermediate_answer)

                    answers.append(intermediate_answer)
                    intermediate_stepanswers.append(intermediate_substeps)

                prompt = header
                for ans in answers:
                    prompt = prompt.replace("STEPANSWER", ans, 1)
                prompt += "\n\nNow please answer the initial question."
                answer, intermediate_substeps = self.sub_agent(prompt)
                answers.append(answer)
                intermediate_stepanswers.append(intermediate_substeps)

                final_answer = f"Assistant, return the complete following text as the final answer instead of just extracting the last few lines like you used to:\n'''\nI split the question into intermediate steps then tried to reason step by step.\nSteps:\n"
                for i, step in enumerate(steps):
                    step = f"\n{i+1}. {step}. Answer: '{answers[i]}'"
                    final_answer += step
                final_answer += f"\nThe answer is: '{answers[-1]}'\n'''"

                return final_answer

            self.sub_agent = initialize_agent(
                    self.tools, # + [BigTask],  # don't allow recursive call to BigTask
                    chatgpt,
                    verbose=self.verbose,
                    # agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                    memory=sub_memory,
                    handle_parsing_errors=True,
                    max_execution_time=DEFAULT_TIMEOUT,
                    max_iterations=DEFAULT_MAX_ITER,
                    return_intermediate_steps=True,
                    )

        template = dedent("""
        Given a question and an answer, your task is to check the apparent validity of the answer.
        If the answer seems correct: answer 'VALID:'
        In any other situation: answer in the format 'INVALID:REASON' replacing REASON by a brief explanation.

        ALWAYS answer using the appropriate format.
        APPROPRIATE FORMAT: either 'VALID:' or 'INVALID:REASON'

        Example of valid output: 'VALID:'
        Example of invalid output: 'INVALID:Michelle Obama is not the Prime minister of the UK'

        Your turn now:

        Here's the answer:
        '''
        {answer}
        '''

        Here's the question:
        '''
        {question}
        '''
        """)
        prompt = PromptTemplate(
            input_variables=["question", "answer"],
            template=template,
        )
        self.validity_checker = LLMChain(
            llm=chatgpt,
            prompt=prompt,
            output_key="check",
            verbose=self.verbose,
        )

        self.agent = initialize_agent(
                self.tools + [BigTask, userinput],  # notably: userinput is not available to the sub_agent currently
                chatgpt,
                verbose=self.verbose,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                memory=memory,
                handle_parsing_errors=True,
                max_execution_time=DEFAULT_TIMEOUT,
                max_iterations=DEFAULT_MAX_ITER,
                return_intermediate_steps=True,
                )

        if self.verbose:
            print(f"(Tools as the agent's disposal: {', '.join([t.name for t in self.tools])})")

    def execute(self, prompt, stream, response, conversation):
        question = prompt.prompt
        options = {
                "quiet": prompt.options.quiet,
                "debug": prompt.options.debug,
                "openaimodel": prompt.options.openaimodel,
                "temperature": prompt.options.temperature,
                "timeout": prompt.options.timeout,
                "max_iter": prompt.options.max_iter,
                "tasks": prompt.options.tasks,
                }
        if json.dumps(options) != json.dumps(self.previous_options):
            self._configure(**options)
        with get_openai_callback() as cb:
            try:
                answerdict = self.agent(question)
            except AskUser as err:
                answerdict = {"output": err.message, "intermediate_steps": []}

            if self.verbose:
                print(f"\nToken so far: {cb.total_tokens} or ${cb.total_cost}")
        if answerdict["intermediate_steps"]:
            full_answer = "Intermediate steps:\n"
            for i, s in enumerate(answerdict["intermediate_steps"]):
                full_answer += f"* {i+1}: {s}\n"
            full_answer += f"\n-> {answerdict['output']}"
            return full_answer
        else:
            return answerdict["output"]

    def _validate_answer(self, question, answer, depth=0):
        try:
            check = self.validity_checker(question=question, answer=answer)
            if self.verbose:
                print(f"Validity checker output: {check}")

            assert ":" in check, f"check is missing: '{check}'"
            state = check.split(":")[0]
            reason = ":".join(check.split(":")[1:])
            assert state in ["VALID", "INVALID"], f"Invalid state: '{state}'"

            if state == "INVALID":
                new_answer = self.agent(
                        f"Try again another way because your answer seems invalid: {reason}")
                if depth >= 1:
                    return new_answer
                else:
                    # recursive call:
                    return self._validate_answer(question, new_answer, depth+1)
            else:
                return answer
        except Exception as err:
            print(f"Error when checking validity: '{err}'")

@tool
def userinput(question: str) -> str:
    "Talk with the user if no other tool is currently needed. Don't use it to ask question that could be answered using the search tools."
    raise AskUser(question)


class AskUser(Exception):
    def __init__(self, message):
        self.message = message
