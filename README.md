# Vortex GPGPU

Vortex is a full-stack open-source RISC-V GPGPU.

## Specifications

- Support RISC-V RV32IMAF and RV64IMAFD
- Microarchitecture:
    - configurable number of cores, warps, and threads.
    - configurable number of ALU, FPU, LSU, and SFU units per core.
    - configurable pipeline issue width.
    - optional graphics rasterizer, texture, and OM units.
    - optional local memory, L1, L2 and L3 caches.
- Software: OpenCL 1.2 Support.
- Supported FPGAs:
    - Altera Arria 10
    - Altera Stratix 10
    - Xilinx Alveo U50, U250, U280
    - Xilinx Versal VCK5000

## Directory structure

- `doc`: [Documentation](docs/index.md).
- `hw`: Hardware sources.
- `driver`: Host drivers repository.
- `runtime`: Kernel Runtime software.
- `sim`: Simulators repository.
- `tests`: Tests repository.
- `ci`: Continuous integration scripts.
- `miscs`: Miscellaneous resources.

## Build Instructions
More detailed build instructions can be found [here](docs/install_vortex.md).
### Supported OS Platforms
- Ubuntu 18.04, 20.04, 22.04, 24.04
- Centos 7
### Toolchain Dependencies
- [POCL](http://portablecl.org/)
- [LLVM](https://llvm.org/)
- [RISCV-GNU-TOOLCHAIN](https://github.com/riscv-collab/riscv-gnu-toolchain)
- [Verilator](https://www.veripool.org/verilator)
- [cvfpu](https://github.com/openhwgroup/cvfpu.git)
- [SoftFloat](https://github.com/ucb-bar/berkeley-softfloat-3.git)
- [CocoGfx](https://github.com/gtcasl/cocogfx.git)
- [Ramulator](https://github.com/CMU-SAFARI/ramulator.git)
- [Yosys](https://github.com/YosysHQ/yosys)
- [Sv2v](https://github.com/zachjs/sv2v)
### Install Vortex codebase
```sh
git clone --depth=1 --recursive https://github.com/vortexgpgpu/skybox.git
cd skybox
```
### Install system dependencies
```sh
# ensure dependent libraries are present
sudo ./ci/install_dependencies.sh
```
### Configure your build folder
```sh
mkdir build
cd build
../configure --xlen=32 --tooldir=$HOME/tools
```
### Install prebuilt toolchain
```sh
./ci/toolchain_install.sh --all
```
### Set environment variables
```sh
# should always run before using the toolchain!
source ./ci/toolchain_env.sh
```
### Building Vortex
```sh
make -s
```

## Tested baseline (Ubuntu 24.04 host)

This repo is actively tested on Ubuntu 24.04 with an out‑of‑tree build and
`--osversion=ubuntu/focal` (configure does not recognize noble yet).

**Required system packages (from `ci/install_dependencies.sh`):**
```sh
sudo apt-get update -y
sudo apt-get install -y build-essential valgrind libstdc++6 binutils python3 uuid-dev ccache
sudo apt-get install -y libboost-serialization-dev libpng-dev
```

**Toolchain requirements:**
- `CC=gcc` and `CXX=g++` for host builds (prevents accidental RISC‑V host builds).
- Verilator available in `PATH` for `rtlsim` (example: `/home/svt/tools/verilator/bin`).

**Recommended build workflow (out‑of‑tree):**
```sh
mkdir build-xlen32
cd build-xlen32
../configure --xlen=32 --osversion=ubuntu/focal
source ./ci/toolchain_env.sh
CC=gcc CXX=g++ make -s
```

## Quick smoke (SimX)
```sh
./ci/blackbox.sh --driver=simx --app=vecadd --cores=2
CONFIGS="-DEXT_GFX_ENABLE" ./ci/blackbox.sh --driver=simx --app=draw3d \
  --args="-ttekkaman.cgltrace -w256 -h256" --cores=2
```
The generated image is written under the build folder:
`build-*/tests/regression/draw3d/output.png`

## Microtests (graphics sanity)
```sh
# from the repo root or build dir
PATH=/home/svt/tools/verilator/bin:$PATH OSVERSION=ubuntu/focal ./ci/skybox_microtests.sh
```
Results are saved to `build-*/artifacts/microtests/results.md` and `.csv`.
### Quick demo rendering a 3D scene using 2 cores

<p align="center">
  <a href="docs/assets/img/tekkaman_1024x1024.png">
    <img src="docs/assets/img/tekkaman_1024x1024.png" alt="output" width=256/>
  </a>
</p>

```sh
CONFIGS="-DEXT_GFX_ENABLE" ./ci/blackbox.sh --driver=simx --app=draw3d --args="-ttekkaman.cgltrace -w256 -h256" --cores=2
```
The generated image will be written to <span style="color: yellow;">tests/regression/draw3d/output.png</span>

### Common Developer Tips
- Installing Vortex kernel and runtime libraries to use with external tools requires passing --prefix=<install-path> to the configure script.
```sh
../configure --xlen=32 --tooldir=$HOME/tools --prefix=<install-path>
make -s
make install
```
- Building Vortex 64-bit requires setting --xlen=64 configure option.
```sh
../configure --xlen=64 --tooldir=$HOME/tools
```
- Sourcing "./ci/toolchain_env.sh" is required everytime you start a new terminal. we recommend adding "source <build-path>/ci/toolchain_env.sh" to your ~/.bashrc file to automate the process at login.
```sh
echo "source <build-path>/ci/toolchain_env.sh" >> ~/.bashrc
```
- Making changes to Makefiles in your source tree or adding new folders will require executing the "configure" script again without any options to get changes propagated to your build folder.
```sh
../configure
```
- To debug the GPU, the simulation can generate a runtime trace for analysis. See /docs/debugging.md for more information.
```sh
./ci/blackbox.sh --app=demo --debug=3
```
- For additional information, check out the /docs.

## Where to read more
- `docs/skybox_feature_map.md` — graphics block map from RTL
- `docs/skybox_hw_sw_interface.md` — AXI/DCR integration + SW control surface
- `docs/skybox_linux_graphics_readiness.md` — Linux/Wayland readiness + gaps
- `docs/skybox_linux_graphics_readiness_ru.md` — RU/extended readiness report
- `docs/skybox_rtl_inventory_ru.md` — source-based RTL inventory (Stage 09b)
- `docs/skybox_rtl_modules_by_subsystem.md` — generated subsystem module map
- `docs/skybox_vulkan_opengl_keyword_audit_ru.md` — HW-first keyword audit
- `docs/skybox_hw_gfx_driver_primitives_ru.md` — HW primitive readiness matrix
- `docs/README.md` — index of Skybox‑specific docs and test entry points
