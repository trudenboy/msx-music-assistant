# MSX Music Assistant Bridge

[English](README.md) | Русский

Стриминг музыки из [Music Assistant](https://music-assistant.io/) на Smart TV через приложение [Media Station X](https://msx.benzac.de/).

## Возможности

- **MA Player Provider** — работает внутри Music Assistant, не требует отдельных контейнеров или аддонов
- **MSX Native UI** — просмотр альбомов, исполнителей, плейлистов с управлением пультом TV
- **Браузинг библиотеки** — навигация по трекам альбомов, альбомам исполнителей, трекам плейлистов и результатам поиска
- **Аудио воспроизведение** — стриминг через очередь MA с PCM→ffmpeg кодированием
- **Браузерный веб-плеер** — лёгкий плеер для кухни, офиса, киосков и мобильного доступа (`http://<SERVER_IP>:8099/web/`)
- **Группировка плееров** — синхронное управление воспроизведением на нескольких TV (экспериментально; без синхронизации аудиопотока, каждый TV получает свой поток)
- **Нативные плейлисты MSX** — бесшовное воспроизведение альбомов/плейлистов с интеграцией очереди и навигацией пультом
- **Динамическая регистрация** — TV регистрируются как MA плееры автоматически по device ID или IP
- **Поддержка нескольких TV** — каждый TV получает уникальный плеер
- **WebSocket Push** — мгновенные уведомления о воспроизведении/остановке из MA
- **Мгновенная остановка** — Stop закрывает плеер сразу; Pause ставит на паузу, не закрывая плеер
- **Универсальность** — Samsung Tizen, LG webOS, Android TV, Fire TV, Apple TV, браузеры
- **Настраиваемый формат** — MP3, AAC или FLAC
- **Локальная сеть** — работает полностью в LAN, без облачных зависимостей

## Примеры использования

### Кухня/Гостиная
Открыть `http://<SERVER_IP>:8099/web/` на планшете — музыка играет пока готовишь.

### Умный дом
Группировка TV в гостиной и на кухне — одна музыка везде одновременно.

### Кафе/Ресторан
Несколько TV воспроизводят фоновую музыку синхронно.

### Мероприятия
Raspberry Pi + монитор в режиме киоска для вечеринки.

### Офис
Фоновая музыка на рабочем ноутбуке через веб-плеер.

## Архитектура

```
┌─────────────┐         ┌───────────────────────────────────────┐
│  Smart TV   │         │        Music Assistant Server          │
│  (MSX App)  │  HTTP   │  ┌─────────────────────────────────┐  │
│             │ ◄─────► │  │   MSXBridgeProvider (port 8099) │  │
│ - JSON nav  │         │  │   ├── MSXHTTPServer (aiohttp)   │  │
│ - Audio     │         │  │   └── MSXPlayer                 │  │
│ - Plugin    │         │  └───────────┬──────────────────────┘  │
└─────────────┘         │              │ internal API             │
                        │              │                          │
┌─────────────┐         │  ┌───────────▼──────────────────────┐  │
│   Браузер   │  HTTP   │  │        MA Core                    │  │
│ (Web Player)│ ◄─────► │  │  music, players, player_queues    │  │
└─────────────┘         │  └───────────────────────────────────┘  │
                        └───────────────────────────────────────┘
```

### Компоненты

| Компонент | Класс | Роль |
|-----------|-------|------|
| **Provider** | `MSXBridgeProvider` | MA `PlayerProvider` — управление жизненным циклом, регистрация плееров, HTTP сервер |
| **Player** | `MSXPlayer` | MA `Player` — представляет Smart TV, хранит stream URL для воспроизведения |
| **HTTP Server** | `MSXHTTPServer` | aiohttp сервер — MSX bootstrap, контент, аудио прокси, REST API |

## Быстрый старт

### Требования

- [Music Assistant](https://music-assistant.io/) сервер (или форк [MA server repo](https://github.com/trudenboy/ma-server))
- [Media Station X](https://msx.benzac.de/) приложение на Smart TV
- Python 3.12+

### Установка

```bash
# 1. Клонировать репозиторий рядом с MA сервером
cd ~/Projects
git clone https://github.com/trudenboy/msx-music-assistant.git
git clone https://github.com/trudenboy/ma-server.git  # если ещё не клонирован

# 2. Настроить venv, установить зависимости, создать симлинк провайдера
cd msx-music-assistant
./scripts/link-to-ma.sh

# 3. Запустить MA сервер (провайдер загрузится автоматически)
source ../ma-server/.venv/bin/activate
cd ../ma-server && python -m music_assistant --log-level debug
```

### Настройка TV

1. Открыть MSX приложение на Smart TV
2. Перейти в **Settings > Start Parameter**
3. Ввести: `http://<IP_СЕРВЕРА>:8099/msx/start.json`
4. Перезапустить MSX

Также можно открыть `http://<IP_СЕРВЕРА>:8099/` в браузере — статус дашборд с URL настройки, списком плееров и кнопкой **Quick stop** для мгновенной остановки воспроизведения.

## Конфигурация

Провайдер предоставляет шесть настроек в MA UI:

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `http_port` | `8099` | Порт HTTP сервера |
| `output_format` | `mp3` | Формат аудио для стриминга (`mp3`, `aac`, `flac`) |
| `player_idle_timeout` | `30` | Таймаут неактивности плеера (минуты) |
| `show_stop_notification` | `false` | Показывать уведомление при остановке из MA |
| `abort_stream_first` | `false` | Сначала прервать поток, потом отправить stop (может помочь на некоторых TV) |
| `enable_player_grouping` | `true` | Разрешить группировку TV для синхронного воспроизведения (экспериментально) |

### Stop, Pause и Resume

- **Stop** — Закрывает MSX плеер мгновенно через двойной broadcast (как Disable)
- **Pause** — Ставит воспроизведение на паузу, MSX плеер остаётся открытым; **Play** возобновляет с места паузы
- **Quick stop** — Кнопка на дашборде или `POST /api/quick-stop/{player_id}`

## HTTP Endpoints

### Web Player

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/web/` | Браузерный веб-плеер (не требует MSX app) |

### MSX Bootstrap

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Статус дашборд (HTML) |
| GET | `/msx/start.json` | MSX стартовая конфигурация |
| GET | `/msx/plugin.html` | MSX interaction plugin |

### Контент

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/msx/menu.json` | Главное меню библиотеки |
| GET | `/msx/albums.json` | Список альбомов |
| GET | `/msx/artists.json` | Список исполнителей |
| GET | `/msx/playlists.json` | Список плейлистов |
| GET | `/msx/tracks.json` | Список треков |
| GET | `/msx/search.json?q=...` | Результаты поиска |

### Управление воспроизведением

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/play` | Начать воспроизведение (`{track_uri, player_id}`) |
| POST | `/api/pause/{player_id}` | Пауза |
| POST | `/api/stop/{player_id}` | Стоп |
| POST | `/api/quick-stop/{player_id}` | Мгновенная остановка |
| POST | `/api/next/{player_id}` | Следующий трек |
| POST | `/api/previous/{player_id}` | Предыдущий трек |

### WebSocket

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/ws?device_id=...` | WebSocket для push уведомлений (MA → MSX) |

### Утилиты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Health check (`{status, provider, players}`) |

## Структура проекта

```
provider/msx_bridge/
├── __init__.py        # setup(), get_config_entries() — точка входа провайдера
├── provider.py        # MSXBridgeProvider — жизненный цикл, регистрация плееров
├── player.py          # MSXPlayer — Smart TV как MA плеер
├── http_server.py     # MSXHTTPServer — aiohttp маршруты
├── constants.py       # Ключи конфигурации и значения по умолчанию
├── mappers.py         # MSX JSON мапперы для контент-страниц
├── models.py          # Pydantic модели для MSX ответов
├── manifest.json      # Метаданные провайдера для MA
└── static/
    ├── web/           # Браузерный веб-плеер
    │   ├── index.html # UI плеера
    │   └── web.js     # Логика плеера
    ├── plugin.html    # MSX interaction plugin
    └── ...

tests/                 # Unit и integration тесты
scripts/               # Setup и dev скрипты
```

## Разработка

См. [CLAUDE.md](CLAUDE.md) для подробного руководства по разработке и конвенциям MA.

```bash
# Установка одной командой
./scripts/link-to-ma.sh

# Активация venv
source ../ma-server/.venv/bin/activate

# Запуск тестов
pytest tests/ -v --ignore=tests/integration

# Линтинг
cd ../ma-server && pre-commit run --all-files
```

## Вклад в проект

См. [CONTRIBUTING.md](CONTRIBUTING.md).

## Лицензия

MIT License — см. [LICENSE](LICENSE).

## Благодарности

- [Music Assistant](https://music-assistant.io/) от Marcel Veldt
- [Media Station X](https://msx.benzac.de/) от Benjamin Zachey
