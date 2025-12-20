# Agent

## About

**Agent** is a frontend CLI client for the llama.cpp REST API.

**Note:** This is a personal toy project. I'm not expecting this to go anywhere
special.

## Layout

I'm currently in the process of merging older projects together directly into
this one. Some modules may be entirely or partially broken. Some dependencies
have issues.

The primary sub-packages are:

- cli: The main program.
- config: Automated configuration.
- llama: Core llama-server wrapper.
- hf: Huggingface hub wrapper.
- text: Text extraction utilities.
- tools: Tools available to models.
- examples: Usually where I prototype modules.

## Future Plans

- Automate llama.cpp setup and installation.
- Automate model download and quantization.
- Enable easy modification of application settings.
- Refine support for tool-calling.
- Add a basic vim-like text editor.
- Add dynamic syntax highlighting.
- Add basic auto-complete, fim, and chat support.
- Add dynamic retrieval augmented generation.
- Enable hot-swapping models for memory constrained environments.
- And more.

I have a lot of ideas, but I have no idea how I'm going to go about it. I'm
just experimenting as I go.

## Setup

### Agent

Agent is still under active development and is **not** intended for general
installation yet. While it is possible to use it locally, this is not
recommended at the moment.

Agents are autonomous and may continue running actions until interrupted. Treat
this project as a development tool, not a production-ready package.

No special package manager or environment tooling is required - `venv` keeps
the setup simple and predictable.

### Cloning

First clone the repository from source.

```sh
git clone https://github.com/teleprint-me/agent.git teleprint-me/agent
cd teleprint-me/agent
```

Then create and install the development environment.

> It's good practice to review scripts before executing them.
> You're encouraged to review the contents of requirements.sh script and its dependencies.

```sh
chmod +x requirements.sh
./requirements.sh
```

This will install the required dependencies for agent.

### llama.cpp

Agent depends on the **llama.cpp** backend. You must install it to enable the
agentic workflow.

`ggml-org` provides prebuilt binaries for common platforms, and some Linux
distributions (e.g., Arch Linux) offer packages through their package managers.
However, building from source is straightforward and gives you full control
over backend support (CUDA, ROCm, Vulkan, etc.).

Agent specifically relies on the **`llama-server`** binary.

See [scripts](scripts) for more information.
Setup instructions can be found in the provided [README.md](scripts/README.md).

> Vulkan is recommended because it works across **NVIDIA, AMD, and Intel**,
> including older cards such as the RX 580.

Ensure the llama-server binary is available from your system path.

```sh
command -v llama-server
```

You should see the absolute path to the binary.

### model downloads

Both **huggingface-hub** and **llama-server** hide downloaded weights behind an
internal cache path. The directories are hashed, symlinked, and usually live
inside the user’s home directory. This makes it hard to track where weights
actually end up, and models can silently consume large amounts of disk space
over time.

If you rely on the built-in auto-download behavior, expect:

- Model files stored in hidden, hashed subdirectories
- No control over the destination path
- Potentially huge storage usage (10TB fills _fast_ when experimenting)

#### Recommended approach

Download weights yourself and store them exactly where you want them. This
avoids cache sprawl and keeps your environment transparent.

- Download vendor-released weights directly
- Quantize locally when possible
- Keep weights in a predictable, human-readable directory structure
- Avoid auto-download flags unless you know what they’re doing

`ggml-org` is safe to download from, but get the files manually instead of
relying on Hugging Face’s cache mechanism.

#### Agent’s huggingface-hub wrapper

The agent includes a convenience wrapper around `huggingface-hub` that:

- bypasses hashed cache paths
- writes weights to a user-specified directory
- exposes a simple CLI for inspecting and downloading models

No more digging through obscure HF cache directories.

Help:

```sh
python -m agent.hf --help
```

Download help:

```sh
python -m agent.hf download --help
```

#### Authentication (gated models)

Some vendor models require authentication. Create a `.env` file:

```sh
touch .env
echo HUGGINGFACE_READ_API=your-token-here >> .env
```

Tokens:
[https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

#### Example: Download a model

```sh
python -m agent.hf download \
    -e .env \
    -t model \
    -i openai/gpt-oss-20b \
    -p /mnt/models/openai/gpt-oss-20b
```

Grab a coffee - some models are large.

#### Recommended Sources

Choose weights based on bandwidth, VRAM, and whether you prefer to quantize
locally.

#### Pre-quantized weights (GGUF, etc.)

- [ggml-org](https://huggingface.co/ggml-org)

#### Raw, vendor-official weights

- [openai](https://huggingface.co/openai)
- [meta-llama](https://huggingface.co/meta-llama)
- [google](https://huggingface.co/google)
- [mistralai](https://huggingface.co/mistralai)
- [Qwen](https://huggingface.co/Qwen)
- [jinaai](https://huggingface.co/jinaai)

#### FIM (fill-in-the-middle) models

- [Qwen/qwen25-coder](https://huggingface.co/collections/Qwen/qwen25-coder)
- [Qwen/qwen3-coder](https://huggingface.co/collections/Qwen/qwen3-coder)

#### Agentic models

- [openai/gpt-oss](https://huggingface.co/collections/openai/gpt-oss)
- [meta-llama/llama-32](https://huggingface.co/collections/meta-llama/llama-32)
- [Qwen/qwen3](https://huggingface.co/collections/Qwen/qwen3)

#### Embedding models

- [Qwen/qwen3-embedding](https://huggingface.co/collections/Qwen/qwen3-embedding)
- [google/embeddinggemma](https://huggingface.co/collections/google/embeddinggemma)
- [jinaai/collections](https://huggingface.co/jinaai/collections)

Pick a model that supports the features required by your task - otherwise
you’ll see degraded performance.

### Quantization

llama.cpp includes a Python-based utility for converting vendor-released model
weights into GGUF format and applying quantization. This step is required
before Agent can run any model locally.

Because the conversion script lives inside the llama.cpp repository, you must
have llama.cpp installed **before** performing these steps.

### Convert vendor weights to GGUF

Before converting, download the raw vendor weights (see the Hugging Face
section). Once you have the model directory, you can invoke the converter.

Help:

```sh
convert_hf_to_gguf.py -h
```

Example conversion:

```sh
convert_hf_to_gguf.py \
    /mnt/models/openai/gpt-oss-20b \
    --outfile /mnt/models/openai/gpt-oss-20b/ggml-model-f16.gguf \
    --outtype f16
```

You can further quantize the model. GPT-OSS supports MXFP4 and was tuned with FP4 QAT.

```sh
llama-quantize \
    /mnt/models/openai/gpt-oss-20b/ggml-model-f16.gguf \
    /mnt/models/openai/gpt-oss-20b/ggml-model-f4.gguf \
    MXFP4_MOE
```

Your GGUF weights are now ready for use with `llama-server`.

### Config

Agent automatically generates a local configuration and cache directory. Right
now the cache path is fixed, but future versions will allow custom paths.

The configuration system initializes the agent with sensible defaults, and you
can modify any of the settings through the CLI.

#### Configuration CLI

Show help:

```sh
python -m agent.config -h
```

You can **view**, **set**, **list**, or **reset** configuration keys. Any
interaction will create the `.agent` directory, which contains:

```sh
tree .agent
.agent
├── history.log         # prompt/input history
├── messages.json       # recent chat history
├── model.log           # model/server logs
├── settings.json       # configuration settings
└── storage.sqlite3     # agent storage database

1 directory, 5 files
```

#### Resetting configuration & cache

During development, you may need to clear the `.agent` directory to avoid
conflicts between versions or stale state.

```sh
rm -rf .agent
```

If something behaves unexpectedly, wiping this folder is the first thing to
try - it has been the most common source of issues during development.

### tools

The agent exposes a small, intentionally restricted set of tools. These
limitations are by design. They help prevent uncontrolled behavior while still
enabling autonomous workflows.

The available tools are:

- **shell** An allow-listed command runner. Only approved commands may be
  executed. Piping is disabled for now, though it may be enabled later for
  advanced models.

- **read** Read arbitrary slices of a file.

- **write** Write or modify slices of a file.

- **memories** Create, update, recall, and delete stored memories. These form
  the agent’s persistent knowledge base.

#### Tool chaining

The model can chain tool calls during a single objective. Once you give the
agent a task, it is allowed to operate autonomously, issuing tool calls one
after another, until it determines the objective is complete.

After the task is finished, control is returned to you.

### usage

Agent is still in its early stages, and only the core functionality is
implemented. The interface is simple, and the workflow revolves around the CLI
utility.

#### Getting help

```sh
python -m agent.cli -h
```

This displays all available runtime options: model path, backend flags, context
size, metrics, Jinja templating, embedding mode, pooling modes, and more.

#### Running the program

Agent automatically launches and manages a `llama-server` instance. You do
**not** need to start the server manually.

Example:

```sh
python -m agent.cli --jinja --model /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf
```

On startup:

1. The CLI spawns `llama-server` with your selected features
2. It waits for the server to become ready
3. It registers the server PID
4. It launches the interactive agent interface
5. On exit, it attempts to terminate the server process

If an internal error interrupts this workflow, a zombie `llama-server` process
may remain. This is a known limitation in the current implementation.

#### Cleaning up zombie processes

Identify:

```sh
ps aux | grep ${USER} | grep llama-server
```

Kill:

```sh
kill <pid>
```

A future version will automatically track and stop orphaned processes, but this
is currently manual.

#### Keyboard shortcuts

These keybindings control the interactive prompt:

- `enter` – Insert a newline
- `alt+enter` – Submit the message
- `backspace` – Standard behavior
- `alt+f` – Autocomplete current token
- `alt+e` – Autocomplete to end of line
- `ctrl+d` – Pop a message from the sequence
- `ctrl+c` – Quit and kill the server
- `ctrl+a` – Move cursor to start of line
- `ctrl+e` – Move cursor to end of line
- `ctrl+k` – Cut from cursor to end
- `ctrl+u` – Cut from cursor to start
- `ctrl+y` – Paste the last cut text

These provide a lightweight REPL-like editing experience.

#### Using the model effectively

You can command the model directly, but don’t assume it always interprets
instructions correctly. The best results come from treating the agent as a
collaborative partner, not a fully autonomous worker.

Models differ in alignment, conditioning, and safety tuning. Some heavily steer
output while others behave more freely. Adjust your prompting style to match
the model you’re using.

The most reliable workflow is:

1. Start small
2. Inspect model output
3. Gradually introduce structure
4. Iterate with the agent as you build the project

This avoids "vibe coding" and keeps the process grounded in real design
decisions.

#### Example workflow

Below is a typical startup sequence showing cache creation, model loading, and
an initial interaction:

```sh
rm -rf .agent

python -m agent.cli \
    --metrics \
    --jinja \
    --model /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf \
    --ctx-size 16384
```

Sample output (truncated):

```
llama-server --port 8080 --ctx-size 16384 --n-gpu-layers 99 ...
waiting for server
Process id 158156
Model Name gpt-oss-20b
Model Path /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf
Vocab Size 201088
Seq Len 16384/131072
Created cache: .agent/messages.json

system
My name is ChatGPT. I am a helpful assistant.

> Hello! My name is Austin. What is your name?
```

Once running, the model can:

- **reason**
- **use tools**
- **read/write files**
- **store/retrieve memories**
- **operate in autonomous chains**

That’s the full loop: start server -> start agent -> think -> act -> respond ->
exit cleanly.

### Editor

The editor is an early prototype that’s still a work‑in‑progress and not yet
functionally useful.

If you’d like to try it, run:

```bash
python -m agent.editor
```

Press **Ctrl + Q** to exit.

#### Current state

- **Syntax highlighting** – auto‑detects the file type.
- **Indentation** – tab key inserts a tab, Shift‑Tab removes indentation.
- **Selection editing** – can tab or reverse‑tab a block of text.

All other features are under development.

The goal is to create a lightweight, VS Code‑like editor that leverages PTK3’s
strengths while adding ergonomic functionality.

## Contributions

I'm open to ideas and contributions. Feel free to open an issue or pull
request. Authors of PRs must understand the code. If they do not understand the
code, the PR will be closed with no further deliberation.

## Resources

- [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [jsonpycraft](https://github.com/teleprint-me/json-py-craft/tree/main/docs)
- [Pygments](https://pygments.org/docs/)
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/index.html)

Note that there is no need for fancy tools like Rich. Pygments and
prompt-toolkit should be sufficient for most of the desired features.

## License

AGPL to ensure end-user freedom.
