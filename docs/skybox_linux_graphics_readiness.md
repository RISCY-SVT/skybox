# Skybox Linux graphics readiness (source-based)

This report is derived from RTL + runtime + tests (not README). Target SoC:
AXI4 interconnect, CVA6 host, Linux 6, separate scanout/display controller.
Goal: render to framebuffer in DRAM + basic 2D composition + OpenCL.

## Executive summary
- **Hardware graphics blocks are present** (raster, texture, OM) and are wired
  through DCRs. Tests confirm correct outputs in **simx** and **rtlsim** for
  raster/tex/OM and draw3d traces.
- **Control path is DCR write-only**, not AXI‑lite; SoC integration needs a
  small MMIO->DCR bridge.
- **AXI4 memory interface is single‑beat / fixed bursts**, which is correct
  but bandwidth‑limited; 1080p60 may be difficult without bursts or wider
  memory/interconnect.
- **Linux/Wayland stack is missing**: no DRM render driver, no dma‑buf, no
  sync primitives, no GEM buffer management. A render‑only driver + UMD is
  required.

## Capability matrix (HW/SW/testing vs target SoC)

| Area / Feature | HW status (RTL) | SW status (runtime/tests) | Tested (simx/rtlsim) | Evidence / Notes | Gaps / Next steps |
|---|---|---|---|---|---|
| Raster pipeline | **Yes** (`hw/rtl/raster/*`, `VX_raster_*`) | `tests/regression/raster` + draw3d | **simx** raster triangle, **rtlsim** via draw3d | `CONFIGS=-DEXT_RASTER_ENABLE` raster test; draw3d traces | OK for basic raster; add smaller rtlsim raster test if desired |
| Texture sampling | **Yes** (`hw/rtl/tex/*`, `VX_tex_*`) | `tests/regression/tex` + draw3d | **simx** tex soccer g1; **rtlsim** via draw3d box128 | `CONFIGS=-DEXT_TEX_ENABLE` tex test; draw3d box128 | OK; no Linux UMD path for tex state |
| Output Merger (OM) | **Yes** (`hw/rtl/om/*`, `VX_om_*`) | `tests/regression/om` | **simx** OM whitebox + depth/blend | `CONFIGS=-DEXT_OM_ENABLE` om test | OK; no Linux blend/format API yet |
| Caches (R/T/O caches) | **Yes** (`VX_config.vh` + cache RTL) | Configurable via `CONFIGS` | Covered indirectly by tests | draw3d + om/tex use caches by default | Add explicit cache on/off A/B tests in simx |
| 2D via 3D (blit/scale/compose) | **Indirect** (3D pipeline) | `cocogfx` used in tests for reference; draw3d supports textured quads | **simx** draw3d box/vase | 2D = special case of 3D; no separate blitter HW | Provide UMD/driver path to issue 2D draws |
| DMA / memory interface | **AXI4 full, single‑beat** (`VX_axi_adapter`) | Runtime uses physical buffers | **simx/rtlsim** OK | `awlen=0/arlen=0`, `burst=FIXED`, cache/prot=0 | For Linux perf, consider INCR bursts + coherency |
| DCR control path | **Write‑only DCR bus** (`Vortex_top` ports) | `vx_dcr_write` in runtime/tests | **simx/rtlsim** OK | No AXI‑lite | Need MMIO->DCR bridge (kernel driver) |
| OpenCL compute | **Yes** (core + ISA) | existing runtime + OpenCL tests (elsewhere) | Out of scope here | Vortex compute path works | Need Linux user‑mode stack |
| Wayland/DRM render node | **No** | **No** | N/A | No KMS/DRM in repo | Implement DRM render‑only driver + GEM + dma‑buf |
| dma‑buf/PRIME import/export | **No** | **No** | N/A | Not present | Add PRIME + sync fences |
| Sync (fences, timeline) | **No explicit** | **No** | N/A | Only runtime wait | Need Linux syncobj or timeline fence integration |
| Context isolation / MMU | **No** | **No** | N/A | Physical addresses in tests | Add IOMMU / SMMU or driver‑managed buffers |

## Tested coverage (commands + outputs)

### Microtests (draw3d, simx + rtlsim)
```
PATH=/home/svt/tools/verilator/bin:$PATH OSVERSION=ubuntu/focal \
  ./ci/skybox_microtests.sh
```
- simx: `tri8`, `tri64`, `vase32`, `box128` → PASS (sha matches ref)
- rtlsim: `tri8`, `box128` → PASS (sha matches ref)
- results: `build-xlen32-gfxmicro/artifacts/microtests/results.md`

### Raster (simx)
```
CONFIGS="-DEXT_RASTER_ENABLE" ./ci/blackbox.sh --driver=simx --app=raster \
  --args="-ttriangle.cgltrace -rtriangle_ref_128.png -o<out>"
```
- Output sha matches `tests/regression/raster/triangle_ref_128.png`.

### Texture (simx)
```
CONFIGS="-DEXT_TEX_ENABLE" ./ci/blackbox.sh --driver=simx --app=tex \
  --args="-isoccer.png -rsoccer_ref_g1.png -g1 -o<out>"
```
- Output sha matches `tests/regression/tex/soccer_ref_g1.png`.

### Output Merger (simx)
```
CONFIGS="-DEXT_OM_ENABLE" ./ci/blackbox.sh --driver=simx --app=om \
  --args="-rwhitebox_128.png -o<out>"
CONFIGS="-DEXT_OM_ENABLE" ./ci/blackbox.sh --driver=simx --app=om \
  --args="-d -rwhitebox_d_128.png -o<out>"
CONFIGS="-DEXT_OM_ENABLE" ./ci/blackbox.sh --driver=simx --app=om \
  --args="-b -rwhitebox_b_128.png -o<out>"
CONFIGS="-DEXT_OM_ENABLE" ./ci/blackbox.sh --driver=simx --app=om \
  --args="-db -rwhitebox_db_128.png -o<out>"
```
- All outputs match reference images.

## Gaps for Linux/Wayland
- **Kernel driver**: no DRM render node, GEM allocator, or IOCTL surface.
- **Buffer sharing**: no dma‑buf/PRIME import/export; no fence/sync support.
- **MMU/coherency**: hardware assumes physical addresses; need IOMMU/SMMU or
  software‑managed physically‑contiguous buffers.
- **AXI performance**: single‑beat fixed bursts may limit bandwidth; for 1080p60
  a burst‑capable adapter is likely required.

## Risks
- **AXI single‑beat**: limits throughput and increases interconnect overhead.
- **DCR write‑only**: no register readback for debug or capability discovery.
- **No preemption/context switching**: limits multi‑process usage under Linux.

## Stage 06 plan (proposed)
1. **AXI burst support** in `VX_axi_adapter.sv` (INCR bursts, max outstanding).
2. **MMIO->DCR bridge** (AXI‑lite or simple CSR interface) + DCR readback.
3. **Minimal Linux UMD**: user‑space lib to allocate buffers + program DCRs.
4. **Render‑only DRM driver PoC**: GEM + dma‑buf export + syncobj fence.
5. **Perf microbench**: 2D blit/scale tests to estimate 1080p60 feasibility.

