# Agent

## About

A simple wrapper for enabling agentic systems using the OpenAI REST API.  
Includes a minimal, Tkinter-based text editor for interacting with programmable agents using OpenAI and Llama.Cpp backends.

> **Note:** This is a personal toy project. It's experimental and not intended for production use.

## Setup

I'm using **Python 3.12.x** for stability, as most ML tooling is compatible with it.  
This gives other tools time to catch up to Python 3.13+ while keeping my environment reliable.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

I avoid pinning package versions during active development.
For stability, generate a frozen requirements file (`pip freeze > requirements.lock.txt`).

## Dependencies

Dependencies are intentionally minimal:

- `Python 3.12+` — Stable baseline
- `OpenAI` and `gguf` — Language model compatibility (OpenAI + local LLMs)
- `Tkinter` and `TtkBootstrap` — GUI and theming support for the editor
- `jsonpycraft`, `dotenv`, etc. — Configuration tools (planned use)

A few utilities are included but not fully integrated yet.

## Usage

Once installed, launch the CLI with:

```sh
python -m agent.cli
```

Or you can launch the GUI with:

```sh
python -m agent.gui
```

The editor should appear.

_**NOTE:** The CLI uses [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/index.html) and the GUI uses [tkinter](https://docs.python.org/3/library/tkinter.html)_.

## Notes

The goal is to build a **custom, extensible editor** that fits my personal workflow.
At the moment, it’s barely functional — just enough to test ideas and establish a foundation.

The agent layer depends on experimental LLaMA.cpp integration and OpenAI APIs.
Some features are unstable or under active development.

Expect broken things, weird output, and a lot of duct tape.

## License

Licensed under the **AGPL** to ensure the code remains free and publicly available.
This guarantees user freedom while protecting against closed forks.
