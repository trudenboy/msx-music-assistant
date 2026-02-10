---
name: PR 3123 cleanup
overview: "Привести PR #3123 к виду «только MSX Bridge»: пересобрать ветку feat/msx-bridge-player-provider поверх upstream/dev и оставить в PR только изменения, касающиеся MSX provider."
todos: []
isProject: false
---

# Очистка PR #3123 от посторонних изменений

## Проблема

PR #3123 (feat/msx-bridge-player-provider → music-assistant/server dev) сейчас содержит 72 файла и 12 780 строк diff, потому что в ветку попали изменения из `origin/dev` (fork trudenboy):

**Лишние в PR:**
- `kion_music` — 10 файлов
- `vk_music` — 8 файлов  
- `zvuk_music` — 7 файлов
- `yandex_music` — изменения (My Wave и др.)
- `.gitignore`, `requirements_all.txt` — правки, не связанные с MSX

**Целевое состояние PR:** только MSX Bridge (19 файлов provider + tests).

## Причина

Merge `origin/dev` в `feat/msx-bridge-player-provider` добавил провайдеры и правки из форка, которых нет в `upstream/dev` (music-assistant/server). В PR эти изменения выглядят как новые.

## Решение

Пересоздать ветку `feat/msx-bridge-player-provider` на базе `upstream/dev`, включив только MSX Bridge.

## План действий

### 1. Обновить remotes

```bash
cd /Users/renso/Projects/ma-server
git fetch upstream
```

### 2. Создать новую ветку от upstream/dev

```bash
git checkout -b feat/msx-bridge-clean upstream/dev
```

### 3. Перенести только MSX Bridge

Скопировать из текущей ветки (или из msx-music-assistant) только файлы:

- `music_assistant/providers/msx_bridge/` (вся директория)
- `tests/providers/msx_bridge/` (вся директория)

Источник: `msx-music-assistant/provider/msx_bridge/` → `ma-server/music_assistant/providers/msx_bridge/` (путь `provider/` → `music_assistant/providers/`).

### 4. Обновить requirements_all.txt

MSX Bridge имеет `requirements: []`, поэтому:

- Запустить `uv run python -m scripts.gen_requirements_all`
- Оставить изменения в `requirements_all.txt` только если они относятся к MSX (скорее всего — нет)

### 5. Проверить .gitignore

В PR был diff по `.gitignore`. Проверить, нужны ли для MSX какие-либо записи; при отсутствии необходимости — не трогать.

### 6. Коммит и force-push

```bash
git add music_assistant/providers/msx_bridge/ tests/providers/msx_bridge/
git commit -m "feat: Add MSX Bridge Player Provider"
git push origin feat/msx-bridge-clean:feat/msx-bridge-player-provider --force
```

### 7. Проверка

После push PR #3123 должен показывать только изменения, связанные с MSX Bridge (19 файлов).

## Важные моменты

- Репозиторий upstream: [music-assistant/server](https://github.com/music-assistant/server)
- Текущий fork: trudenboy/ma-server  
- PR: trudenboy/ma-server:feat/msx-bridge-player-provider → music-assistant/server:dev
- `--force` допустим, так как ветка используется только для этого PR