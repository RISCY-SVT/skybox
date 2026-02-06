# Skybox HW primitives for future Vulkan/OpenGL stack (RU, hardware-focused)

## Scope and basis

- Focus: hardware primitives/contract only (no Mesa/DRM implementation details).
- Basis of truth: RTL code in `hw/rtl/**` and wrappers in `hw/rtl/afu/**`.
- Snapshot SHA: `a6f311d6e3b8e2a57c8c68a8e61609c1a715f764`.

## Primitive readiness matrix

| Primitive / requirement | Status | RTL evidence | What it means for future driver |
|---|---|---|---|
| Command submission model | 🟡 Partial | `Vortex` DCR write ingress (`hw/rtl/Vortex.sv:50`), XRT control (`hw/rtl/afu/xrt/VX_afu_ctrl.sv:47`) | Submission exists via DCR + wrapper control, but SoC-native MMIO contract must be defined. |
| Render pipeline blocks (raster/tex/om) | ✅ Present | `VX_graphics` and `VX_raster_*`, `VX_tex_*`, `VX_om_*` (`hw/rtl/VX_graphics.sv:16`) | Hardware render path exists for render-only node. |
| Memory path to external RAM | ✅ Present | `Vortex_axi` + `VX_axi_adapter` (`hw/rtl/Vortex_axi.sv:16`, `hw/rtl/libs/VX_axi_adapter.sv:17`) | Framebuffer-in-RAM rendering is feasible. |
| AXI4 features (burst/outstanding/error handling) | 🟡 Limited | `awlen/arlen=0`, `awburst/arburst=00`, assert-only error handling (`hw/rtl/libs/VX_axi_adapter.sv:179`, `hw/rtl/libs/VX_axi_adapter.sv:211`, `hw/rtl/libs/VX_axi_adapter.sv:203`) | Works functionally, but Linux-scale bandwidth/robustness likely needs richer AXI behavior. |
| Completion/fence signaling | 🟡 Partial | busy propagation (`hw/rtl/Vortex.sv:181`), fence wait trace (`hw/rtl/core/VX_lsu_slice.sv:507`), `ap_done` (`hw/rtl/afu/xrt/VX_afu_wrap.sv:115`) | Basic completion/fence behavior exists; timeline-style sync primitives are not evident. |
| Interrupt support | ✅ Present (wrapper-level) | `interrupt` signal in AFU wrappers (`hw/rtl/afu/xrt/VX_afu_wrap.sv:53`, `hw/rtl/afu/xrt/VX_afu_ctrl.sv:431`) | IRQ path exists for wrapper integration. |
| Cache management (flush/invalidate) | 🟡 Partial | cache flush modules (`hw/rtl/cache/VX_cache_flush.sv:16`, `hw/rtl/cache/VX_bank_flush.sv:16`) | Primitive exists, but software-visible Linux contract must be explicitly defined. |
| Per-process GPU VA / MMU / address-space isolation | ❌ Not evident | No explicit GPU MMU/IOMMU RTL primitive found in current inventory | Multi-process isolation and secure userspace execution need new HW or strong platform support. |
| Context preemption / fine-grained scheduling isolation | ❌ Not evident | No explicit context-save/preemption control surface in RTL inventory | Driver model will be limited to coarse job scheduling without preemption. |
| Structured fault reporting (page/access/protocol faults) | ❌ Not evident | AXI asserts/error checks exist, but no robust fault telemetry block exposed (`hw/rtl/libs/VX_axi_adapter.sv:203`) | Linux UMD/KMD fault handling will require extra HW-visible fault registers/events. |
| Timestamp/query primitives for sync | ❌ Not evident | PERF counters exist (`PERF_ENABLE` paths) but no explicit per-job timestamp/query interface | Need additional counters/register protocol for modern API synchronization telemetry. |

## Notes for Stage 10+

- For Linux render-only integration, first target should be a minimal SoC-native control wrapper (AXI-Lite/MMIO) with explicit job queue, completion IRQ, and fault/status registers.
- AXI bridge behavior should be upgraded beyond single-beat FIXED requests for practical graphics bandwidth.
- Add formalized HW contract doc for flush/fence/cache-coherency with host CPU interconnect.
