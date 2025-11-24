# Agent

## About

**Agent** is a frontend CLI client for the llama.cpp REST API.

**Note:** This is a personal toy project.
I'm not expecting this to go anywhere special.

## Layout

I'm currently in the process of merging older projects together directly into this one. Some modules may be entirely or partially broken. Some dependencies have issues.

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

I have a lot of ideas, but I have no idea how I'm going to go about it. I'm just experimenting as I go.

## Setup

### llama.cpp

Agent depends on the **llama.cpp** backend. You must install it to enable the agentic workflow.

`ggml-org` provides prebuilt binaries for common platforms, and some Linux distributions (e.g., Arch Linux) offer packages through their package managers. However, building from source is straightforward and gives you full control over backend support (CUDA, ROCm, Vulkan, etc.).

Agent specifically relies on the **`llama-server`** binary.

### Install from source

Create a local workspace:

```sh
mkdir -p /mnt/source/cpp
git clone https://github.com/ggml-org/llama.cpp /mnt/source/cpp/llama.cpp
cd /mnt/source/cpp/llama.cpp
```

Then build from source:

```sh
cmake -B build -DCMAKE_BUILD_TYPE=Debug \
      -DGGML_DEBUG=0 \
      -DBUILD_SHARED_LIBS=1 \
      -DGGML_VULKAN=1

cmake --build build -j $(nproc)
```

Vulkan is recommended because it works across **NVIDIA, AMD, and Intel**, including older cards such as the RX 580.

### Add `llama-server` to your PATH

```sh
cd ~
echo "export PATH=${PATH}:/mnt/source/cpp/llama.cpp/build/bin" >> ~/.bashrc
```

If you use `zsh` or another shell, add the same line to the appropriate rc file.
Restart your shell and verify:

```sh
which llama-server
```

You should see the absolute path to the binary.

### Quantization

llama.cpp includes a Python-based utility for converting vendor-released model weights into GGUF format and applying quantization. This step is required before Agent can run any model locally.

Because the conversion script lives inside the llama.cpp repository, you must have llama.cpp installed **before** performing these steps.

### Setup the conversion environment

The conversion utilities require a small Python environment:

```sh
cd /mnt/source/cpp/llama.cpp
python -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Quantization runs entirely on the **CPU**.
There is **no benefit** to quantizing on a GPU - system memory is usually larger than VRAM and avoids out-of-memory issues.

### Convert vendor weights to GGUF

Before converting, download the raw vendor weights (see the Hugging Face section). Once you have the model directory, you can invoke the converter.

Help:

```sh
python convert_hf_to_gguf.py -h
```

Example conversion:

```sh
python convert_hf_to_gguf.py \
    /mnt/models/openai/gpt-oss-20b \
    --outtype q8_0 \
    --outfile /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf
```

Once the conversion completes, you can leave the virtual environment:

```sh
deactivate
cd ~
```

Your GGUF weights are now ready for use with `llama-server`.

### agent

Agent is still under active development and is **not** intended for general installation yet. While it is possible to use it locally, this is not recommended at the moment.

Agents are autonomous and may continue running actions until interrupted. Treat this project as a development tool, not a production-ready package.

### Clone the repository

```sh
mkdir -p /mnt/source/python
git clone https://github.com/teleprint-me/agent /mnt/source/python/agent
cd /mnt/source/python/agent
```

### Create a Python environment

Use a dedicated virtual environment to isolate the agent’s dependencies:

```sh
python -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
```

No special package manager or environment tooling is required - `venv` keeps the setup simple and predictable.

### model downloads

Both **huggingface-hub** and **ggml-org** hide downloaded weights behind an internal cache path. The directories are hashed, symlinked, and usually live inside the user’s home directory. This makes it hard to track where weights actually end up, and models can silently consume large amounts of disk space over time.

If you rely on the built-in auto-download behavior, expect:

* Model files stored in hidden, hashed subdirectories
* No control over the destination path
* Potentially huge storage usage (10TB fills *fast* when experimenting)

#### Recommended approach

Download weights yourself and store them exactly where you want them.
This avoids cache sprawl and keeps your environment transparent.

* Download vendor-released weights directly
* Quantize locally when possible
* Keep weights in a predictable, human-readable directory structure
* Avoid auto-download flags unless you know what they’re doing

`ggml-org` is safe to download from, but get the files manually instead of relying on Hugging Face’s cache mechanism.

#### Agent’s huggingface-hub wrapper

The agent includes a convenience wrapper around `huggingface-hub` that:

* bypasses hashed cache paths
* writes weights to a user-specified directory
* exposes a simple CLI for inspecting and downloading models

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

Tokens: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

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

Choose weights based on bandwidth, VRAM, and whether you prefer to quantize locally.

#### Pre-quantized weights (GGUF, etc.)

* [ggml-org](https://huggingface.co/ggml-org)

#### Raw, vendor-official weights

* [openai](https://huggingface.co/openai)
* [meta-llama](https://huggingface.co/meta-llama)
* [google](https://huggingface.co/google)
* [mistralai](https://huggingface.co/mistralai)
* [Qwen](https://huggingface.co/Qwen)
* [jinaai](https://huggingface.co/jinaai)

#### FIM (fill-in-the-middle) models

* [Qwen/qwen25-coder](https://huggingface.co/collections/Qwen/qwen25-coder)
* [Qwen/qwen3-coder](https://huggingface.co/collections/Qwen/qwen3-coder)

#### Agentic models

* [openai/gpt-oss](https://huggingface.co/collections/openai/gpt-oss)
* [meta-llama/llama-32](https://huggingface.co/collections/meta-llama/llama-32)
* [Qwen/qwen3](https://huggingface.co/collections/Qwen/qwen3)

#### Embedding models

* [Qwen/qwen3-embedding](https://huggingface.co/collections/Qwen/qwen3-embedding)
* [google/embeddinggemma](https://huggingface.co/collections/google/embeddinggemma)
* [jinaai/collections](https://huggingface.co/jinaai/collections)

Pick a model that supports the features required by your task - otherwise you’ll see degraded performance.

### config

Agent automatically generates a local configuration and cache directory.
Right now the cache path is fixed, but future versions will allow custom paths.

The configuration system initializes the agent with sensible defaults, and you can modify any of the settings through the CLI.

#### Configuration CLI

Show help:

```sh
python -m agent.config -h
```

You can **view**, **set**, **list**, or **reset** configuration keys.
Any interaction will create the `.agent` directory, which contains:

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

During development, you may need to clear the `.agent` directory to avoid conflicts between versions or stale state.

```sh
rm -rf .agent
```

If something behaves unexpectedly, wiping this folder is the first thing to try - it has been the most common source of issues during development.

### tools

The agent exposes a small, intentionally restricted set of tools.
These limitations are by design.
They help prevent uncontrolled behavior while still enabling autonomous workflows.

The available tools are:

* **shell**
  An allow-listed command runner.
  Only approved commands may be executed.
  Piping is disabled for now, though it may be enabled later for advanced models.

* **read**
  Read arbitrary slices of a file.

* **write**
  Write or modify slices of a file.

* **memories**
  Create, update, recall, and delete stored memories.
  These form the agent’s persistent knowledge base.

#### Tool chaining

The model can chain tool calls during a single objective.
Once you give the agent a task, it is allowed to operate autonomously, issuing tool calls one after another, until it determines the objective is complete.

After the task is finished, control is returned to you.

### usage

The program is in its infancy (and has been for some time). Only the basics are currently implemented.

To get help, run:

```sh
python -m agent.cli -h
```

The server is automatically executed at runtime. There's no need to run an instance in the background.

```sh
python -m agent.cli --jinja --model /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf
```

Assuming no errors occur, the server process id is registered, then killed at program exit. If an error occurs, its likely that a zombie process exists. Its recommended that you kill that process before executing the program again. This is not a bug. It's just a limitation of the current implementation.

To kill the zombie process, you'll first need to identify it:

```sh
ps aux | grep ${USER} | grep llama-server
```

Identify the process id, then kill it:

```sh
kill <pid-goes-here>
```

Note that I plan on eventually adding a detection mecahnism for tracking, running, and stopping llama-server processes automatically. For now, it's done manually.

Existing keyboard shortcuts are:

- `enter`: Add a newline to the input.
- `backspace`: Retains expected behavior.
- `alt+enter`: Submit a message to the agent.
- `alt+f`: Autocomplete current token.
- `alt+e`: Autocomplete to end of line.
- `ctrl+d`: Pop a message from the sequence.
- `ctrl+c`: Quit the application and kill the `llama-server` process.
- `ctrl+a`: Move cursor to start of line.
- `ctrl+e`: Move cursor to end of line.
- `ctrl+k`: Cut from cursor start to end of line.
- `ctrl+u`: Cut from cursor end to start of line.
- `ctrl+y`: Paste cut content to cursor position.

You can command the model directly, but its best to not assume the model understands your instructions correctly. The models operate best with a human operating as a partner alongside them. They'll build confidence and align themselves naturally with the most probable output.

Some models are heavily conditioned and this may affect their behavior - the llama community calls this censoring, but there's a lot more than that going on under the hood.

It's best to start a project from scratch while slowly ramping up. The more you engage with the process, the better off the project will be as a result. This means actively reading documentation and code, making architectural and design choices, and more. This is the antithesis of vibe coding.

On that note, I actually enjoy programming, so I pick apart every line until I understand how the code behaves.

## Contributions

I'm open to ideas and contributions. Feel free to open an issue or pull request. Authors of PRs must understand the code. If they do not understand the code, the PR will be closed with no further deliberation.

## Resources

- [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [jsonpycraft](https://github.com/teleprint-me/json-py-craft/tree/main/docs)
- [Pygments](https://pygments.org/docs/)
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/index.html)

Note that there is no need for fancy tools like Rich. Pygments and prompt-toolkit should be sufficient for most of the desired features.

## License

AGPL to ensure end-user freedom.
