# Skybox graphics feature map (source-based)

This map is derived from RTL and sim sources (not README). Key entry points and configuration knobs:

## Gating / enablement
- `hw/rtl/VX_config.vh`: `EXT_GFX_ENABLE` defines `EXT_TEX_ENABLE`, `EXT_RASTER_ENABLE`, `EXT_OM_ENABLE`.
- ISA flags: `ISA_EXT_TEX`, `ISA_EXT_RASTER`, `ISA_EXT_OM` bits are set when enabled.

## Top-level integration
- `hw/rtl/Vortex.sv`: includes `VX_tex_define.vh`, `VX_raster_define.vh`, `VX_om_define.vh` only when corresponding EXT_* enables are set.
- `hw/rtl/VX_cluster.sv`, `hw/rtl/VX_socket.sv`: per-socket bus interfaces for raster/tex/om and perf IFs.
- `hw/rtl/core/VX_core_top.sv` and `hw/rtl/core/VX_core.sv`: connect graphics buses/perf IFs into the core.
- `hw/rtl/core/VX_sfu_unit.sv`: instantiates **VX_tex_agent**, **VX_raster_agent**, **VX_om_agent** (per-core SFU side), which bridge execute/commit interfaces to the graphics buses.
- `hw/rtl/VX_graphics.sv`: the graphics fabric for a cluster; instantiates units and caches and arbitrates per-socket buses to units.

## Graphics blocks (RTL)
- **Raster**: `hw/rtl/raster/` (VX_raster_unit, VX_raster_slice, VX_raster_edge, VX_raster_extents, VX_raster_te, VX_raster_be, VX_raster_qe, VX_raster_mem, VX_raster_dcr/csr, VX_raster_arb).
- **Texture**: `hw/rtl/tex/` (VX_tex_unit, VX_tex_sampler, VX_tex_addr, VX_tex_stride, VX_tex_mem, VX_tex_dcr/csr, VX_tex_arb, VX_tex_wrap, VX_tex_sat, VX_tex_format).
- **Output merger (OM)**: `hw/rtl/om/` (VX_om_unit, VX_om_mem, VX_om_ds, VX_om_compare, VX_om_blend, VX_om_logic_op, VX_om_stencil_op, VX_om_dcr/csr, VX_om_arb).
- **SimX models**: `sim/simx/raster_unit.cpp`, `sim/simx/tex_unit.cpp`, `sim/simx/om_unit.cpp`.

## Key configuration knobs (from `VX_config.vh`)
- Core topology: `NUM_CLUSTERS`, `NUM_CORES`, `NUM_WARPS`, `NUM_THREADS`, `SOCKET_SIZE`.
- Raster: `NUM_RASTER_UNITS`, `RASTER_NUM_SLICES`, `RASTER_TILE_LOGSIZE`, `RASTER_BLOCK_LOGSIZE`, `RASTER_MEM_QUEUE_SIZE`, `RASTER_QUAD_FIFO_DEPTH`, `RASTER_MEM_FIFO_DEPTH`.
- Texture: `NUM_TEX_UNITS`, `TEX_REQ_QUEUE_SIZE`, `TEX_MEM_QUEUE_SIZE`.
- OM: `NUM_OM_UNITS`, `OM_MEM_QUEUE_SIZE`.
- Caches: `NUM_TCACHES`, `NUM_RCACHES`, `NUM_OCACHES` and the corresponding cache sizes/ways/line sizes in `VX_config.vh`.

## DCR/CSR control path
- Each block has CSR/DCR modules: `VX_*_dcr.sv`, `VX_*_csr.sv` (raster/tex/om).
- DCR address ranges are used to split writes (see `VX_graphics.sv`).

## 2D fast-path assessment
- No dedicated RTL “blitter/2D” pipeline found in `hw/rtl/` or `sim/simx/`.
- 2D operations appear to be a special case of the graphics pipeline or handled in software (host uses `cocogfx` blitter in tests/regression/draw3d).

## Entry points for tests
- `tests/regression/draw3d` uses `draw3d` app + `.cgltrace` inputs, with reference PNGs for comparison.
- CI script `ci/regression.sh.in` shows typical gfx configs: `CONFIGS="-DEXT_GFX_ENABLE"` and variants with raster units/caches disabled.
