# Skybox RTL inventory (RU, Stage 09)

## Basis of truth

- Snapshot date: `2026-02-06T10:09:28+01:00`
- Skybox git SHA: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
- Submodules:
  - `third_party/cocogfx` = `e5a599b8c002ec9d792bbb691ac8563bb3fa7372`
  - `third_party/cvfpu` = `a6af691551ffbd76d5d9cf30774d3295a41615e4`
  - `third_party/cvfpu/src/common_cells` = `6aeee85d0a34fedc06c14f04fd6363c9f7b4eeea`
  - `third_party/cvfpu/src/fpu_div_sqrt_mvp` = `86e1f558b3c95e91577c41b2fc452c86b04e85ac`
  - `third_party/cvfpu/tb/flexfloat` = `28be2d4fbf41b38fc37763bb6e90a1c88f6aaa61`
  - `third_party/ramulator` = `e62c84a6f0e06566ba6e182d308434b4532068a5`
  - `third_party/softfloat` = `b51ef8f3201669b2288104c28546fc72532a1ea4`
- Источник истины: RTL и runtime код:
  - `hw/rtl/**`
  - `runtime/**`
  - `ci/skybox_microtests.sh`, `ci/regression.sh.in` (как доказательство фактического тестового покрытия)
- Документация (`README`, `docs/*.md`) использовалась только как вторичный ориентир.

---

### 1) Top-level compute fabric (Vortex / Cluster / Socket / Core)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level: custom RISC-V GPU-like manycore, DCR+CSR control surface
- RTL entry points:
  - top module: `Vortex` (`hw/rtl/Vortex.sv:28`)
  - hierarchy roots: `VX_cluster` (`hw/rtl/VX_cluster.sv:34`), `VX_socket` (`hw/rtl/VX_socket.sv:16`)
  - ключевые include/ifdef:
    - `EXT_TEX_ENABLE`, `EXT_RASTER_ENABLE`, `EXT_OM_ENABLE` (`hw/rtl/Vortex.sv:16`, `hw/rtl/Vortex.sv:20`, `hw/rtl/Vortex.sv:24`)
- Interfaces:
  - memory interface: internal VX mem bus mapped to external mem request/response (`hw/rtl/Vortex.sv:35`, `hw/rtl/Vortex.sv:136`)
  - control: DCR write-only ingress (`dcr_wr_valid/addr/data`) (`hw/rtl/Vortex.sv:50`)
  - clocks/resets: single `clk/reset`
- Config knobs:
  - scale knobs: `NUM_CLUSTERS`, `NUM_CORES`, `SOCKET_SIZE` (`hw/rtl/VX_config.vh:95`, `hw/rtl/VX_config.vh:99`, `hw/rtl/VX_config.vh:116`)
  - graphics enable chain via config macros (`hw/rtl/VX_config.vh:35`)
- Features matrix:
  - ✅ Multi-cluster hierarchy и генерация кластеров (`hw/rtl/Vortex.sv:152`)
  - ✅ DCR fanout в кластеры через `VX_dcr_bus_if` (`hw/rtl/Vortex.sv:145`, `hw/rtl/Vortex.sv:157`)
  - 🟡 Внешний control path только write-side в top (readback на уровне Vortex не выведен)
  - ❌ Прямого MMIO/AXI-Lite интерфейса у `Vortex` нет (это решается wrapper/AFU)
- Known limitations / hazards:
  - DCR readback зависит от runtime shadow state (см. блок 3), не от явного RTL read-порта.
- Coverage by our tests:
  - `vecadd` simx/rtlsim (Stage 09 smoke) покрывает compute path + cluster/core execution.
  - draw3d microtests покрывают compute + graphics path в кластере.
- TODO / what to test next:
  - Проверка масштабирования по `NUM_CLUSTERS>1`, `NUM_CORES>1` на rtlsim.
  - Directed test на корректность DCR broadcast в multi-cluster.

---

### 2) AXI4 / SoC bridge (Vortex_axi + AXI adapters + AFU wrapper)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level:
    - AXI4 master: `Vortex_axi` / `VX_axi_adapter`
    - AXI4-Lite slave: XRT AFU wrapper
- RTL entry points:
  - top module for AXI memory bridge: `Vortex_axi` (`hw/rtl/Vortex_axi.sv:16`)
  - bridge helpers: `VX_mem_adapter` (`hw/rtl/libs/VX_mem_adapter.sv:17`), `VX_axi_adapter` (`hw/rtl/libs/VX_axi_adapter.sv:17`)
  - platform wrapper: `VX_afu_wrap` (`hw/rtl/afu/xrt/VX_afu_wrap.sv:16`)
- Interfaces:
  - AXI write channels AW/W/B and read channels AR/R fully wired at signal level (`hw/rtl/Vortex_axi.sv:28`)
  - DCR write pass-through in `Vortex_axi` (`hw/rtl/Vortex_axi.sv:77`)
  - AXI4-Lite control in AFU wrapper (`hw/rtl/afu/xrt/VX_afu_wrap.sv:35`)
- Config knobs:
  - `AXI_DATA_WIDTH`, `AXI_ADDR_WIDTH`, `AXI_TID_WIDTH`, `AXI_NUM_BANKS` (`hw/rtl/Vortex_axi.sv:17`)
  - adapter buffering: `RSP_OUT_BUF` (`hw/rtl/libs/VX_axi_adapter.sv:26`)
- Features matrix:
  - ✅ AXI multi-bank interface присутствует (`m_axi_* [NUM_BANKS]`)
  - 🟡 Single-beat only in current adapter:
    - `awlen=0`, `arlen=0` (`hw/rtl/libs/VX_axi_adapter.sv:179`, `hw/rtl/libs/VX_axi_adapter.sv:211`)
    - `awburst=2'b00`, `arburst=2'b00` (FIXED) (`hw/rtl/libs/VX_axi_adapter.sv:181`, `hw/rtl/libs/VX_axi_adapter.sv:213`)
  - 🟡 Write response фактически игнорируется, только assert на `bresp==0` (`hw/rtl/libs/VX_axi_adapter.sv:197`)
  - ✅ AXI-Lite control path есть в AFU wrapper (`hw/rtl/afu/xrt/VX_afu_wrap.sv:35`)
- Known limitations / hazards:
  - Потенциальный bottleneck по bandwidth/latency из-за single-beat FIXED bursts.
  - `B` channel не используется для полноценной flow/error handling логики.
  - NEEDS CONFIRMATION: лимиты outstanding и ordering guarantees в полном SoC interconnect контексте.
- Coverage by our tests:
  - simx/rtlsim smoke (`vecadd`, draw3d microtests) покрывает runtime path, но не полноценный external AXI fabric.
  - Нет отдельного directed AXI protocol compliance теста в репозитории.
- TODO / what to test next:
  - Directed AXI testbench для burst (INCR), reorder, multi-ID.
  - Измерения throughput на long linear traffic (L2/L3 + framebuffer workloads).
  - Проверка ошибок `bresp/rresp != 0` с injected faults.

---

### 3) HW/SW control surface (DCR + CSR + MPM perf)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level: custom DCR address map + CSR counters
- RTL entry points:
  - address map macros: `hw/rtl/VX_types.vh`
  - top DCR ingress: `hw/rtl/Vortex.sv:50`, `hw/rtl/Vortex_axi.sv:77`
  - DCR routing to graphics blocks: `hw/rtl/VX_graphics.sv:84`, `hw/rtl/VX_graphics.sv:201`, `hw/rtl/VX_graphics.sv:297`
- Interfaces:
  - DCR write bus (`VX_dcr_bus_if`), no explicit DCR read output from top module.
  - CSR/MPM query through runtime API.
- Config knobs:
  - DCR base states: startup/mpm (`hw/rtl/VX_types.vh:22`)
  - TEX/RASTER/OM DCR ranges (`hw/rtl/VX_types.vh:336`, `hw/rtl/VX_types.vh:356`, `hw/rtl/VX_types.vh:443`)
  - MPM class selection (`VX_DCR_BASE_MPM_CLASS`) (`hw/rtl/VX_types.vh:27`)
- Features matrix:
  - ✅ DCR map для graphics и base startup state определён в коде
  - ✅ Runtime инициализирует DCR состояния TEX/RASTER/OM (`runtime/stub/vortex.cpp:53`)
  - 🟡 `dcr_read` в runtime возвращает shadow `DeviceConfig`, а не явный RTL read-path (`runtime/simx/vortex.cpp:226`, `runtime/rtlsim/vortex.cpp:235`)
  - ✅ MPM class/counters используются runtime utils (`runtime/stub/utils.cpp`)
- Known limitations / hazards:
  - Риск рассинхронизации shadow DCR state и фактического RTL state при ошибках пути записи.
  - NEEDS CONFIRMATION: требуется ли hardware DCR readback для Linux production driver model.
- Coverage by our tests:
  - `ci/skybox_microtests.sh` фиксирует PERF/IPC и опирается на runtime counters.
  - vecadd simx/rtlsim smoke подтверждает базовый DCR startup path.
- TODO / what to test next:
  - Directed test: write/read consistency для DCR (если добавить hardware read path).
  - Негативные тесты на invalid DCR addr и side-effects.

---

### 4) Memory hierarchy (L1/L2/L3, local mem, interconnect, gbar)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level: custom memory fabric + cache hierarchy
- RTL entry points:
  - cache stack: `hw/rtl/cache/VX_cache*.sv`
  - mem fabric: `hw/rtl/mem/VX_mem_switch.sv`, `VX_mem_arb.sv`, `VX_lsu_adapter.sv`, `VX_local_mem*.sv`, `VX_gbar_*`
  - cluster wiring to L2: `hw/rtl/VX_cluster.sv:191`
- Interfaces:
  - VX mem bus interfaces between cores, localmem, caches, and external memory
  - optional graphics caches (TCACHE/RCACHE/OCACHE) feeding into L2 (`hw/rtl/VX_cluster.sv:166`, `hw/rtl/VX_cluster.sv:175`, `hw/rtl/VX_cluster.sv:184`)
- Config knobs:
  - `L1_DISABLE`, `LMEM_DISABLE`, `NUM_TCACHES`, `NUM_RCACHES`, `NUM_OCACHES`, sizes/ways/MSHR (`hw/rtl/VX_config.vh:131`, `hw/rtl/VX_config.vh:627`, `hw/rtl/VX_config.vh:658`, `hw/rtl/VX_config.vh:713`, `hw/rtl/VX_config.vh:766`)
- Features matrix:
  - ✅ L1/L2/L3 knobs and cache modules присутствуют
  - ✅ Local memory configurable banks/sizes (`VX_config.vh` LMEM section)
  - ✅ Graphics-side caches присутствуют и подключены
  - 🟡 NEEDS CONFIRMATION: host-side cache coherency contract для Linux SoC integration
  - 🟡 NEEDS CONFIRMATION: memory ordering corner-cases under heavy mixed gfx+compute traffic
- Known limitations / hazards:
  - При переключении host toolchain/runtime конфигов возможно смешивание несовместимых объектов (observed в Stage 09 smoke before clean).
- Coverage by our tests:
  - vecadd simx/rtlsim покрывает compute LSU/cache path.
  - draw3d microtests покрывают graphics cache path (TCACHE/RCACHE/OCACHE + L2).
- TODO / what to test next:
  - Stress-tests на MSHR saturation и bank conflicts.
  - Directed tests на flush/invalidate semantics (если нужны для Linux coherency model).
  - Separate perf matrix для cache on/off вариантов.

---

### 5) Graphics integration hub (`VX_graphics`)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level: fixed-function gfx blocks orchestrated around SFU lanes
- RTL entry points:
  - top module: `hw/rtl/VX_graphics.sv:16`
  - invoked from cluster: `hw/rtl/VX_cluster.sv:152`
- Interfaces:
  - per-socket buses for raster/tex/om
  - DCR address-range routing into raster/tex/om DCR buses
  - cache bus fanout to RCACHE/TCACHE/OCACHE clusters
- Config knobs:
  - `NUM_RASTER_UNITS`, `NUM_TEX_UNITS`, `NUM_OM_UNITS`
  - tile/slice config for raster (`RASTER_*`)
- Features matrix:
  - ✅ RASTER/TEX/OM units instantiated conditionally by extension ifdef (`hw/rtl/VX_graphics.sv:67`, `hw/rtl/VX_graphics.sv:169`, `hw/rtl/VX_graphics.sv:267`)
  - ✅ DCR range-based routing to each block (`hw/rtl/VX_graphics.sv:84`, `hw/rtl/VX_graphics.sv:201`, `hw/rtl/VX_graphics.sv:297`)
  - ✅ Per-block cache clusters present
  - 🟡 No dedicated display/scanout logic inside `VX_graphics` (render-only pipeline)
- Known limitations / hazards:
  - Для Linux display stack требуется separate KMS/scanout controller.
  - NEEDS CONFIRMATION: fairness/latency behavior across TEX/RASTER/OM under load.
- Coverage by our tests:
  - draw3d microtests (`tri8/tri64/vase32/box128`) directly exercise this block on simx/rtlsim.
- TODO / what to test next:
  - Add directed mixed-workload test where TEX+OM+RASTER saturate simultaneously.
  - Add performance counters dump per block under configurable unit counts.

---

### 6) Rasterizer block (`VX_raster_*`)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level: custom raster tile/slice pipeline
- RTL entry points:
  - top unit: `hw/rtl/raster/VX_raster_unit.sv:18`
  - main stages: `VX_raster_mem`, `VX_raster_extents`, `VX_raster_edge`, `VX_raster_slice`, `VX_raster_te`, `VX_raster_be`, `VX_raster_qe`
  - DCR/CSR: `VX_raster_dcr`, `VX_raster_csr`
- Interfaces:
  - raster bus in/out via `VX_raster_bus_if`
  - cache traffic via `cache_bus_if`
  - DCR control via `dcr_bus_if`
- Config knobs:
  - `RASTER_NUM_SLICES`, `RASTER_TILE_LOGSIZE`, `RASTER_BLOCK_LOGSIZE`, queue depths (`hw/rtl/VX_graphics.sv:95`)
- Features matrix:
  - ✅ Tile-based raster flow with edge/extents calculation (`hw/rtl/raster/VX_raster_unit.sv:138`)
  - ✅ DCR-driven operation (`hw/rtl/raster/VX_raster_unit.sv:63`)
  - 🟡 Runtime assert on tile evaluator fifo overflow indicates explicit pressure sensitivity (`hw/rtl/raster/VX_raster_te.sv:208`)
  - ✅ Regression hooks with raster-only configs exist (`ci/regression.sh.in:186`)
- Known limitations / hazards:
  - Pipeline overflow risk on certain workloads (assert-based detection).
  - NEEDS CONFIRMATION: coverage for degenerate primitives and extreme tile sizes.
- Coverage by our tests:
  - draw3d microtests cover raster pipeline in combined mode.
  - `ci/regression.sh.in` contains raster-only cases, but not all were re-run in Stage 09.
- TODO / what to test next:
  - Re-run raster-only regression matrix on both simx and rtlsim.
  - Add directed overflow/boundary tests for tile evaluator.

---

### 7) Texture block (`VX_tex_*`)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level: custom texture address + memory + sampler path
- RTL entry points:
  - top unit: `hw/rtl/tex/VX_tex_unit.sv:18`
  - main stages: `VX_tex_dcr`, `VX_tex_addr`, `VX_tex_mem`, `VX_tex_sampler`, `VX_tex_format`, `VX_tex_lerp`
  - csr file: `VX_tex_csr`
- Interfaces:
  - texture bus (`VX_tex_bus_if`)
  - cache bus (`cache_bus_if`)
  - DCR control via `dcr_bus_if`
- Config knobs:
  - `NUM_TEX_UNITS`, cache config `TCACHE_*`
  - texture stage/format/filter/wrap via DCR (`VX_DCR_TEX_*`)
- Features matrix:
  - ✅ Address generation + mip selection path (`hw/rtl/tex/VX_tex_unit.sv:105`)
  - ✅ Sampling path with interpolation modules (`hw/rtl/tex/VX_tex_unit.sv:185`)
  - 🟡 `VX_tex_csr` is mostly stub (`TODO`) (`hw/rtl/tex/VX_tex_csr.sv:45`)
  - ✅ DCR path actively wired and used (`hw/rtl/tex/VX_tex_unit.sv:48`)
- Known limitations / hazards:
  - CSR plane appears incomplete; control is primarily DCR-based.
  - NEEDS CONFIRMATION: formal coverage for all filter/wrap combinations.
- Coverage by our tests:
  - draw3d microtests (box/vase/triangle) exercise texture in realistic traces.
  - No dedicated texture-only directed test evidence in Stage 09 run.
- TODO / what to test next:
  - Add minimal texture-only microtests (wrap/filter matrix).
  - Verify mip-level edge cases and out-of-range coordinates.

---

### 8) Output Merger block (`VX_om_*`)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - external spec level: depth/stencil + blend + logic ops
- RTL entry points:
  - top unit: `hw/rtl/om/VX_om_unit.sv:18`
  - sub-blocks:
    - depth/stencil: `VX_om_ds`
    - blending: `VX_om_blend`, `VX_om_blend_func`, `VX_om_blend_multadd`, `VX_om_blend_minmax`
    - logic op: `VX_om_logic_op`
    - memory: `VX_om_mem`
- Interfaces:
  - om bus (`VX_om_bus_if`)
  - cache bus (`cache_bus_if`)
  - DCR control (`dcr_bus_if`)
- Config knobs:
  - `VX_DCR_OM_*` state range (`hw/rtl/VX_types.vh:443`)
- Features matrix:
  - ✅ Depth/stencil compare + ops implemented (`hw/rtl/om/VX_om_ds.sv:61`, `hw/rtl/om/VX_om_ds.sv:112`)
  - ✅ Blend and logic op modes implemented (`hw/rtl/om/VX_om_blend.sv:58`, `hw/rtl/om/VX_om_blend.sv:136`)
  - ✅ Write bypass optimization present (`hw/rtl/om/VX_om_unit.sv:219`)
  - 🟡 NEEDS CONFIRMATION: corner-case compatibility against external graphics API expectations (full blend state space)
- Known limitations / hazards:
  - Correctness depends on DCR state programming; no separate high-level state validation layer in RTL.
- Coverage by our tests:
  - draw3d microtests (including alpha/depth use in traces) touch OM path.
  - No explicit standalone OM-only test in Stage 09 run.
- TODO / what to test next:
  - Directed OM tests for depth/stencil edge cases and blend mode matrix.
  - Stress test on simultaneous depth+stencil+blend writes.

---

### 9) FPU block (`VX_fpu_*`, cvfpu integration)

- Version/Revision:
  - skybox git: `c7be83b8c0add586789fcfc0c26e7c75dc5922f8`
  - related submodule: `third_party/cvfpu` = `a6af691551ffbd76d5d9cf30774d3295a41615e4`
  - external spec level: RISC-V F/D extensions path in execution core
- RTL entry points:
  - core-side unit: `hw/rtl/core/VX_fpu_unit.sv:16`
  - backend options in fpu dir (`VX_fpu_fpnew`, `VX_fpu_dsp`, `VX_fpu_dpi`)
- Interfaces:
  - FPU CSR interface: `VX_fpu_csr_if`
  - integrated into execute path (`hw/rtl/core/VX_execute.sv:99`)
- Config knobs:
  - `EXT_F_ENABLE`, `EXT_D_ENABLE` and capability bits in `MISA` composition (`hw/rtl/VX_config.vh:46`, `hw/rtl/VX_config.vh:52`, `hw/rtl/VX_config.vh:997`, `hw/rtl/VX_config.vh:999`)
- Features matrix:
  - ✅ Multiple FPU implementations present in RTL
  - ✅ Integrated into core execution + CSR plumbing
  - 🟡 NEEDS CONFIRMATION: точный runtime/backend selection policy между `fpnew/dsp/dpi` в конкретном build profile
  - ❌ Stage 09 не включал отдельный FP-focused directed test
- Known limitations / hazards:
  - Возможна конфигурационная чувствительность (backend-dependent behavior/perf).
- Coverage by our tests:
  - vecadd OpenCL smoke косвенно проходит через FP-capable toolchain path, но не является исчерпывающим FPU validation.
- TODO / what to test next:
  - Add rv32f/rv32d directed tests under simx/rtlsim with per-backend comparison.
  - Compare numeric corner-cases against reference (NaN/Inf/denorm handling).

---

## Сводная таблица всех блоков

| Block | RTL top modules | Key ifdef/params | Status (✅/🟡/❌) | Tested? | Notes / gaps |
|---|---|---|---|---|---|
| Top compute fabric | `Vortex`, `VX_cluster`, `VX_socket`, `VX_core*` | `NUM_CLUSTERS`, `NUM_CORES`, `SOCKET_SIZE` | ✅ | ✅ (`vecadd`, draw3d path) | DCR readback path не явный в top |
| AXI/SoC bridge | `Vortex_axi`, `VX_axi_adapter`, `VX_mem_adapter`, `VX_afu_wrap` | `AXI_*`, `RSP_OUT_BUF` | 🟡 | 🟡 (functional smoke only) | Single-beat FIXED burst, limited response handling |
| DCR/CSR control | `VX_types.vh`, `VX_dcr_bus_if`, runtime dcr APIs | `VX_DCR_*`, `VX_CSR_*` | 🟡 | ✅ (runtime init/perf) | Runtime shadow `dcr_read`; NEEDS CONFIRMATION for HW readback needs |
| Memory hierarchy | `VX_cache*`, `VX_mem_*`, `VX_local_mem*`, `VX_gbar_*` | `L1/L2/L3`, `LMEM_*`, `*CACHE_*` | ✅ | ✅ (vecadd + draw3d microtests) | Coherency contract with host fabric needs validation |
| Graphics hub | `VX_graphics` | `EXT_RASTER/TEX/OM_ENABLE`, `NUM_*_UNITS` | ✅ | ✅ (draw3d microtests) | Render-only; no scanout block |
| Raster block | `VX_raster_unit`, `VX_raster_*` | `RASTER_*` | ✅ | ✅ (draw3d), 🟡 (raster-only not rerun here) | Overflow assert path needs stress testing |
| Texture block | `VX_tex_unit`, `VX_tex_*` | `VX_DCR_TEX_*`, `NUM_TEX_UNITS` | 🟡 | ✅ (draw3d) | `VX_tex_csr` has TODO/stub |
| OM block | `VX_om_unit`, `VX_om_*` | `VX_DCR_OM_*`, `NUM_OM_UNITS` | ✅ | ✅ (draw3d) | Need dedicated OM matrix tests |
| FPU block | `VX_fpu_unit`, `VX_fpu_*` | `EXT_F_ENABLE`, `EXT_D_ENABLE` | 🟡 | 🟡 (indirect) | Backend selection/coverage needs dedicated tests |

---

## NEEDS CONFIRMATION register

- NEEDS CONFIRMATION: полный ordering/coherency contract AXI path при интеграции с Linux SoC interconnect.
- NEEDS CONFIRMATION: требуется ли hardware DCR readback для production Linux driver model (vs runtime shadow state).
- NEEDS CONFIRMATION: исчерпывающее покрытие filter/wrap/mip corner cases для TEX.
- NEEDS CONFIRMATION: backend selection logic and equivalence для FPU (`fpnew/dsp/dpi`) в production configs.
