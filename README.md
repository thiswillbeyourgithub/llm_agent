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
