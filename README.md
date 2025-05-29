# Bluefin - rely on OCI layer sharing for distrobox and devcontainer

 [![project bluefin](./docs/project-bluefin.svg)](https://projectbluefin.io/)

As I began using bluefin on my production laptop I was really challenged to rethink my assumptions on how to use and manage a development linux workstation.

I have been relying on cloud native technology for many years to enable my development workflow. For several years I had k3s installed on a Raspberry Pi cluster, because, why not? If my code runs on armv7 then it will have no problem running in an x86_64 context.

Right before I started using bluefin I had let go of k3s and went back to using docker compose to build and run projects locally.

Using bluefin, I finally had a reason to dive deep into using [Dev Containers in vscode](https://code.visualstudio.com/docs/devcontainers/containers). And so the experimentation began...

Of the experiments I have performed so far, this one seems to offer the best balance of features and HD space utilization.

- [Bluefin - use podman distrobox container in vscode](https://universal-blue.discourse.group/t/bluefin-use-podman-distrobox-container-in-vscode/6193)
- [Bluefin - use docker distrobox container in vscode](https://universal-blue.discourse.group/t/bluefin-use-docker-distrobox-container-in-vscode/6195)
- [**Bluefin - rely on OCI layer sharing for distrobox and devcontainer**](https://universal-blue.discourse.group/t/bluefin-rely-on-oci-layer-sharing-for-distrobox-and-devcontainer/6519)
- [Bluefin - Using distrobox with vscode tasks](https://universal-blue.discourse.group/t/bluefin-using-distrobox-with-vscode-tasks/8448)

> [!IMPORTANT]
>
> What I am providing in this repo is a sample implementation of some ideas.
>
> You should not think of this repo as code that you can clone and use as is. Your requirements are going to be different than mine. Be prepared to heavily modify or even rewrite what is here.
>
> The files herein are simply a sample implementation of the ideas presented below.

### Table of Contents

- [Problem Statement](#problem-statement)
- [Tool Installation Proposed Policy](#tool-installation-proposed-policy)
- [Image Hierarchy](#image-hierarchy)
- [Guiding Principles](#guiding-principles)
- [Amount of Reusability](#amount-of-reusability)
- [Dev Container Specific Concerns](#dev-container-specific-concerns)
- [Podman Distrobox Compatibility](#podman-distrobox-compatibility)
- [Example Consumer Project](#example-consumer-project)
- [Scripts and Sample Config](#scripts-and-sample-config)
- [Command Line Interface](#command-line-interface)
- [Sample Config Structure](#sample-config-structure)
- [Assumptions](#assumptions)
- [References](#references)

## Problem Statement

As a developer using one of the bluefin-dx bootc images, I would like:

- a set of OCI images that can be used for both distroboxen and dev containers
- manage the versions of tool chains between development projects as they are encountered in a single place
	- e.g., the version of `zig` should be the same in a `devcontainer` and corresponding `distrobox`
	- but multiple versions of `zig` can be accomplished with multiple image tags (e.g., `0.13` vs `nightly`)
	- the version is managed by changing the value of a single ARG or shell variable (as appropriate)
- such that most of the layers (think HD space utilization) will be shared between the `distrobox` and `devcontainer`
- help avoid *host layering* and the need for *custom OS image*

## Tool Installation Proposed Policy
Tools, libraries, etc. could be installed in different locations for varying reasons.

| Where             | Proposed Policy |
| -- | --- |
| ~~Custom Image~~ | Avoid as this is expensive (time, cloud resources) and wasteful as it should not be needed - I like bluefin |
| ~~Host Layering~~ | Avoid at all cost as this defeats the purpose of the deployment model used by bluefin, and can complicate updates |
| Flatpak           | Apps that run close to the host - *not pertinent to this experiment* |
| `$HOME`           | If needed on host as well as in containers<br>- where versioning roughly matches that of the host OS package version (meaning version available in Fedora WS in my case)<br>- can also be used in situations where a specific version needs to be built from source; tested close to the metal as well as in containers<br>- or tool is needed on host as well as containers (e.g., installed via `curl` script)<br>- typically installed with `PREFIX=~/.local` or equiv. |
| Base Image(s)     | All tools, libraries, etc. that are needed in a majority of containers<br>- can install multiple tool versions (with unique names or install locations)<br>- where versioning is typically at pace with image OS package(s)<br>- to maximize layer reuse |
| Other Images      | as needed for projects<br>-separate image tags per tool version - e.g., zig `0.13` vs `nightly`<br>- contains only dependencies for that tool env<br>- built from source or installed with OS (or other) package manager, or `curl` deployment script |
| ~~`-dx` layer~~   | customization is **N/A**<br>- only contains UID / GID mapping to support `$HOME` bind mount<br>- always the last layer<br>- kept as light as possible because these layers are not shared |
| ~~Distrobox~~     | avoid - defer to OCI images |
| Dev Container     | avoid if can, but flexibility is available<br>- specialized tool version for individual projects; vscode extensions, etc.<br>  - typically not shared across repos / branches<br>- or where cloned repo already contains .devcontainer spec<br>- much less layer sharing |

## Image Hierarchy
This is just an example of my current setup. It will change drastically over time and yours, undoubtedly, will be different.

> If multiple top-level images are needed, then the result will be multiple hierarchies. Try to avoid that complexity; extra HD space consumption. But the flexibility is available if needed.

```
        ghcr.io/ublue-os/fedora-toolbox:latest
                        |
                fedora-dev-base                   includes git, vscode, emacs, info, vim, tmux, fastfetch, fzf, zoxide, jq, yq
                        |
                fedora-python                     includes py313, py314, py314t, tkinter, tk, gitk
               /        |     \
              /         |     fedora-zig:0.14.0   includes clang, llvm, cmake, zig, zls
             /          |           \
    fedora-go           |            |            includes golang, gopls
       |                |            |
fedora-go-dx fedora-python-dx  fedora-zig-dx      adds USER, GROUP - built with Containerfile.img-dx with IMG and USER build args
```

## Guiding Principles
1. Keep the most common things that should be shared higher up in the hierarchy
2. Keep things that are specific (especially version specific) lower in the hierarchy
3. The final layers cannot be shared (`-dx` layers) but are built using a common parameterized build ([Containerfile.img-dx](./fedora/Containerfile.img-dx)) for repeatability
4. Both `distrobox` and `devcontainer` use `fedora-*-dx` images and bind mount `$HOME` dir.
5. All activities that mutate the file system are constrained to `$HOME`, `/tmp`, etc. to eliminate OCI image layer Copy-on-Write (CoW) operations.
6. Images and containers are periodically re-created to:
	- update container internals efficiently
	- clean up no longer needed containers, images, volumes
	- focus on what is needed right now to minimize HD space utilization

## Amount of Reusability

The layers from `ghcr.io/ublue-os/fedora-toolbox:latest`, `fedora-dev-base` and `fedora-python` are all shared. The rest are not (and should not be). If the lifetime of the images and containers are managed as projects become active / deferred then HD utilization will be minimized over time.

<details>
<summary>Expand to see how layers are shared</summary>

```
$ ./ocisictl.sh list --layers

docker - fedora-dev-base:latest
- sha256:8aa1535203f2a74c605e30406aea2a4e5df9e6ed0e4343a2df9d3d97f0d2d60b
- sha256:cc6437ae47f7b2ae16ba45604edc5f63b274ca2d00303a4b2821f237bc03db20
---
- sha256:59a8d00200c9c1611119f7fdf63eac0dd0f1621b69748b329051002aebb8d4e3
- sha256:1ebd0393e1601d812744b5d5cf1f171e56ad1353914fac54f11429e63d58077c

docker - fedora-python-dx:latest
- sha256:8aa1535203f2a74c605e30406aea2a4e5df9e6ed0e4343a2df9d3d97f0d2d60b
- sha256:cc6437ae47f7b2ae16ba45604edc5f63b274ca2d00303a4b2821f237bc03db20
---
- sha256:59a8d00200c9c1611119f7fdf63eac0dd0f1621b69748b329051002aebb8d4e3
- sha256:1ebd0393e1601d812744b5d5cf1f171e56ad1353914fac54f11429e63d58077c
- sha256:4ab523a234e0d388e15cbcb9f5e3dcea0c6a2591a6b44a41df975fafae0fe592
---
- sha256:0f2d8438515715cef586a3f83e05cd2a3d29c0adfd4072949cee7b7535d2e981
- sha256:fd9b2541960ca09c0f13e658510a4e65ce777bde3147a33ce561e11d95451ac1
- sha256:4c5aca3e929a2e100cbc46eeb2332f5ab7cbfa88a32f80c21931929e84b2740d

docker - fedora-python:latest
- sha256:8aa1535203f2a74c605e30406aea2a4e5df9e6ed0e4343a2df9d3d97f0d2d60b
- sha256:cc6437ae47f7b2ae16ba45604edc5f63b274ca2d00303a4b2821f237bc03db20
---
- sha256:59a8d00200c9c1611119f7fdf63eac0dd0f1621b69748b329051002aebb8d4e3
- sha256:1ebd0393e1601d812744b5d5cf1f171e56ad1353914fac54f11429e63d58077c
- sha256:4ab523a234e0d388e15cbcb9f5e3dcea0c6a2591a6b44a41df975fafae0fe592

docker - ghcr.io/ublue-os/fedora-toolbox:latest
- sha256:8aa1535203f2a74c605e30406aea2a4e5df9e6ed0e4343a2df9d3d97f0d2d60b
- sha256:cc6437ae47f7b2ae16ba45604edc5f63b274ca2d00303a4b2821f237bc03db20

podman - ghcr.io/ublue-os/debian-toolbox:latest
- sha256:2f7436e79a0bc6cdec6536da54ae6a5863c8e3b5f145e0f8ac0b96306baddbc9
- sha256:5a85dac09342d01219ae9d637ca0df331fc6fc87acd6b8eb8c5012c0723b1e45

podman - localhost/debian:bookworm
- sha256:2f7436e79a0bc6cdec6536da54ae6a5863c8e3b5f145e0f8ac0b96306baddbc9
- sha256:5a85dac09342d01219ae9d637ca0df331fc6fc87acd6b8eb8c5012c0723b1e45
---
- sha256:93ede05a0a9d6728ec9f3be96761f6abfaac5c4fb10b296bf3667fe2162a312f
- sha256:8c94e919a7bd1c6cb962a683059ecd7cf5ef2419b6768bc51197b74d6ff776e6

podman - localhost/debian-dx:bookworm
- sha256:2f7436e79a0bc6cdec6536da54ae6a5863c8e3b5f145e0f8ac0b96306baddbc9
- sha256:5a85dac09342d01219ae9d637ca0df331fc6fc87acd6b8eb8c5012c0723b1e45
---
- sha256:93ede05a0a9d6728ec9f3be96761f6abfaac5c4fb10b296bf3667fe2162a312f
- sha256:8c94e919a7bd1c6cb962a683059ecd7cf5ef2419b6768bc51197b74d6ff776e6
---
- sha256:54a5e317649be16ce3f8b2872f5237eec0cec60225ebdf596c0fddf2d535fb3f
- sha256:42ea0539ce67b1de6d06e9dcdfb0341cc1f4cf317f8341e71d2c2a37d3293cf2
```
</details>

## Dev Container Specific Concerns
> Note that `vscode` is installed in `fedora-dev-base` for `vscode-server` primarily. This is required by the **Dev Containers** `vscode` extension.
> 
> When switchng projects (and devcontainer) that needs different extensions I find I need to `rm -fr ~/.vscode-server` before creating the new devcontainer.
> This is a downside of mounting my `$HOME` directory that I live with.

When using the `fedora-*-dx` images in a devcontainer please make sure to do the following.

- Reference the local image
- set the `$HOME` and `$USER` env vars
- mount the `$HOME` dir as a bind mount
- set `remoteUser` to whatever `$USER` is in use - the OCI image is setup so that the `$UID` and `GID` are created to be the same to simplify working in the `$HOME` dir

<details>
<summary>Expand to see sample devcontainer.json snippet</summary>

```json
{
	"name": "my-devcontainer-project",
	"image": "fedora-python-dx:latest",
	"containerEnv": {
		"HOME": "/var/home/klmcw",
		...
		"USER": "klmcw"
	},
	"mounts": [
		{
			"source": "/var/home/klmcw",
			"target": "/var/home/klmcw",
			"type": "bind"
		}
	],
  ...
  "remoteUser": "klmcw"
}
```

</details>

> Note that the Microsoft [*templates*](https://containers.dev/templates) and [*features*](https://containers.dev/features) are based on Ubuntu and not Fedora. So please do not expect them to work with the images described here whose base image is `ghcr.io/ublue-os/fedora-toolbox:latest`.
> 
> Since my goal is to minimize duplication and HD space utilization I am not heading down that path. Although the idea is good for a sizeable organization to share working image snippets.
> 
> I am going to rely on parameterized Containerfiles as a means of sharing work - e.g., [Containerfile.img-dx](./fedora/Containerfile.img-dx).

## Podman Distrobox Compatibility

There is a downside to strictly using `docker` to get the most out of `vscode` devcontainers.

The Ptyxis container integration does not work with `docker`. And there are no current plans to add it. Ptyxis integrates with `podman`.

Well, guess what? the `fedora-*-dx` images are OCI images. They can be pushed or imported to a repo accessible by `podman`.

And then just set distrobox to use the `podman` image and runtime, then assemble.

```bash
export DBX_CONTAINER_MANAGER=podman

DBX_CONTAINER_ALWAYS_PULL=0 distrobox assemble create --replace --name fedora-python-dx
```

I am not doing that because I am focused on minimizing duplication and HD space utilization.

## Example Consumer Project

Please see [klmcwhirter/pi-day-2025-with-py](https://github.com/klmcwhirter/pi-day-2025-with-py) for a sample project that uses `fedora-python-dx:latest` in a dev container.

## Scripts and Sample Config

> [!IMPORTANT]
> The `ocisictl` tool has been rewritten in Python. If you are looking for the shell implementation see the [ocisictl-shell](https://github.com/klmcwhirter/oci-shared-images/tree/ocisictl-shell) branch.

The main script is [`ocisictl.sh`](./ocisictl.sh). It will create all of the OCI images and assemble distroboxen.
> "2 things are hard in programming: cache invalidation, **naming things** and off-by-one errors."
>
> -many contributors

_I am bad at naming. `ocisictl` stands for **oci**-**s**hared-**i**mage **c**on**t**ro**l**._

`ocisictl` uses a config file - [`ocisictl.yaml`](./ocisictl.yaml) to declare the image hierarchy and which containers to assemble.

### Command Line Interface

`ocisictl` has the following verbs.

_Note that all of them share these options._

|Option|Comment|
| --- | --- |
| -h, --help | print help and exit |
| -f, --file FILE | provides support for multiple yaml files |
| -v, --verbose | turn on verbose (also debug) output |

With the `-f` option you can now have multiple config files to keep things focused. For example, I have added an [`ocisictl-system.yaml`](./ocisictl-system.yaml) file to show how another hierarchy could be added for _system_ (or whatever category you can dream up) containers.

Then you can simply do `./ocisictl.sh process -f ocisictl-system.yaml` or `./ocisictl.sh list -f ocisictl-system.yaml --layers`.

```
$ ./ocisictl.sh --help

usage: python -m ocisictl [-h] (list | process | clean) ...

options:
  -h, --help            show this help message and exit

verbs:
  (list | process | clean)
    list                List information about the configuration or the system
    process             Create images / assemble containers
    clean               Clean up images
```

```
$ ./ocisictl.sh list --help

usage: python -m ocisictl list [-h] [-f FILE] (-a | -e | -l) [-v]

List information about the configuration or the system

options:
  -h, --help       show this help message and exit
  -f, --file FILE  configuration FILE (default: ocisictl.yaml)
  -a, --assemble   list containers to assemble (default: False)
  -e, --enabled    list images to create (default: False)
  -l, --layers     list layers of images (default: False)
  -v, --verbose    enable verbose output (default: False)
```

```
$ ./ocisictl.sh process --help

usage: python -m ocisictl process [-h] [-f FILE] [-p] [-s] [-v]

Create images / assemble containers

options:
  -h, --help        show this help message and exit
  -f, --file FILE   configuration FILE (default: ocisictl.yaml)
  -p, --prune       stop containers and perform system pruning before
                    starting, and clean up artifacts after done (default:
                    False)
  -s, --skip-clean  skip the clean up artifacts step after done (default:
                    False)
  -v, --verbose     enable verbose output (default: False)
```

```
$ ./ocisictl.sh clean --help

usage: python -m ocisictl clean [-h] [-f FILE] [-v]

Clean up images

options:
  -h, --help       show this help message and exit
  -f, --file FILE  configuration FILE (default: ocisictl.yaml)
  -v, --verbose    enable verbose output (default: False)
```

### Sample Config Structure
The supplied [`ocisictl.yaml`](./ocisictl.yaml) file is setup to produce the graph above. It also creates `debian:bookworm` and `debian-bookworm-dx` to highlight how one might create multiple hierarchies if needed.

The file is a YAML list where each item in the list represents an image to create and, optionally, a distrobox to assemble.

|Property|Description|Required|Sample Value|
| --- | --- | --- | --- |
|**Image Creation**||||
|name|the image name; maps to Containerfile._name_|X|fedora-python-dx|
|path|the directory containing Containerfile._name_|X|fedora|
|enabled|whether to process this item or not|X|true or false|
|tag|the image tag to use; defaults to _latest_||0.14.0|
|manager|the DBX_CONTAINER_MANAGER to use; defaults to env var or `docker` if not set; accessible in `PATH`||`docker` or `podman`|
|**Distrobox Assembly**||||
|distrobox|override the name for the assemble step; defaults to _name_||debian-bookworm-dx|
|assemble|whether to assemble or not; defaults to true if _name_ ends with `-dx`||true or false|

### Assumptions

There are (at least) 2 basic assumptions being made by the sample artifacts.

1. Your user is in the `docker` group if you are using `export DBX_CONTAINER_MANAGER=docker`, e.g., if using with devcontainers

   If you are using [bluefin-dx](https://docs.projectbluefin.io/bluefin-dx/#step-2-add-yourself-to-the-right-groups) simply use `ujust dx-mode` and reboot.

2. The base image in use is able to perform the commands in [./fedora/Containerfile.img-dx](./fedora/Containerfile.img-dx) and  [./debian/Containerfile.img-dx](./debian/Containerfile.img-dx) if debian is left `enabled`.

> In addition to those, if you are using `docker` you may want to add `export DBX_CONTAINER_MANAGER=docker` to your .bashrc (or equiv.).
> 
> Be careful with that setting if you use `podman` as well though.
> 
> I do. I am a container junky. Having both `docker` and `podman` gives me separate namespaces for dev stuff (docker) vs system stuff (podman) where I need stability.
> 
> That frees me up to do `docker system prune -af --volumes` at any time without disturbing my _system_ containers.

## References
1. https://universal-blue.discourse.group/t/bluefin-use-docker-distrobox-container-in-vscode/6195/1
2. https://universal-blue.discourse.group/t/bluefin-use-podman-distrobox-container-in-vscode/6193/1
3. https://code.visualstudio.com/docs/devcontainers/containers
4. https://code.visualstudio.com/api/advanced-topics/remote-extensions#debugging-in-a-custom-development-container
5. https://github.com/ublue-os/toolboxes
