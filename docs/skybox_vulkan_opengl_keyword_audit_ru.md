# Skybox Vulkan/OpenGL keyword audit (RU)

- Scope A (HW-only): `hw/**`
- Scope B (Whole repo): all files except `.git`, `third_party`, `build*`, `*/artifacts/*`
- Max scanned file size: `1000000` bytes
- Keywords: `vulkan`, `vk`, `egl`, `gles`, `mesa`, `drm`

## Summary

| Keyword | HW-only hits | Whole-repo hits | Notes |
|---|---:|---:|---|
| `vulkan` | 0 | 27 | No HW evidence |
| `vk` | 0 | 9 | No HW evidence |
| `egl` | 0 | 9 | No HW evidence |
| `gles` | 0 | 7 | No HW evidence |
| `mesa` | 0 | 14 | No HW evidence |
| `drm` | 0 | 29 | No HW evidence |

## HW-only evidence

### `vulkan`

| File | Hits |
|---|---:|
| - | 0 |

| File:line | Context |
|---|---|
| - | - |

### `vk`

| File | Hits |
|---|---:|
| - | 0 |

| File:line | Context |
|---|---|
| - | - |

### `egl`

| File | Hits |
|---|---:|
| - | 0 |

| File:line | Context |
|---|---|
| - | - |

### `gles`

| File | Hits |
|---|---:|
| - | 0 |

| File:line | Context |
|---|---|
| - | - |

### `mesa`

| File | Hits |
|---|---:|
| - | 0 |

| File:line | Context |
|---|---|
| - | - |

### `drm`

| File | Hits |
|---|---:|
| - | 0 |

| File:line | Context |
|---|---|
| - | - |

## Whole-repo evidence (top files)

### `vulkan`

| File | Hits |
|---|---:|
| `docs/skybox_linux_graphics_readiness_ru.md` | 10 |
| `scripts/keyword_audit.py` | 6 |
| `docs/README.md` | 2 |
| `docs/skybox_rtl_inventory_ru.md` | 2 |
| `README.md` | 1 |
| `docs/skybox_hw_gfx_driver_primitives_ru.md` | 1 |

### `vk`

| File | Hits |
|---|---:|
| `tests/regression/draw3d/carnival.cgltrace` | 2 |
| `tests/regression/raster/carnival.cgltrace` | 2 |
| `scripts/keyword_audit.py` | 2 |
| `tests/regression/draw3d/polybump.cgltrace` | 1 |

### `egl`

| File | Hits |
|---|---:|
| `docs/skybox_linux_graphics_readiness_ru.md` | 5 |
| `scripts/keyword_audit.py` | 2 |

### `gles`

| File | Hits |
|---|---:|
| `docs/skybox_linux_graphics_readiness_ru.md` | 2 |
| `scripts/keyword_audit.py` | 2 |
| `sim/common/gfxutil.cpp` | 1 |

### `mesa`

| File | Hits |
|---|---:|
| `docs/skybox_linux_graphics_readiness_ru.md` | 10 |
| `scripts/keyword_audit.py` | 2 |
| `docs/skybox_hw_gfx_driver_primitives_ru.md` | 1 |

### `drm`

| File | Hits |
|---|---:|
| `docs/skybox_linux_graphics_readiness_ru.md` | 15 |
| `docs/skybox_linux_graphics_readiness.md` | 4 |
| `scripts/keyword_audit.py` | 2 |
| `docs/skybox_hw_gfx_driver_primitives_ru.md` | 1 |

