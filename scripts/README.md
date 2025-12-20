# Scripts

`Agent` uses **llama‑cpp** as its inference backend, and it requires the
following binaries to be present on the target system:

| Binary | Purpose |
|--------|---------|
| `llama-server`   | The server process that serves model queries. |
| `llama-quantize` | Utility for quantising Hugging‑Face checkpoints into GGUF format. |
| `convert_hf_to_gguf.py` | Convert pickled / safetensor weights to GGUF format |

If any of these are missing, Agent will abort.

> **Tip:**  
> ggml‑org supplies prebuilt binaries for most platforms.  For full control
> (CUDA / ROCm / Vulkan), build from source – see the sections below.

## Quick start

```sh
# Clone this repository and run the helper scripts.
git clone https://github.com/youruser/python-agent.git agent
cd agent/scripts

# Install required build tools first …
chmod +x install-packages.sh && ./install-packages.sh

# …then compile & install llama‑cpp binaries into /usr/local.
chmod +x install-llama.sh   && ./install-llama.sh
```

> **Always read the scripts before executing** – they perform a full system
> modification.

## Manual build (any distro)

```sh
git clone https://github.com/ggml-org/llama.cpp.git ~/builds/llama.cpp
cd ~/builds/llama.cpp

# Configure for Vulkan backend and shared libs.
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DGGML_VULKAN=1 # change to CUDA / ROCm (HIP) if desired.

# Compile
cmake --build build -j "$(nproc)"

# Install (default: /usr/local)
DESTDIR=/usr/local cmake install --build build
```

> Vulkan is the most portable option – it works on NVIDIA, AMD and Intel GPUs,
> even older cards such as RX 580.

## Arch Linux

I provide a personal PKGBUILD that builds `llama.cpp` from source with Vulkan.
To use it:

```sh
cd scripts    # contains my custom PKGBUILD
makepkg -Ccsi # clean build, install & resolve dependencies automatically
```

> **⚠️** Review the PKGBUILD *before* installing – you’re building a package that will replace any existing `llama.cpp` packages on your system.

## Distro‑specific installers

| Distribution | Command |
|--------------|---------|
| Debian (unstable) | ```sudo apt install llama.cpp``` |
| Fedora            | ```sudo dnf install llama.cpp``` |
| Arch / AUR        | ```yay -S llama.cpp```, optionally with `-cuda`/`-hip`/`-vulkan` suffixes |

> Packages on the official repositories are typically limited to CPU
> builds.  For GPU support, compile from source as described above.

## Script utilities

| File               | Purpose |
|--------------------|---------|
| **packages.sh**         | Shared helper functions used by all scripts (never executed directly). |
| **install-packages.sh** | Installs build‑time dependencies required for the Vulkan backend. |
| **install-llama.sh**    | Builds and installs `llama.cpp` binaries into `/usr/local`. |

> None of these are automatically run – you must call them manually after
> reviewing their contents.

## Uninstallation

If you installed via CMake:

```sh
cd ~/builds/llama.cpp          # or wherever the source lives
make uninstall                   # uses install_manifest.txt internally
```

For a PKGBUILD installation, use pacman:

```bash
sudo pacman -Rns llama-cpp   # removes package and orphaned deps if you wish.
```

## Further reading

* Official build guide: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md  
* API reference & examples are in the `docs` directory of the repo.

Happy hacking!

