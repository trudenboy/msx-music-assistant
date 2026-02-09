# TODO

## Отложено

### Быстрая остановка воспроизведения (Stop) на MSX

**Проблема:** При нажатии Stop в Music Assistant воспроизведение на MSX-клиенте останавливается с задержкой (~30 сек). Отключение (power off) и Disable плеера останавливают сразу.

**Что пробовали:** stop-event + опрос в цикле стрима, принудительный `transport.abort()` при выходе по stop, отмена задач и транспортов в `cancel_streams_for_player`. Улучшения не дали эффекта — возможно, задержка на стороне MA (буфер потока) или MSX (буфер/реконнект).

**Сделано (instant stop):** Сначала `broadcast_stop(player_id)` (WebSocket), затем `cancel_streams_for_player(player_id)`, чтобы TV получил команду eject до обрыва стрима. Единый `player_id` (device_id или IP) для WS и стрима — см. `_get_player_id_and_device_param` / `_handle_ws`.

**Сделано (2025-02):**
- **Disable → Enable:** Переопределён `on_player_disabled` без unregister — плеер остаётся в списке при Enable. При Disable всё равно вызываются `broadcast_stop` и `cancel_streams_for_player` для мгновенной остановки на TV.
- **Stop = Quick stop:** В `notify_play_stopped` сигнал `broadcast_stop` + `cancel_streams` отправляется дважды (как при Disable), чтобы Stop в MA останавливал MSX сразу.
- **Pause:** При паузе в MA вызывается `notify_play_stopped` — плеер на MSX закрывается, позиция и очередь в MA сохраняются. При нажатии Play в `MSXPlayer.play()` вызывается `mass.player_queues.resume(player_id)` — очередь заново отправляет текущий трек на MSX.
- **MSX plugin:** Цепочка `[player:eject|player:hide]` вместо одного `player:eject` — возможно быстрее закрывает плеер (при `showNotification=false`).
- **Опция config:** `abort_stream_first` — при включении сначала `cancel_streams_for_player`, затем `broadcast_stop`; может помочь на некоторых TV.

**Идеи на будущее:**
- Проверить, что стрим при Stop действительно тот же (player_id, endpoint `/stream/` vs `/msx/audio/`).
- Разобрать поведение MA flow stream (буфер ~30 чанков) и возможность раннего завершения при Stop.
- Уточнить поведение MSX-клиента при обрыве соединения (буфер, ретраи).
