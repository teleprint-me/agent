# Scripts

Agent depends upon llama.cpp as the backend service.
Agent specifically relies on the **`llama-server`** binary.

Primary tools are as follows:

- llama-server: The llama.cpp server is the primary binary that agent depends on.
- llama-quantize: Binary used to quantize huggingface models.
- convert_hf_to_gguf.py: A python script used to convert pickled and or safetensor weights to gguf file format.

Agent will fail to execute if these primary dependencies are not met.

Note that `ggml-org` provides prebuilt binaries for common platforms, and some Linux
distributions (e.g., Arch Linux) offer packages through their package managers.
However, building from source is straightforward and gives you full control
over backend support (CUDA, ROCm, Vulkan, etc.).

## Layout

I have provided some (untested) utility scripts which are as follows:

NOTE: Do not run these scripts before reviewing them.

- packages.sh: The source library for common functions shared across scripts.
- install-packages.sh: Installs core development dependencies for building the ggml vulkan backend from source.
- install-llama.sh: Installs the llama.cpp binaries into the target system.

I also have a custom PKGBUILD I personally use for Arch Linux.

## Distro install

llama.cpp is still in review for popular distributions.

Supported distributions are Debian, Fedora, and Arch Linux.

Fedora officially supports packaging llama.cpp.

```sh
# most dependencies are install out of the box
sudo dnf install llama.cpp
```

Currently, Debian only provides llama.cpp via the unstable repositories.

```sh
# This assumes you modified the appropriate config
sudo apt install llama.cpp
```

Arch users are expected to have the supported backend drivers installed already.
Arch Linux only provides llama.cpp via the AUR. You can choose between CPU, CUDA, HIP, and Vulkan.

```sh
# this is the base for CPU
yay -S llama.cpp # use the proper prefix for desired backends
```

## Arch Linux

You can install this any way you'd like. My preferred method is to use `makepkg`.

NOTE: Always review the PKGBUILD **before** execution.

```sh
cd scripts
makepkg -Ccsi
```

This does a clean build and install from the latest source available.

## Lazy install

You can install using the custom scripts. You must review them before execution.

Ensure you do not have any preinstalled packages related to llama.cpp
Note that the scripts are disabled by default to preempt impulsive or premature execution.

```sh
cd scripts
chmod +x install-packages.sh
chmod +x install-llama.sh
```

These scripts *should* automate the build and installation process.

To remove the installation, you must have the original build files.
Enter the working directory, then execute for removal.

```sh
cd scripts/ggml-org/llama.cpp
make uninstall
```

CMake usually does a good job of automating this, even if the build rules didn't account for it.
If this is not an option, then you can use the local build manifest file to remove the files for you.

```sh
xargs rm < build/install_manifest.txt
```

## Manual install

Ensure you have drivers installed for your supported hardware.

Create a local workspace:

```sh
cd scripts
git clone https://github.com/ggml-org/llama.cpp ggml-org/llama.cpp
cd ggml-org/llama.cpp
```

Then build from source:

```sh
cmake -B build -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=1 \
      -DGGML_VULKAN=1

cmake --build build -j $(nproc)
```

Installing is just as simple.

```sh
DESTDIR=/usr/local cmake install --build build
```

Vulkan is recommended because it works across **NVIDIA, AMD, and Intel**,
including older cards such as the RX 580.
