# Bluefin - rely on OCI layer sharing for distrobox and devcontainer

 [![project bluefin](./docs/project-bluefin.svg)](https://projectbluefin.io/)
 
As I began using bluefin on my production laptop I was really challenged to rethink my assumptions on how to use and manage a development linux workstation.

I have been relying on cloud native technology for many years to enable my development workflow. For several years I had k3s installed on a Raspberry Pi cluster, because, why not? If my code runs on armv7 then it will have no problem running in an x86_64 context.

Right before I started using bluefin I had let go of k3s and went back to using docker compose to build and run projects locally.

Using bluefin, I finally had a reason to dive deep into using [Dev Containers in vscode](https://code.visualstudio.com/docs/devcontainers/containers). And so the experimentation began...

Of the 3 experiments I have performed so far, this one seems to offer the best balance of features and HD space utilization.

- [Bluefin - use podman distrobox container in vscode](https://universal-blue.discourse.group/t/bluefin-use-podman-distrobox-container-in-vscode/6193)
- [Bluefin - use docker distrobox container in vscode](https://universal-blue.discourse.group/t/bluefin-use-docker-distrobox-container-in-vscode/6195)
- Bluefin - rely on OCI layer sharing for distrobox and devcontainer

> [!IMPORTANT]
> What I am presenting in this repo is a sample implementation of some ideas. You should not think of this repo as code that you can clone and use as is. Your requirements are going to be different than mine. Be prepared to heavily modify or even rewrite what is here.
>
> The files herein are simply a sample implementation of the ideas presented below.


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
| Other Images      | as needed for projects<br>- separate image tags per tool version - e.g., zig `0.13` vs `nightly`<br>- contains only dependencies for that tool env<br>- built from source or installed with OS (or other) package manager, or `curl` deployment script |
| ~~`-dx` layer~~   | customization is **N/A**<br>- only contains UID / GID mapping to support `$HOME` bind mount<br>- always the last layer<br>- kept as light as possible because these layers are not shared |
| ~~Distrobox~~     | avoid - defer to OCI images |
| Dev Container     | avoid if can, but flexibility is available<br>- specialized tool version for individual projects; vscode extensions, etc.<br>  - typically not shared across repos / branches<br>- or where cloned repo already contains .devcontainer spec<br>- much less layer sharing |

## Image Hierarchy
This is just an example of my current setup. It will change drastically over time and yours, undoubtedly, will be different.

> If multiple top-level images are needed, then the result will be multiple hierarchies. Try to avoid that complexity; extra HD space consumption. But the flexibility is available if needed.

```
        ghcr.io/ublue-os/fedora-toolbox:latest
                        |
                fedora41-dev-base                   includes git, vscode, emacs, info. vim, tmux, fastfetch, fzf, zoxide
                        |
                fedora41-python                     includes py313, py314, py314t, tkinter, tk, gitk
               /        |       \
              /         |       fedora41-zig        includes clang, llvm, cmake, zig, zls
             /          |             \
    fedora41-go         |              |            includes golang, gopls
       |                |              |
fedora-go-dx fedora41-python-dx  fedora41-zig-dx    adds USER, GROUP - built with Containerfile.img-dx with IMG and USER build args
```

## Guiding Principles
1. Keep the most common things that should be shared higher up in the hierarchy
2. Keep things that are specific (especially version specific) lower in the hierarchy
3. The final layer cannot be shared (`-dx` layer) but are built using a common parameterized build (`Containerfile.img-dx`) for repeatability
4. Both `distrobox` and `devcontainer` use `fedora41-*-dx` images and bind mount `$HOME` dir.
5. All activities that mutate the file system are constrained to `$HOME`, `/tmp`, etc. to eliminate OCI image layer Copy-on-Write (CoW) operations.
6. Images and containers are periodically re-created to:
	- update container internals efficiently
	- clean up no longer needed containers, images, volumes
	- focus on what is needed right now to minimize HD space utilization

## Dev Container Specific Concerns
> Note that `vscode` is installed in `fedora41-dev-base` for `vscode-server` primarily. This is required by the **Dev Containers** `vscode` extension.

When using the `fedora41-*-dx` images in a devcontainer please make sure to do the following.

- Reference the local image
- set the `$HOME` and `$USER` env vars
- mount the `$HOME` dir as a bind mount
- set `remoteUser` to whatever `$USER` is in use - the OCI image is setup so that the `$UID` and `GID` are created to be the same to simplify working in the `$HOME` dir

<details>
<summary>Expand to see sample devcontainer.json snippet</summary>

```json
{
	"name": "my-devcontainer-project",
	"image": "fedora41-python-dx:latest",
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


## Amount of Reusability

The layers from `ghcr.io/ublue-os/fedora-toolbox:latest`, `fedora41-dev-base` and `fedora41-python` are all shared. The rest are not (and should not be). If the lifetime of the images and containers are managed as projects become active / deferred then HD utilization will be minimized over time.

<details>
<summary>Expand to see how layers are shared</summary>

```
$ ./show_img_layers.sh 
#* ----------------------------------------------------------------------
vsc-pi-day-2025-with-py-661c447e34349d05dc28e2d4e1b224160b64e283dc0277ac1d54f3ef09e9608c-uid
#* ----------------------------------------------------------------------
[
  "sha256:0c2b6a377a20da8b9ac82b59bbbcfa9bd456c9b84d34e3061c7983dad7a8f099",
  "sha256:b98392206191c39eeef6b2ca6f190614835decc5d5e9ee1a14e9bcbe6602c6b9",
  "sha256:5751b81ae8667b954dc3c663aa797472e7e77bc46b640825069e0c86cde590ea",
  "sha256:7e9c868121fc600cbc22ba2f463dc97c4bf6b424486ac9d13b3a96efc62afae8",
  ---
  "sha256:20951a30ee757fa4c4c9ed674a0cd4e9fe5c714a1bacfba71f089e602771820d",
  "sha256:2a61b3c79f20e1dc7332ec35776e46760821e04a39193c6dd7feba4e2201f860",
  "sha256:66280f6f1726d1ca9b6e005e69ea3c7c6814e1b44fab140053fa83fd453f6d7a",
  "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef"
]
#* ----------------------------------------------------------------------
fedora41-zig-dx
#* ----------------------------------------------------------------------
[
  "sha256:0c2b6a377a20da8b9ac82b59bbbcfa9bd456c9b84d34e3061c7983dad7a8f099",
  "sha256:b98392206191c39eeef6b2ca6f190614835decc5d5e9ee1a14e9bcbe6602c6b9",
  "sha256:5751b81ae8667b954dc3c663aa797472e7e77bc46b640825069e0c86cde590ea",
  "sha256:7e9c868121fc600cbc22ba2f463dc97c4bf6b424486ac9d13b3a96efc62afae8",
  ---
  "sha256:bae5826f4b9ecf759664926666fbffaf77fecd578bcff44dd068a22629e73947",
  "sha256:68537e08bc0cdd6af3e76c529f55c08022193926f8e2d58fe405909edbb06db9",
  "sha256:20951a30ee757fa4c4c9ed674a0cd4e9fe5c714a1bacfba71f089e602771820d",
  "sha256:53fed649be544c960f7e8081fe19f5847f9d799f11085daa2e0654049d2894c0",
  "sha256:6e4909f2a675d10605e7f69a27cc9180cbd0113d1f8a0d5bf720218decbd774c"
]
#* ----------------------------------------------------------------------
fedora41-go-dx
#* ----------------------------------------------------------------------
[
  "sha256:0c2b6a377a20da8b9ac82b59bbbcfa9bd456c9b84d34e3061c7983dad7a8f099",
  "sha256:b98392206191c39eeef6b2ca6f190614835decc5d5e9ee1a14e9bcbe6602c6b9",
  "sha256:5751b81ae8667b954dc3c663aa797472e7e77bc46b640825069e0c86cde590ea",
  "sha256:7e9c868121fc600cbc22ba2f463dc97c4bf6b424486ac9d13b3a96efc62afae8",
  ---
  "sha256:4ab09ae90712d28fabed751da22fd5add31db35f41a606eb94f7fb986aaadeaf",
  "sha256:a324f282ed39dcb7ebfb752d3daf5b601ed7101a93799e8f021b5ae607862e6b",
  "sha256:c66cce1c5801fcf1d6dffc57c63969a9d8638ac2bed6283e13a962465867bbfc",
  "sha256:9cbf655016ac3a4a54621b064257b45f1452048fd468cbd58eb3d8e1f1a48218"
]
#* ----------------------------------------------------------------------
fedora41-python-dx
#* ----------------------------------------------------------------------
[
  "sha256:0c2b6a377a20da8b9ac82b59bbbcfa9bd456c9b84d34e3061c7983dad7a8f099",
  "sha256:b98392206191c39eeef6b2ca6f190614835decc5d5e9ee1a14e9bcbe6602c6b9",
  "sha256:5751b81ae8667b954dc3c663aa797472e7e77bc46b640825069e0c86cde590ea",
  "sha256:7e9c868121fc600cbc22ba2f463dc97c4bf6b424486ac9d13b3a96efc62afae8",
  ---
  "sha256:20951a30ee757fa4c4c9ed674a0cd4e9fe5c714a1bacfba71f089e602771820d",
  "sha256:2a61b3c79f20e1dc7332ec35776e46760821e04a39193c6dd7feba4e2201f860",
  "sha256:66280f6f1726d1ca9b6e005e69ea3c7c6814e1b44fab140053fa83fd453f6d7a"
]
```
</details>

## Example Consumer Project

Please see [klmcwhirter/pi-day-2025-with-py](https://github.com/klmcwhirter/pi-day-2025-with-py) for a sample project that uses `fedora41-python-dx:latest` in a dev container.

## References
1. https://universal-blue.discourse.group/t/bluefin-use-docker-distrobox-container-in-vscode/6195/1
2. https://universal-blue.discourse.group/t/bluefin-use-podman-distrobox-container-in-vscode/6193/1
3. https://code.visualstudio.com/docs/devcontainers/containers
4. https://code.visualstudio.com/api/advanced-topics/remote-extensions#debugging-in-a-custom-development-container
5. https://github.com/ublue-os/toolboxes
