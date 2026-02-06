# Skybox docs index

This folder contains both general Vortex documentation and Skybox‑specific
graphics notes. The sections below are the entry points used in our test and
integration work.

## Skybox graphics notes (source‑based)
- `skybox_feature_map.md` — graphics block map from RTL (raster/tex/OM, caches).
- `skybox_hw_sw_interface.md` — AXI/DCR integration + SW control surface.
- `skybox_linux_graphics_readiness.md` — Linux/Wayland readiness report, gaps,
  risks, and next‑stage plan.
- `skybox_linux_graphics_readiness_ru.md` — RU/extended readiness report
  (separate scanout/display controller assumed).
- `skybox_rtl_inventory_ru.md` — source-based RTL inventory (Stage 09b).
- `skybox_rtl_modules_by_subsystem.md` — generated module grouping by subsystem.
- `skybox_vulkan_opengl_keyword_audit_ru.md` — keyword presence audit (HW-only
  + whole-repo scopes).
- `skybox_hw_gfx_driver_primitives_ru.md` — HW primitive readiness matrix for a
  future Linux render-only Vulkan/OpenGL stack.

## Test entry points
- `ci/skybox_microtests.sh` — simx/rtlsim microtests with sha checks.
  - Results: `build-*/artifacts/microtests/results.md` and `.csv`.
- `tests/regression/draw3d` — 3D traces + reference PNGs.
- `tests/regression/raster` — raster unit tests.
- `tests/regression/tex` — texture unit tests.
- `tests/regression/om` — output merger tests (color/depth/blend).

## General docs
- `install_vortex.md` — install/build overview.
- `simulation.md` — simulator usage.
- `debugging.md` — debug workflows.
