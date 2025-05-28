# Agent

## About

**Agent** is a simple wrapper for enabling agentic systems using the OpenAI and Llama.Cpp REST APIs.

> **Note:** This is an experimental, personal toy project. Not intended for production use—expect rough edges!

## Setup

You’ll need to clone the project for now:

```sh
git clone https://github.com/teleprint-me/agent.git agent
cd agent
```

You can also use `pip` to install the package locally:

```sh
pip install git+https://github.com/teleprint-me/agent
```

Python **3.12.x** is recommended for stability and compatibility with most ML tooling.
This lets other tools catch up to Python 3.13+ while keeping your environment reliable.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

- _Tip:_

  - Avoid pinning dependencies during early development.
  - For a stable setup, freeze requirements with:
    `pip freeze > requirements.lock.txt`

## Dependencies

Dependencies are intentionally minimal:

- **Python 3.12+** — Stable baseline
- **OpenAI** and **gguf** — Model compatibility (OpenAI + local LLMs)
- **Prompt Toolkit** and **Pygments** — CLI and theming for the console
- **Tkinter** and **ttkbootstrap** — GUI and theming for the editor
- **jsonpycraft**, **dotenv**, **peewee**, etc. — Planned config and utility tools

Other utilities are included but not fully integrated yet.

## Usage

If using the llama.cpp server backend, ensure you start it with the correct flags to enable templates, functions, and pooling:

```sh
llama-server \
    --port 8080 \
    --n-gpu-layers 32 \
    --ctx-size 16384 \
    --pooling mean \
    --slots --jinja -fa \
    -m /path/to/ggml-model-f16.gguf
```

Set up a `.env` file for your API connection:

```sh
touch .env
```

Add the following environment variables:

```env
OPENAI_API_KEY=sk-no-key-required
OPENAI_BASE_URL=http://localhost:8080/v1
```

### Launch

- **CLI:**

  ```sh
  python -m agent.cli
  ```

The text user interface should appear.

- **GUI:**

  ```sh
  python -m agent.gui
  ```

The editor window should appear.

- **Config:**

A simple CLI tool is included for customizing agent and model settings. For help:

```sh
python -m agent.config -h
```

Configuration is managed via `jsonpycraft` for clean, editable JSON-based settings.

## Implementation Notes

- The **GUI** is currently minimal—just a styled window with basic file actions (open, close, new, save, save as) and simple tabs.
  No real “agent” features yet; it’s a skeleton to build on.
- The **CLI** is getting most of the early development attention.
  Once the CLI matures, focus will shift to the GUI.
- The priority is to make the core API as _agnostic_ as possible, so both the CLI and GUI can share the same backend logic.
- Current work is focused on the basics: streaming, tool calling, reasoning, configuration, chat loop cycle, and simple input.

It’s a moving target. Expect frequent changes, bugs, and some questionable design decisions (at least until it all clicks together).

## Resources

- [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [OpenAI API](https://platform.openai.com/docs/api-reference/introduction)
- [jsonpycraft](https://github.com/teleprint-me/json-py-craft/tree/main/docs)
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/index.html)
- [Tkinter](https://docs.python.org/3/library/tkinter.html)
- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/en/latest/)

## License

Licensed under the **AGPL** to ensure the code remains free and publicly available.
This guarantees user freedom while protecting against closed-source forks.
