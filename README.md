# llm_agent
Plugin for [llm](https://llm.datasette.io/) by the great [simonw](https://simonwillison.net/) to add a simple langchain agent.

## Features
* Multiple search engines: duckduckgo, metaphor, tavily, wikipedia, pubmed, arxiv etc.
* Browser tool: use playwright to browse the internet autonomously.
* Math tool: calculator included
* BigTask: a tool used to autonomously split a task into subtasks
* Shell: you can opt in to give the llm access to your shell.
* Files: you can opt in to give the llm access to your files. This is super handy for things like "Modify VAE.py to add docstrings, also add GPU compatibility and add tests."
* Wallet safe: there is a timeout and recursion limit to avoid too high costs. Also the number of token used so far is displayed.
* Persistent memory: if you use the `user` argument, you can just ask the LLM to memorize something (for example "I want you to memorize that I'm a computer science engineer." or "I want you to memorize that my prefer search engine for people related question is duckduckgo.")

## Current tools available
* agent
    * llm-math (calculator)
    * human (meaning it can decide to ask you for stuff)
    * BigTask (ability to call sub_agent to split the task into many subtasks, each subtask has access to the tools of sub_agent)
    * files (optional, read, write, list, search, move, copy)
    * shell (optional, any command)
    * memorize (optional, if 'user' argument is set this will be used to store information about the user if explicitly asked to remember it)

* sub_agent (= almost the same as agent but is called to handle subtasks created by BigTask and does not have access to BigTask itself, making infinite recursion using BigTask impossible)
    * llm-math
    * human
    * search related:
        * browser tools (it can use playwright to navigate the web autonomously)
        * ddg-search (quick answers via duckduckgo, no API required)
        * tavily (optional, a search engine friendly to LLM, API key is required)
        * metaphor (optional, a search engine friendly to LLM, API key is required)
        * wikipedia (quick answers via wikipedia, not the whole article)
        * arxiv
        * pubmed (buggy at the moment)
    * files (if enabled)
    * shell (if enabled)

**Note that if the arugment task_tool is set to False, BigTask tool will not appear and all tools of the sub_agent will be given to the agent instead.**

## Things I used it for
* Using the BigTask tool: make it search information about bioaccumulation in salmon and in tuna to compare which is worst.
* Using the files tool: make it modify a python code to implement various enhancement (worked incredibly well!)

## How to
* to install: `llm install llm-agent-plugin`
* to run: `llm chat -m agent`
* Very early stage, done mostly while procrastinating work. Will improve a lot.


## TODO
* find a way to implement streaming of tokens
* many more to come. This is highly experimental and will be substantially improved
