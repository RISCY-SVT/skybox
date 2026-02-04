# Skybox HW/SW interface + AXI4 reconnaissance (source-based)

This document is derived from RTL + tests/runtime code, not README. It focuses
on integration signals and the graphics control surface used by draw3d.

## AXI4 / SoC integration points (RTL)

### Suggested top-level for AXI4 memory
- **`hw/syn/xilinx/sandbox/Vortex_top.v`**
  - Exposes a full AXI4 memory interface (`m_axi_mem_*`) plus a **separate DCR write bus**:
    `dcr_wr_valid/addr/data`.
  - Instantiates `Vortex_wrap`, which in turn instantiates `Vortex_axi`.
- **`hw/syn/xilinx/sandbox/Vortex_wrap.sv`**
  - Fan-out and parameterization for AXI width/ID/banks.
  - Bridges the AXI interface into `Vortex_axi` and forwards DCR writes.
- **`hw/rtl/Vortex_axi.sv`**
  - Bridges internal memory requests/responses to AXI4 via:
    - `hw/rtl/libs/VX_mem_adapter.sv` (data width + addr/tag adaptation)
    - `hw/rtl/libs/VX_axi_adapter.sv` (AXI channelization)

### AXI channel behavior (from `VX_axi_adapter.sv`)
- **Single-beat only**: `awlen=0`, `arlen=0`, `wlast=1`, `rlast` expected.
- **Burst type**: `awburst=2'b00`, `arburst=2'b00` (FIXED).
- **Size**: `awsize/arsize = log2(DATA_WIDTH/8)`.
- **Cache/Prot/QoS/Region**: all zeros.
- **Write response**: always ready; asserts `bresp==0`.
- **Read response**: expects `rresp==0`, `rlast==1`.
- **IDs**: `awid/arid` driven from request tags (tag buffer used if width differs).
- **Banks**: optional interleave (`BANK_INTERLEAVE`) or contiguous banking.

**Implication for SoC integration**:
The AXI memory interface is **full AXI4** but uses only single-beat, fixed bursts.
If your interconnect or memory controller expects INCR bursts, you’ll need to
extend `VX_axi_adapter.sv` to emit bursts. As-is, it should work with an AXI4
interconnect that supports FIXED bursts and single beats.

### Control path (DCR/CSR)
The DCR interface is **separate** from AXI4 memory:
- `Vortex_top.v` exposes `dcr_wr_valid`, `dcr_wr_addr`, `dcr_wr_data`.
- No AXI-lite/MMIO control path is provided by default.
**SoC requirement**: add a small MMIO/DCR bridge (e.g., AXI-lite -> DCR write).

## Graphics HW/SW control surface (from draw3d + sim models)

### Where SW programs graphics state
- `tests/regression/draw3d/main.cpp`
  - DCR write macros:
    - `RASTER_DCR_WRITE(...)`, `TEX_DCR_WRITE(...)`, `OM_DCR_WRITE(...)`
  - Key writes:
    - Raster: `VX_DCR_RASTER_TBUF_ADDR`, `VX_DCR_RASTER_TILE_COUNT`,
      `VX_DCR_RASTER_PBUF_ADDR`, `VX_DCR_RASTER_PBUF_STRIDE`,
      `VX_DCR_RASTER_SCISSOR_X/Y`
    - OM: `VX_DCR_OM_CBUF_ADDR`, `VX_DCR_OM_CBUF_PITCH`,
      `VX_DCR_OM_CBUF_WRITEMASK`, `VX_DCR_OM_ZBUF_ADDR`,
      `VX_DCR_OM_ZBUF_PITCH`, depth/stencil/blend registers
    - TEX: `VX_DCR_TEX_STAGE`, `VX_DCR_TEX_LOGDIM`, `VX_DCR_TEX_FORMAT`,
      `VX_DCR_TEX_WRAP`, `VX_DCR_TEX_FILTER`, `VX_DCR_TEX_ADDR`,
      `VX_DCR_TEX_MIPOFF(i)`
- `runtime/include/vortex.h`: `vx_dcr_read/write` interface used by apps/tests.
- `sim/common/graphics.h`: reference DCR state objects:
  `RasterDCRS`, `TexDCRS`, `OMDCRS`.

### Buffer formats / pitch
`draw3d` programs:
- **Color buffer**: base address + pitch (bytes/line); format implied by DCRs.
- **Depth buffer**: base address + pitch (bytes/line); enabled/disabled via
  depth DCRs.
- **Texture**: base address + format + wrap/filter + log2 dimensions.

### SW fallbacks / isolation knobs
`tests/regression/draw3d/main.cpp` supports:
- `-x` → `sw_rast` (software raster)
- `-u` → `sw_tex` (software texture)
- `-y` → `sw_om` (software output merger)
These flags are carried in `kernel_arg` and used to isolate or bypass HW units.

### Relevant RTL blocks
See `docs/skybox_feature_map.md` for the block map. Key RTL control modules:
- `hw/rtl/raster/VX_raster_dcr.sv`
- `hw/rtl/tex/VX_tex_dcr.sv`
- `hw/rtl/om/VX_om_dcr.sv`

## Practical integration checklist
1. **AXI4 memory**: connect `Vortex_top.v` `m_axi_mem_*` to SoC interconnect.
2. **DCR/MMIO bridge**: provide a simple write-only register path to DCRs.
3. **Framebuffer in DRAM**: map CBUF/ZBUF/texture buffers in system RAM; use
   `draw3d` as a reference for DCR programming sequence.
4. **Feature isolation**: use `sw_rast/sw_tex/sw_om` to isolate blocks.

