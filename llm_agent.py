import textwrap
import sys
from datetime import datetime
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
from langchain.agents.agent_toolkits import FileManagementToolkit
from langchain.tools import ShellTool
from langchain.agents.agent_toolkits import PlayWrightBrowserToolkit
from langchain.tools.playwright.utils import create_sync_playwright_browser
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

DEFAULT_MODEL = "gpt-3.5-turbo-1106"
DEFAULT_TEMP = 0
DEFAULT_TIMEOUT = 240  # 4 minutes
DEFAULT_MAX_ITER = 50
DEFAULT_TASKS = True
DEFAULT_FILES = False
DEFAULT_SHELL = False


@llm.hookimpl
def register_models(register):
    register(Agent())

class Agent(llm.Model):
    VERSION = "0.3.0"
    model_id = "agent"
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
        user: Optional[str] = Field(
                description="If a string, should be the name of the user and will be used for persistent memory.",
                default=None)
        tavily_tool: Optional[bool] = Field(
                description="If True, will use tavily for search if an api key is supplied.",
                default=False)
        metaphor_tool: Optional[bool] = Field(
                description="If True, will use metaphor for search if an api key is supplied.",
                default=False)
        files_tool: Optional[bool] = Field(
                description="If True, will enable the file related tools. The tool 'delete_file' is disabled but be careful.",
                default=DEFAULT_FILES)
        shell_tool: Optional[bool] = Field(
                description="If True, will enable the tool to use the shell. Be careful.",
                default=DEFAULT_SHELL)

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

        @field_validator("tavily_tool")
        def validate_tavily_tool(cls, tavily_tool):
            assert isinstance(tavily_tool, bool), "Invalid type for tavily_tool"
            return tavily_tool

        @field_validator("metaphor_tool")
        def validate_metaphor_tool(cls, metaphor_tool):
            assert isinstance(metaphor_tool, bool), "Invalid type for metaphor_tool"
            return metaphor_tool

        @field_validator("files_tool")
        def validate_files_tool(cls, files_tool):
            assert isinstance(files_tool, bool), "Invalid type for files_tool"
            return files_tool

        @field_validator("shell_tool")
        def validate_shell_tool(cls, shell_tool):
            assert isinstance(shell_tool, bool), "Invalid type for shell_tool"
            return shell_tool

    def __init__(self):
        self.configured = False

        # if we qre certain that llm will use Agent then might as
        # well initialize it directly instead of waiting the first message
        if "agent" not in sys.argv:
            return
        try:
            args = " ".join(sys.argv[1:]).replace("-o", "--option")
            while args and not args.startswith("--option"):
                args = args[1:]
            options = {
                    "quiet": False,
                    "debug": False,
                    "openaimodel": DEFAULT_MODEL,
                    "temperature": DEFAULT_TEMP,
                    "timeout": DEFAULT_TIMEOUT,
                    "max_iter": DEFAULT_MAX_ITER,
                    "tasks": DEFAULT_TASKS,
                    "user": None,
                    "tavily_tool": False,
                    "metaphor_tool": False,
                    "files_tool": DEFAULT_FILES,
                    "shell_tool": DEFAULT_SHELL,
                    }
            for arg in args.split("--option"):
                arg = arg.strip()
                if not arg:
                    continue
                k, v = arg.split(" ")
                assert k in options, f"missing {k} from options?"
                if v.lower() == "false":
                    v = False
                elif v.lower() == "true":
                    v = True
                elif v.lower() == "none":
                    v = None
                elif v.isdigit():
                    if "." in v:
                        v = float(v)
                    else:
                        v = int(v)
                options[k] = v
            self._configure(**options)
        except Exception as err:
            print(f"Error when configuring early Agent: {err}")

    def _configure(
            self,
            quiet,
            debug,
            openaimodel,
            temperature,
            timeout,
            max_iter,
            tasks,
            user,
            tavily_tool,
            metaphor_tool,
            files_tool,
            shell_tool,
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

        # load llm
        chatgpt = ChatOpenAI(
                model_name=openaimodel,
                temperature=temperature,
                verbose=self.verbose,
                streaming=False,
                )

        # load some tools
        self.atools = []  # for self.agent
        self.satools = []  # for self.sub_agent

        self.atools += load_tools(["llm-math"], llm=chatgpt)
        self.atools += load_tools(["human"])

        self.satools += load_tools(["llm-math"], llm=chatgpt)
        self.satools += load_tools(["ddg-search"], llm=chatgpt)
        self.satools += load_tools(["wikipedia"], llm=chatgpt)
        self.satools += load_tools(["arxiv"], llm=chatgpt)
        self.satools += load_tools(["human"])

        # pubmed is a bit buggy at the moment
        # pubmed_tool = PubmedQueryRun()
        # pubmed_tool.description += f"args {pubmed_tool.args}".replace("{", "{{").replace("}", "}}")
        # self.satools += pubmed_tool

        if files_tool:
            toolkit = FileManagementToolkit(
                    selected_tools=[
                        "read_file",
                        "write_file",
                        "list_directory",
                        "file_search",
                        "move_file",
                        "copy_file",
                        # "delete_file",
                        ])
            self.atools += toolkit.get_tools()
            self.satools += toolkit.get_tools()

        if shell_tool:
            self.atools += ShellTool()
            self.satools += ShellTool()

        # init memories
        memory = ConversationBufferMemory(
                output_key="output",
                memory_key="chat_history",
                return_messages=True)
        # sub_memory = ConversationBufferWindowMemory(
        #         output_key="output",
        #         memory_key="chat_history",
        #         return_messages=True,
        #         k=2)

        if not user:
            # just tell the llm the date
            memory.chat_memory.add_user_message(
                f"Today's date is {datetime.now()}.")
        else:
            # load the date, name of user and previous memories
            memory.chat_memory.add_user_message(
                f"My name is {user} and today's date is {datetime.now()}.")

            # look for previous persisted memories
            llm_agent = llm.user_dir() / "agent"
            llm_agent.mkdir(exist_ok=True)
            self.user_memories = llm_agent / f"{user}.json"
            if not self.user_memories.exists():
                with open(self.user_memories.absolute(), "w") as file:
                    json.dump([], file)
            with open(self.user_memories.absolute(), "r") as file:
                memories = json.load(file)
                assert isinstance(memories, list), "Memories is not a list"
                messages = []
                for mem in memories:
                    assert isinstance(mem, dict), "Invalid type of memory"
                    assert "timestamp" in mem, "Memory missing timestamp key"
                    assert "message" in mem, "Memory missing message key"
                    mess = mem["message"]
                    assert mess, "Empty message in memory"
                    messages.append(mess)
                message = (f"Here are a few things you have to know:\n- " + "\n- ".join(messages)).strip()
                if self.verbose:
                    print(f"Loaded from memory: '{message}")
                memory.chat_memory.add_user_message(message)

            @tool
            def memorize(memory: str) -> str:
                """Use this ONLY if the user asks you to memorize an information
                persistently. I'll then make sure to store it somewhere for future use
                by you. Input must be the information the user wants you to memorize."""
                with open(self.user_memories.absolute(), "r") as file:
                    memories = json.load(file)
                    memories.append({
                            "timestamp": int(time.time()),
                            "message": memory,
                            })
                with open(self.user_memories.absolute(), "w") as file:
                    json.dump(memories, file)
                return f"I added the memory '{memory}' to persistent memory."

            self.atools.append(memorize)

        # add tavily search to the tools if possible
        if tavily_tool:
            tavily_key = llm.get_key(None, "tavily", env_var="TAVILY_API_KEY")
            os.environ["TAVILY_API_KEY"] = tavily_key
            if not tavily_key:
                print("No Tavily API key given, will only use duckduckgo for search.")
            else:
                # can only be loaded after the API key was set
                tavily_search = TavilySearchAPIWrapper()
                tavily_tool = TavilySearchResults(api_wrapper=tavily_search)
                self.atools.append(tavily_tool)

        # add metaphor only if available
        if metaphor_tool:
            metaphor_key = llm.get_key(None, "metaphor", env_var="METAPHOR_API_KEY")
            os.environ["METAPHOR_API_KEY"] = metaphor_key
            if not metaphor_key:
                print("No Metaphor API key given, will not use this search engine.")
            else:
                mtph = Metaphor(api_key=os.environ["METAPHOR_API_KEY"])

                @tool
                def metaphor_search(query: str) -> str:
                    """Advanced search using Metaphor. Use for advanced
                    topics or if the user asks for it."""
                    res = mtph.search(query, use_autoprompt=False, num_results=5)

                    output = "Here's the result of the search:"
                    for result in res.get_contents().contents:
                        html = result.extract
                        url = result.url
                        text = BeautifulSoup(html).get_text().strip()
                        output += f"\n- {url} :\n'''\n{text}\n'''\n"
                    output = output.strip()
                    return output

                self.atools.append(metaphor_search)

        # add browser toolkit
        self.browser = create_sync_playwright_browser()
        toolkit = PlayWrightBrowserToolkit.from_browser(sync_browser=self.browser)
        self.satools.extend(toolkit.get_tools())

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
                """If you have a task requiring multiple steps, use
                this tool. If the task is directly from the user: give
                me his exact instructions without any reformulation."""
                question = question.replace("The end goal it to answer this:", "").strip()
                steps = subtasker(question)["steps"].splitlines()

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
                        answerdict = self.sub_agent(stepprompt)
                    except Exception as err:
                        print(f"Error {err}, retrying after 2s")
                        time.sleep(2)
                        answerdict = self.sub_agent(stepprompt)
                        # intermediate_answer = self._validate_answer(stepprompt, intermediate_answer)

                    answers.append(answerdict["output"])
                    intermediate_stepanswers.append(answerdict["intermediate_steps"])

                prompt = header
                for ans in answers:
                    prompt = prompt.replace("STEPANSWER", ans, 1)
                prompt += "\n\nNow please answer the initial question."
                answerdict = self.sub_agent(prompt)
                answers.append(answerdict["output"])
                intermediate_stepanswers.append(answerdict["intermediate_steps"])

                final_answer = f"Assistant, return the complete following text as the final answer instead of just extracting the last few lines like you used to:\n'''\nI split the question into intermediate steps then tried to reason step by step.\nSteps:\n"
                for i, step in enumerate(steps):
                    step = f"\n{i+1}. {step}. Answer:\n"
                    step += textwrap.indent(answers[i], "    ")
                    step = step.replace(r"\\n", "\n")
                    final_answer += step
                final_answer += f"\nThe answer is: '{answers[-1]}'\n'''"

                return final_answer

            self.sub_agent = initialize_agent(
                    llm=chatgpt,
                    tools=self.satools,
                    verbose=self.verbose,
                    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                    # agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                    memory=memory,
                    handle_parsing_errors=True,
                    max_execution_time=DEFAULT_TIMEOUT,
                    max_iterations=DEFAULT_MAX_ITER,
                    return_intermediate_steps=True,
                    )

            # only add to the tools now so that sub_agent can't make recursive bigtask calls
            self.atools += [BigTask]

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
                llm=chatgpt,
                tools=self.atools,
                verbose=self.verbose,
                # agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                memory=memory,
                handle_parsing_errors=True,
                max_execution_time=DEFAULT_TIMEOUT,
                max_iterations=DEFAULT_MAX_ITER,
                return_intermediate_steps=True,
                )

        print(f"(Tools as the agent's disposal: {', '.join([t.name for t in self.atools])})")
        if tasks:
            print(f"(Tools at the disposal of BigTask's agent: {', '.join([t.name for t in self.satools])})")

        self.configured = True

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
                "user": prompt.options.user,
                "tavily_tool": prompt.options.tavily_tool,
                "metaphor_tool": prompt.options.metaphor_tool,
                "files_tool": prompt.options.files_tool,
                "shell_tool": prompt.options.shell_tool,
                }

        if not self.configured:
            self._configure(**options)

        with get_openai_callback() as cb:
            answerdict = self.agent(question)

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
