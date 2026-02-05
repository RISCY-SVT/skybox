> **RU report (extended).** Scanout/display controller is assumed to be separate; this report covers GPU render/2D/compute only.

# Skybox как GPU‑рендер для Linux 6 (Wayland): готовность, пробелы, минимальные добавления (обновлено по Stage 05)

> Контекст: наш SoC = **CVA6 + AXI4**, **Linux 6.x**, **scanout/display контроллер** (DP/HDMI/LCD) будет **отдельным** блоком, который читает framebuffer из памяти.  
> Здесь оценивается только **GPU‑рендер/2D/compute** (Skybox), не KMS/scanout.

## 0) Что проверено на этом этапе (Stage 03–05): фактология из прогонов

**Базовая жизнеспособность репозитория на Ubuntu 24.04:**
- `develop` ветка собирается и проходит smoke (simx/rtlsim) при известных workaround’ах (`--osversion=ubuntu/focal`, CC/CXX=gcc/g++).
- Подмодули приведены к clean‑состоянию (нет `M`, `??`, `+/-` в `git submodule status --recursive`).

**Графический пайплайн (минимальная функциональность):**
- `draw3d` в SimX с `-DEXT_GFX_ENABLE` рендерит сцену из `tekkaman.cgltrace` → получается корректный `output.png` (256×256).
- Микротесты (SimX): `tri8`, `tri64`, `vase32`, `box128` → PNG совпадает с reference по sha256.
- Микротесты (RTLSIM): `tri8`, `box128` → PNG совпадает с reference по sha256.
- Доп. «whitebox» тесты в SimX (Stage 05) с sha256‑сравнением:
  - `raster` (треугольник) → OK
  - `tex` (семплинг текстуры) → OK
  - `om` (depth/blend) → OK

**Важно:** все проверки выше — это **симуляторы** (SimX/Verilator RTLSIM) + сравнение PNG. Это хорошая базовая регрессия, но **не подтверждение** реального тайминга/пропускной способности/кохерентности на SoC.

---

## 1) Что «минимально нужно» для Linux‑графики (Wayland) при раздельном scanout

Для Wayland в нормальном (не «fbdev‑only») сценарии обычно нужны:

### 1.1 Kernel space: DRM (render‑only) + buffer sharing
1) **DRM render node**: отдельный `/dev/dri/renderD*` для вычислений/рендера без прав на modeset. В DRM есть явная модель «render node / render-only» устройств (флаг `DRIVER_RENDER`).  
2) **GEM buffer objects** (или TTM) для выделения/маппинга GPU‑буферов. В современном DRM `DRIVER_GEM` — база для таких драйверов.  
3) **PRIME / dma‑buf** для обмена буферами между «рендер‑драйвером» и «scanout/KMS‑драйвером» (наш DP‑контроллер). PRIME в DRM опирается на dma‑buf и reservation/fence для синхронизации.  
4) **Синхронизация**: минимум — корректные implicit‑fences через reservation objects; лучше иметь опцию explicit sync через `drm_syncobj`/sync_file (особенно если целиться в Vulkan/современные compositor’ы).

### 1.2 User space: Mesa/GBM/EGL (или Vulkan ICD)
Чтобы Wayland compositor мог использовать GPU, чаще всего нужен стек:
- **Mesa driver** (Gallium/Vulkan) + **EGL** + **GBM** (особенно для DRM/KMS‑путей).
- Для split display/render в экосистеме Mesa существует инфраструктура **renderonly/KMSRO**, которая именно про «рендер‑драйвер» + «отдельный KMS‑драйвер» и общий буферный обмен.

> Отдельно: авторы проекта публично заявляют про Vulkan‑ориентированный Skybox и поддержку Vulkan API (в публикациях), но это **не означает** «готов Mesa/DRM‑драйвер в mainline Linux». Это скорее исследовательский full‑stack для FPGA/хоста.

---

## 2) Что есть в Skybox «уже сейчас» (с точки зрения HW‑функций)

По репозиторию Skybox/Vortex заявлено: RISC‑V GPU + OpenCL 1.2 + «optional graphics rasterizer, texture, and OM units».

По нашим фактическим тестам/прогонам (см. раздел 0) подтверждено:
- **Fixed‑function rasterizer** работает на трассах.
- **Texture sampling** работает на тесте с `soccer.png`.
- **OM (depth/blend)** работает на тестах OM.
- Выходной формат в артефактах — **RGBA PNG**, т.е. render target в тестах соответствует типичным 32‑битным форматам.

### 2D ускорение: что реально означает «есть/нет»
- В Skybox **нет выделенного 2D BLT‑движка** (bitblt/fill/stretch) как в классических 2D IP (Vivante GC, ARM 2D, etc.).
- Но **2D‑ускорение возможно через 3D‑путь**: рисование прямоугольников (двух треугольников) с текстурами/альфа‑блендингом — это то, как современные compositor’ы фактически и делают 2D‑композицию.

Вывод: аппаратно «кирпичики» для 2D‑композиции **есть** (raster+tex+blend), но «готового Linux‑пути» до Wayland пока **нет**.

---

## 3) Capability matrix: минимально необходимое для Linux/Wayland vs Skybox (на сегодня)

Легенда:
- ✅ есть (и/или уже протестировано в Stage 05)
- ⚠️ частично/заявлено/есть в коде, но не доведено до Linux‑стека или не протестировано нами
- ❌ отсутствует / надо делать

| Область | Что минимально нужно для **Wayland + ускорение** (render‑only GPU) | Skybox (сейчас) | Что проверено нами | Что минимально добавить/сделать |
|---|---|---:|---:|---|
| **HW: базовый рендер** | Треугольники → framebuffer | ✅ | raster/tri microtests + raster regression | — |
| **HW: текстуры** | Сэмплинг + адресация (для композитинга) | ✅ | tex regression + box128 microtest | — |
| **HW: альфа‑blend** | Нужен для UI/композиции | ✅ | om regression + box128 microtest | — |
| **HW: скейл/фильтрация** | Желательно (видео/скейлинг окон) | ⚠️ | косвенно (tex тест), фильтры не верифицированы | добавить микро‑тесты: nearest/linear, wrap/clamp, разные размеры |
| **HW: форматы** | хотя бы XRGB8888/ARGB8888 (DRM common) | ⚠️ | выход PNG RGBA; другие форматы не проверены | зафиксировать список форматов в RTL + добавить тесты |
| **HW: производительность памяти** | 1080p60 требует ~475 MiB/s только на scanout (RGBA), + запись/композиция | ⚠️ | не измеряли на железе | в AXI‑адаптере/LSU обеспечить burst/throughput, оценить QoS/arb |
| **Kernel: device model** | Стандартизованный интерфейс для userspace | ❌ | — | выбрать: DRM render node (рекомендуется) vs char/uio для PoC |
| **Kernel: GEM/буферы** | alloc/mmap буферов под рендер | ❌ | — | GEM (или TTM) + mmap |
| **Kernel: dma‑buf PRIME** | обмен буферами с KMS/scanout драйвером | ❌ | — | PRIME export/import + reservation fences |
| **Kernel: sync** | implicit fences минимум; explicit sync желательно | ❌ | — | начать с implicit; затем syncobj |
| **User space: EGL/GBM/Mesa** | compositor ожидает EGL/GBM + driver | ❌ | — | самый «правильный» путь: Gallium driver (GLES2) или Vulkan ICD + winsys |
| **OpenCL** | нужно по требованиям | ⚠️ | vecadd/compute smoke (раньше) | подтвердить на реальном SoC + оценить зависимость от host‑драйвера |
| **Отладка/регрессия** | reproducible tests | ✅ | microtests + sha256 refs | расширить rtlsim‑покрытие (меньшие tex/om refs, scissor, stress) |

---

## 4) Минимальные добавления, без которых «Linux + Wayland + ускорение» не взлетит

Если цель — **стандартный Linux userspace** (Weston/wlroots, GTK/Qt через EGL), то минимально нужны три слоя:

### A) HW/SoC integration «обязательный минимум»
1) **Нормальный MMIO control plane** (AXI4‑Lite) для:
   - обнаружения устройства/версии,
   - программирования DCR‑подобных регистров,
   - подачи команд (doorbell),
   - чтения статуса/ошибок (readback!),
   - IRQ по завершению работ.
2) **AXI4 master интерфейс, дружелюбный к памяти**: burst, outstanding transactions, выравнивание, (опц.) QoS.  
   Без этого риск «не дотянуть 1080p60» даже при наличии рендера.

### B) Kernel driver «обязательный минимум»
Рекомендуемый путь: **DRM render‑only драйвер** (не KMS), чтобы потом соединить с отдельным KMS драйвером scanout через dma‑buf.  
Минимальный набор:
- GEM BO (alloc/mmap),
- ioctl submit (command buffer),
- dma‑buf export (и желательно import),
- fence/синхронизация (implicit).

### C) User space «обязательный минимум»
Варианты:
1) **Mesa Gallium GLES2** (максимальная совместимость с Wayland compositor’ами).  
   Это большой кусок работ, но самый «системный» путь.
2) **Vulkan ICD** (если реально есть достаточный Vulkan‑подобный стек в Skybox‑коде) + compositor/стек, который умеет Vulkan.  
   Риск: совместимость и трудоёмкость не меньше, и экосистема тоньше.

---

## 5) Что бы я исправил/добавил в нашем отчёте (по сравнению с версией Stage 05)

1) Убрать формулировки вида «Vulkan traces exist» без прямого подтверждения в коде/тестах. Корректнее:  
   - **в репозитории мы видели CGL trace‑ориентированный путь**,  
   - **в публикациях заявлена Vulkan‑ориентация/поддержка Vulkan API**,  
   - **Linux‑интеграция (DRM/Mesa) нами не подтверждена**.
2) В матрице явно выделить «минимум для Wayland» = DRM render‑node + dma‑buf + Mesa/GBM/EGL; иначе создаётся ложное ощущение «почти готово».

---

## 6) Вывод по готовности Skybox как графического ускорителя для Linux (на сегодня)

**Как RTL/архитектура:** Skybox выглядит перспективно: графические блоки реально работают в simx/rtlsim и подтверждены регрессией (PNG refs). По этой части проект «живой».

**Как Linux‑GPU (Wayland, стандартный userspace):** на текущей стадии Skybox **не готов**, потому что отсутствует ключевое: **DRM render driver + userspace driver (Mesa/Vulkan ICD) + dma‑buf/sync**. Это не «полировка», а большой отдельный пласт работ.

**Тем не менее:** по сравнению с чистым compute‑GPU, Skybox уже имеет важные fixed‑function кирпичи (raster/tex/OM), которые делают достижимым быстрый 2D (композиция) при наличии драйверного стека.

---

## Ссылки (для справки)
- Skybox repo (README/specs): https://github.com/vortexgpgpu/skybox  
- Vortex repo (README/specs): https://github.com/vortexgpgpu/vortex  
- Vortex publications (Skybox/Vulkan claim): https://vortex.cc.gatech.edu/publications/  
- Linux DRM internals / render nodes / GEM: https://docs.kernel.org/gpu/drm-internals.html  
- Linux dma-buf docs: https://docs.kernel.org/driver-api/dma-buf.html  
- Linux DRM sync objects: https://docs.kernel.org/gpu/drm-uapi.html (drm_syncobj)  
- Mesa renderonly/KMSRO (background): https://lists.freedesktop.org/archives/mesa-dev/2019-January/214067.html
