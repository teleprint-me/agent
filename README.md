# Agent

## About

**Agent** is a frontend CLI client for the llama.cpp REST API.

> **Note:** This is an personal toy project. I'm not expecting this to go anywhere special.

## llama.cpp

Agent depends on the llama.cpp backend. You'll need to install it to enable an agentic workflow.

ggml-org releases pre-built binaries for end users. Some linux distributions support a package for llama.cpp, e.g. Arch Linux from the AUR. llama.cpp supports a wide variety of backends from CUDA to ROCm and more. 

You'll need to follow the instructions in the llama.cpp README.md for building.

Agent primarily depends upon the `llama-server` binary.

Create a local working environment.

```sh
mkdir ~/.bin/cpp
cd ~/.bin/cpp
git clone https://github.com/ggml-org/llama.cpp llama.cpp
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Debug -DGGML_DEBUG=0 -DBUILD_SHARED_LIBS=1 -DGGML_VULKAN=1
cmake --build build -j $(nproc)
```

Add `llama-server` and related binaries to the environment:

```sh
cd # go home
echo "export PATH=${PATH}:/path/to/build/bin" >> ~.bashrc
```

If you use `zsh` or some other shell, you can add it similarily.

```sh
echo "export PATH=${PATH}:/path/to/build/bin" >> .zshrc
```

ggml-org hosts their own quantized weights on huggingface. You can toggle flags to auto-download the target weights. I do not recommend doing this. It's easy to lose track of where the weights are and downloading models eats up disk space fast. I have 10TB of local storage and it's already consumed half of that.

neither huggingface nor ggml-org allow you to pick a path to download. they both create a cache path which then stores the model weights in some arbitrarily chosen path which is usually local to the users home path.

I have a package that I plan on merging into agent that allows users to specify exactly where they want the weights to be stored. It's not very user friendly, but it gets the job done. You can then reference the model from **any** chosen storage path which is a huge deal considering how big the weights are.

It's best practice to download the original model weights from the vendor directly, then quantize the model weights locally. It's not difficult, but it can be bandwidth intensive.

Note that there is no benefit to quantizing models on the GPU. Use the CPU to utilize system memory more effectively. It's common that the CPU will have more memory avaiable than the GPU itself.

```sh
~/.bin/cpp/llama.cpp
python -m venv .venv
source .venv/bin/activate
pip install -U pip
install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

From here, you'll need to download the model weights from the vendor. Once you've done that, you can convert the model wieghts.

```sh
python convert_hf_to_gguf.py -h
```

The conversion process is rather simple in use (the implementation is quite involved).

```sh
python convert_hf_to_gguf.py /mnt/models/openai/gpt-oss-20b --outtype q8_0 --outfile /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf
```

Once you have the model weights, you're all set to go.

Recommended models are:

- Qwen2.5 and Qwen3 coder models for FIM
- GPT-OSS and Qwen3 for Agentic abilities.
- Gemini, Jinaai, or Qwen3 for Embeddings

Feel free to use any model you prefer. The model shoudld support the features for the provided task at hand. Otherwise, it will perform poorly.

## Setup

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

## Running

The program is in its infancy (and has been for some time). Only the basics are currently implemented.

To get help, run:

```sh
python -m agent.cli -h
```

The server is automatically executed at runtime. There's no need to run an instance in the background.

```sh
python -m agent.cli --jinja --model /mnt/models/openai/gpt-oss-20b/ggml-model-q8_0.gguf
```

Assuming no errors occur, the server process id is registered, then killed at program exit. If an error occurs, its likely that a zombie process exists. Its recommended that you kill that process before executing the program again.

This is not a bug. It's just a limitation of the current implementation.

## Future Plans

- Refining support for tool-calling.
- Add basic chat support.
- Add a basic text editor.
- Add dynamic syntax high-lighting.
- Add retrieval augmented generation.
- Enable hot-swapping models for memory constrained environments.
- And more.

I have a lot of ideas, but I have no idea how I'm going to go about it. I'm just experimenting as I go.

## Layout

I'm currently in the process of merging older projects together directly into this one. Some modules may be entirely or partially broken. Some dependencies have issues.

The primary sub-packages are:

- cli: The main program
- config: Automated configuration.
- llama: Core llama-server wrapper.
- text: Text extraction utilities.
- tools: Tools available to models.

## Examples

Look out for examples as that's usually where I prototype modules. 

## Contributions

I'm open to ideas and contributions. Feel free to open an issue or pull request.

## Resources

- [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [OpenAI API](https://platform.openai.com/docs/api-reference/introduction)
- [jsonpycraft](https://github.com/teleprint-me/json-py-craft/tree/main/docs)
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/index.html)
- [Tkinter](https://docs.python.org/3/library/tkinter.html)
- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/en/latest/)

## License

AGPL to ensure end-user freedom.
