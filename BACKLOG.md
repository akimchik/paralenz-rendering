# Project Backlog & Feature Roadmap

This file tracks planned features and professional improvements for the Headless FFmpeg Automation suite.

## Phase 3: Visual Polishing & Core Upgrades (In Progress)
- [x] **UV Paved Road Execution:** Migrate the entire Python environment management to `uv`. Utilize PEP 723 inline script metadata (`# /// script`) inside `build_headless_movie.py` so users can execute the project directly from GitHub without cloning or manual setup (e.g., `uv run https://raw.githubusercontent.com/...`).
- [ ] **Automatic Color Correction:** Apply a standard "Underwater Recovery" LUT or `.cube` grade to all MP4s dynamically during the FFmpeg render process (using `lut3d`).
- [ ] **Smooth Transitions:** Automate cross-dissolves (crossfades) between raw 4K clips using the FFmpeg `xfade` filter instead of hard cuts.
- [x] **Перевірити і оптимізувати unit-tests для кращого менеджменту проекту і розуміння test-coverage.** (Закрито через структурний рефакторинг `main`).

## Phase 3.5: Code Review Remediation (v3.1.5 - v3.1.7)

Full code review виявив 18 проблем. Завдання розбиті на декілька ітерацій.

### 🎯 Зроблено у v3.1.5 (Critical Hotfixes)
- [x] **CR-01: Видалити хардкодовані `/opt/homebrew/bin/` фолбеки**
- [x] **CR-02: Рефакторинг `check-status.py`**
- [x] **CR-03: DRY — Створити `scripts/utils.py` для спільного коду**
- [x] **CR-04: Тест `test_headless_engine.py` — видалити `/opt/homebrew/` fallback**
- [x] **CR-05: Тест `validate_output.py` — видалити подвійний `import shutil` та хардкоди**

### 🚧 Заплановано на v3.1.6 (High Priority & Stability)
- [ ] **CR-06: Баг у `render` — додати `exit 1`** — Після `echo "Usage: ./render -d YYYY-MM-DD"` скрипт не виходить. Додати `exit 1` щоб запобігти виконанню з порожнім `$DATE`.
- [ ] **CR-07: Переписати `test_srt_generation.py`** — Замінити перевірку raw source code (`assertIn(expected, self.code)`) на справжні unit-тести які викликають `format_srt_time()` і перевіряють поведінку.
- [ ] **CR-08: Виправити `test_logic_accuracy.py`** — Замінити продубльовану локальну `detect_dives_logic()` (gap=1800) на імпорт реальної `detect_dives()` (gap=7200) з `scripts/build_headless_movie.py`.
- [ ] **CR-09: Оновити `skill/python-telemetry.md`** — Замінити посилання на застарілий `requirements.txt` на PEP 723 + `uv`.
- [ ] **CR-10: Узгодити SKILL.md щодо `./render` wrapper** — Прибрати слово "legacy" і визнати `./render` як валідний entry point, або обґрунтовано видалити його.
- [ ] **CR-12: Рефакторинг FFmpeg fallback у `build_headless_movie.py`** — Замінити крихку мутацію `cmd.index(...)` на окрему функцію `build_ffmpeg_cmd(codec=...)` яка будує команду з нуля.
- [ ] **NEW: Надійна очистка тимчасових файлів** — Використати `atexit` або `try/finally` у `build_headless_movie.py`, щоб `temp_dir` вичищався завжди (навіть при `No space left on device` або `Ctrl+C`).
- [ ] **NEW: Faststart Fix** — Додати прапорець `-movflags +faststart` до фінального рендеру FFmpeg, щоб відео миттєво відкривалося у QuickTime.

### 📅 Заплановано на v3.1.7 (Tech Debt & Polish)
- [ ] **CR-11: Вичистити `EOF` з `.gitignore`** — Видалити артефакт `EOF` рядок із `.gitignore` (сміття від `cat << EOF`).
- [ ] **CR-13: Додати PEP 723 inline metadata** — Додати `# /// script` блок у `calc_offset.py` та `check_videos.py` для автоматичного підтягування `pandas` через `uv run`.
- [ ] **CR-14: Мігрувати E2E тести на `main(args=...)`** — `test_headless_engine.py` і `validate_output.py` мають імпортувати `main()` замість subprocess для правильного трекінгу coverage.
- [ ] **CR-15: Доповнити CHANGELOG.md v3.1.4** — Додати пропущені пункти: рефакторинг CLI tools, DoD checklist, CI migration to pytest-cov, SKILL TDD mandates.
- [ ] **CR-16: Створити `tests/conftest.py`** — Замінити `sys.path.insert(...)` boilerplate у кожному тестовому файлі на єдиний `conftest.py` або `pyproject.toml` з `pythonpath = ["."]`.
- [ ] **CR-17: Підняти inline imports на рівень модуля** — В `test_build_headless_movie.py` перенести `from scripts.build_headless_movie import concatenate_slices, build_overlay_slices, main` на верх файлу.
- [ ] **CR-18: Закрити UV Paved Road в BACKLOG** — Позначити як `[x]` (вже реалізовано у v3.1.1).

## Phase 4: Workflow Improvements
- [ ] **Experimental Color Grading Optimization:** The current `colorbalance` approach (Filter #1) amplifies red noise in dark underwater shadows (turning caves purple). We need to explore luma-masking or non-linear RGB curves (`curves` filter) to optimize the red filter: making corals brighter without ruining shadows.
- [ ] **Water Type Color Profiles:** Enhance the `--water` argument to support `freshwater` (boosts magenta to counteract green algae instead of pure red).
- [ ] **Multi-Day Processing:** Upgrade the `./render` wrapper to accept a range of dates (or automatically process all available media dates) in a single run.
- [ ] **Concurrent Rendering:** Explore using Python's `multiprocessing` to generate highlight slices in parallel before the final FFmpeg concatenation.

---
*Last updated: August 25, 2026*
