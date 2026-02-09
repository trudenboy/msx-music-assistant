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

## WebSocket: Play/Stop из MA не доходят до TV

В логах теперь есть явные сообщения:

1. **При подключении TV:**  
   `WebSocket connected: player_id=msx_xxx, clients_for_player=1, all_players=[...]`  
   Запомни этот `player_id`.

2. **При Play в MA:**  
   - `broadcast_play: no WebSocket clients for player_id=... (connected: [])` — к WebSocket никто не подключён или уже отключился.  
   - `broadcast_play: no WebSocket clients for player_id=X (connected: [Y])` — в MA выбран плеер X, а подключён плеер Y (разные player_id).  
   - `broadcast_play: player_id=X, sending to N client(s)` — сообщение отправлено; если на TV ничего не происходит, проблема на стороне MSX (executeAction или контекст плагина).

3. **При Stop в MA:**  
   Аналогично: `broadcast_stop: no WebSocket clients...` или `broadcast_stop: player_id=X, sending to N client(s)`.

Что проверить: совпадает ли `player_id` из сообщения «WebSocket connected» с именем плеера в MA (например, «MSX TV (192.168.x.x)» или «MSX TV (device_id)»). Если TV подключается без `device_id`, будет player_id по IP; если контент запрашивается с `device_id`, возможен другой player_id и рассылка уходит «в пустоту».
