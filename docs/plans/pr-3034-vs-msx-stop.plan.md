---
name: PR 3034 vs MSX stop
overview: "Анализ PR #3034 (group volume mute) показал, что он не решает проблему задержки остановки воспроизведения на MSX: PR касается только mute/volume в группах, а проблема MSX — это прекращение стрима и команда Stop."
todos: []
isProject: false
---

# Анализ: PR #3034 и прерывание воспроизведения на MSX

## Что делает PR #3034

PR добавляет поддержку **группового mute** (выключение звука) и атрибут **mute lock**:

- `**cmd_group_volume_mute**` — новый API `players/cmd/group_volume_mute`: для группы/синк-лидера вызывает `cmd_volume_mute` у всех включённых участников группы (через `asyncio.gather`).
- `**ATTR_MUTE_LOCK**` — флаг в `player.extra_data`: если игрок в группе был вручную замьючен, при изменении громкости группы его не размьючивают.

Изменения только в:

- [music_assistant/constants.py](pull-requests/pr-3034/diffs/music_assistant__constants.py.diff) — константа `ATTR_MUTE_LOCK`.
- [music_assistant/controllers/players/player_controller.py](pull-requests/pr-3034/diffs/music_assistant__controllers__players__player_controller.py.diff) — новый `cmd_group_volume_mute`, установка/сброс mute lock в `cmd_volume_mute`, учёт mute lock в `_handle_cmd_volume_set` при групповой громкости.

То есть PR касается **громкости и mute**, а не воспроизведения/стрима/stop.

## Проблема на MSX (из [docs/TODO.md](docs/TODO.md))

- **Симптом:** после нажатия Stop в MA воспроизведение на MSX останавливается с задержкой (~30 с).
- **Уже пробовали:** stop-event, опрос в цикле стрима, `transport.abort()` при выходе по stop, отмена задач и транспортов в `cancel_streams_for_player` — без явного эффекта.
- **Гипотезы:** буфер потока в MA (~30 чанков) или буфер/реконнект на стороне MSX.

То есть проблема — в **остановке стрима и реакции на cmd_stop**, а не в mute.

## Вывод

**PR #3034 не помогает решить проблему принудительного прерывания воспроизведения на MSX.**


| Аспект  | PR #3034                                   | Проблема MSX                              |
| ------- | ------------------------------------------ | ----------------------------------------- |
| Область | Volume mute в группах, mute lock           | Остановка воспроизведения (Stop)          |
| Команды | `cmd_volume_mute`, `cmd_group_volume_mute` | `cmd_stop`, закрытие стрима, отмена задач |
| Слой    | Player controller (громкость/мьют)         | Стрим (HTTP proxy, transport, буфер MA)   |


Для быстрой остановки на MSX по-прежнему нужно искать решение в:

- корректном вызове `cancel_streams_for_player` и `broadcast_stop` при `cmd_stop`;
- раннем завершении стрима/буфера в MA при Stop;
- поведении MSX-клиента при обрыве соединения (буфер, ретраи).

Мержить PR #3034 в контексте MSX имеет смысл только как общее улучшение (групповой mute); для задержки Stop он нейтрален.