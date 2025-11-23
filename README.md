# Agent

## About

**Agent** is a frontend CLI client for the llama.cpp REST API.

**Note:** This is an personal toy project.
I'm not expecting this to go anywhere special.

## Layout

I'm currently in the process of merging older projects together directly into this one. Some modules may be entirely or partially broken. Some dependencies have issues.

The primary sub-packages are:

- cli: The main program.
- config: Automated configuration.
- llama: Core llama-server wrapper.
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

Agent depends on the llama.cpp backend. You'll need to install it to enable an agentic workflow.

ggml-org releases pre-built binaries for end users. Some linux distributions support a package for llama.cpp, e.g. Arch Linux from the AUR. llama.cpp supports a wide variety of backends from CUDA to ROCm and more. 

You'll need to follow the instructions in the llama.cpp README.md for building.

Agent primarily depends upon the `llama-server` binary.

Create a local working environment.

```sh
mkdir -p ~/.bin/cpp
git clone https://github.com/ggml-org/llama.cpp ~/.bin/cpp/llama.cpp
cd ~/.bin/cpp/llama.cpp
```

Then build:

```
cmake -B build -DCMAKE_BUILD_TYPE=Debug -DGGML_DEBUG=0 -DBUILD_SHARED_LIBS=1 -DGGML_VULKAN=1
cmake --build build -j $(nproc)
```

Vulkan has the widest range for support and supports Nvidia, AMD, and Intel. This includes older cards like the RX 580.

We need to add `llama-server` and related binaries to the environment:

```sh
cd # go home
echo "export PATH=${PATH}:/path/to/build/bin" >> ~/.bashrc # or ~/.zshrc
```

If you use `zsh` or some other shell, you can add it similarily. Restart the shell and make sure the binary is available.

```sh
which llama-server
```

It should output the absolute path to the binary.

Neither huggingface nor ggml-org allow you to pick a path to download. They both create a cache path which then stores the model weights in some arbitrarily chosen path - which is usually local to the users home path. Huggingface creates symbolic links which are hashed entries and obfuscate the model files.

ggml-org hosts their own quantized weights on huggingface. You can toggle flags to auto-download the target weights, but I do not recommend doing this. It's easy to lose track of where the weights are and downloading models eats up disk space fast. I have 10TB of local storage and it's already consumed half of that.

If you download the model from ggml-org (which is safe), get the model directly and then store the weights in the desired path. That way, you know where the weights are.

It's best practice to download the original model weights from the vendor directly, then quantize the model weights locally. It's not difficult, but it can be bandwidth intensive.

I have a package that I plan on merging into agent that allows users to specify exactly where they want the weights to be stored. It's not very user friendly, but it gets the job done. You can then reference the model from **any** chosen storage path - which is a huge deal considering how big the weights are.

llama.cpp has a utility for converting model weights which is written in python.

```sh
cd ~/.bin/cpp/llama.cpp
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Note that there is no benefit to quantizing models on the GPU. Use the CPU to utilize system memory more effectively. It's common that the CPU will have more memory available than the GPU itself.

From here, you'll need to download the model weights from the vendor. Once you've done that, you can convert the model weights.

For help, just use the following command.

```sh
python convert_hf_to_gguf.py -h
```

The conversion process is simple assuming you installed the required dependencies.

```sh
python convert_hf_to_gguf.py /mnt/models/openai/gpt-oss-20b --outtype q8_0 --outfile /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf
```

Once you have the model weights, just deactivate the virtual environment, and you're all set to go.

```sh
deactivate
cd # go home
```

Recommended models are:

- Qwen2.5 and Qwen3 coder models for FIM
- GPT-OSS and Qwen3 for Agentic abilities.
- Gemini, Jinaai, or Qwen3 for Embeddings

Feel free to use any model you prefer. The model should support the features for the provided task at hand. Otherwise, it will perform poorly.

### agent

Agent is not ready to be installed locally, but you can do so if you desire. Note that I do not currently recommend doing this for a lot of very valid reasons. 

Agents are not restricted and may be able to run amock continuously unless interrupted.

Currently, the recommended way is to treat this as a development package.

```sh
mkdir /mnt/source/python
git clone https://github.com/teleprint-me/agent /mnt/source/python/agent
cd /mnt/source/python/agent
```

Create and activate a virtual environment to isolate python packages.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

I don't plan on using anything special for managing packages. Using `venv` keeps things simple.

### config

Agent will auto-magically generate a cache path locally. There's no way to specify the path for the cache at the moment, but I plan on allowing users to define the path if they'd like.

The configuration sets up the agent with sane defaults. You can modify the settings however you'd like.

For help, use the following command:

```sh
python -m agent.config -h
```

You can view, set, list, or reset the configuration. Doing so will create the `.agent` path which contains logs, settings, a database for the agents storage, and a cache of the most recent chat history.

```sh
tree .agent   
.agent
├── messages.json
├── model.log
├── settings.json
└── storage.sqlite3

1 directory, 4 files
```

You will need to wipe this directory every so often between development cycles.

```sh
rm -rf .agent
```

This way, there are no conflicts between releases. If you run into any issues, the first thing you should do is reset the cache. I've found this to be a common source of issues I've run into while developing this software.

### tools

The agent has limited access and functionality. This is intentional and by design.

The agent has the following tools:

- shell: An allow list restricting available commands.
- read: Read any part of a file.
- write: Write any part of a file.
- memories: Store (create, update), recall (read), and forget (delete) memories.

The model can chain tool calls between each action. This means once given an objective, it will continue to operate independently on its own until that objective has been completed.

Once an objective has been completed, you will regain control of the prompt.

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

You can use `ctrl+d` to pop messages within the sequence. `ctrl+c` to exit the interface and kill the server process.

You can command the model directly, but its best to not assume the model understands your instructions correctly. The models operate best with a human operating as a partner alongside them. They'll build confidence and align themselves naturally with the most probable output.

Some models are heavily conditioned (the llama community calls this censoring, but there's a lot more than that going on under the hood) and this may affect their behavior. It's best to start a project from scratch while slowly ramping up. The more you are a part of the decision and action process, the better off the project will be as a result. This is the antithesis of vibe coding.

On that note, I actually enjoy programming, so I pick apart every line until I understand how the code behaves.

## Contributions

I'm open to ideas and contributions. Feel free to open an issue or pull request. Authors of PRs must understand the code. If they do not understand the code, the PR will be closed with no further dileberation.

## Resources

- [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [jsonpycraft](https://github.com/teleprint-me/json-py-craft/tree/main/docs)
- [Pygments](https://pygments.org/docs/)
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/index.html)

Note that there is no need for fancy tools like Rich. Pygments and prompt-toolkit should be sufficient for most of the desired features.

## License

AGPL to ensure end-user freedom.
