# Захват MSX_DEBUG логов для диагностики Stop

## Что уже проверено (локальный тест)

Скрипт `debug-stream-stop.py` успешно симулирует flow MSX:
- **_register_stream** вызывается при старте стрима (player_id=msx_debug_test)
- **cancel_streams_for_player** при Stop находит 1 task и 1 transport
- Стрим обрывается сразу (ContentLengthError — соединение закрыто)

В локальном тесте механизм cancel работает.

## Как получить логи в вашем окружении

1. Убедитесь, что в коде включено логирование `[MSX_DEBUG]` (provider.py, http_server.py).

2. Запустите MA server как обычно:
   ```bash
   python -m music_assistant --log-level debug
   ```

3. Воспроизведите музыку через MSX (через `/stream/{player_id}`).

4. Нажмите Stop в MA UI.

5. В логах MA найдите строки с `[MSX_DEBUG]`:
   ```bash
   grep MSX_DEBUG ~/.musicassistant/musicassistant.log
   ```
   или там, куда пишет ваш MA (проверьте `MA_DATA_DIR`).

6. Важно проверить:
   - есть ли строка `_register_stream` (стрим регистрировался);
   - есть ли строка `cancel_streams_for_player` с `found tasks=X transports=Y`;
   - совпадает ли `player_id` в register и cancel;
   - `registered_player_ids=` — какие player_id зарегистрированы на момент cancel.

Если `found tasks=0 transports=0` при `registered_player_ids=[X, Y]` — это несовпадение player_id.
