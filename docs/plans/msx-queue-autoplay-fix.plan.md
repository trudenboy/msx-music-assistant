---
name: msx-queue-autoplay-fix
overview: Обновить MSX Bridge провайдер и плагин так, чтобы при проигрывании очереди треки шли подряд без закрытия плеера и корректно обновлялись метаданные.
todos:
  - id: analyze-queue-hooks
    content: Изучить player_queues и streams_controller для flow-режима и смены текущего трека
    status: completed
  - id: implement-provider-play-update
    content: Добавить notify_track_updated и broadcast_play_update в MSX Bridge провайдер и HTTP-сервер
    status: completed
  - id: implement-player-poll-tracking
    content: Реализовать в MSXPlayer.poll() отслеживание смены queue.current_item и вызов notify_track_updated
    status: completed
  - id: update-msx-plugin-js
    content: Добавить поддержку сообщения play_update в MSX JS-плагин и обновление UI/длительности без остановки плеера
    status: completed
  - id: add-tests-msx-bridge
    content: Написать юнит-тесты для poll-логики и WS play_update в msx-music-assistant и ma-server
    status: completed
  - id: sync-and-update-pr
    content: "Синхронизировать изменения между msx-music-assistant и ma-server, прогнать pre-commit и обновить PR #3123"
    status: completed
isProject: false
---

## Цель

Обеспечить корректное воспроизведение очереди (альбомы, плейлисты) на MSX: после окончания трека плеер не закрывается, автоматически начинает следующий трек, и в UI MSX обновляются название, артист и длительность.

## Текущее поведение

- MSX Bridge использует flow‑режим очереди и отдаёт поток через `/msx/audio/{player_id}` из `http_server.py`.
- Сейчас `play_media` в `MSXPlayer` один раз шлёт `broadcast_play` (через `notify_play_started`) c метаданными **первого** трека.
- Когда очередь переходит к следующему треку, MA обновляет текущий item, но MSX не получает новых метаданных и продолжает считать длительность равной первой.
- MSX нативный плеер закрывается, когда его внутренний таймер доходит до этой длительности — даже если flow‑поток ещё играет следующий трек.

## Основная идея решения

- 

- **Отслеживать внутри провайдера смену текущего трека в flow‑очереди**.
- При каждой смене текущего трека **слать в MSX обновление метаданных** по WebSocket (новый title/artist/duration/cover), *не* останавливая поток.
- MSX JS‑плагин должен уметь получать эти обновления и обновлять UI и длительность, не закрывая и не пересоздавая плеер.

## Шаги по бэкенду (ma-server)

- **1. Анализ существующих хуков очереди**
  - Просмотреть `[music_assistant/controllers/player_queues.py](music_assistant/controllers/player_queues.py)` и `[music_assistant/controllers/streams/streams_controller.py](music_assistant/controllers/streams/streams_controller.py)`, чтобы понять:
    - как / где хранится `flow_mode_stream_log` и текущий queue item;
    - какие сигналы/методы уже вызываются при смене трека во flow‑стриме.
- **2. Выбор точки для отправки обновлений**
  - Вариант A (проще и локально для провайдера):
    - В `[music_assistant/providers/msx_bridge/player.py](music_assistant/providers/msx_bridge/player.py)` реализовать периодический опрос очереди в `poll()`:
      - получать активную очередь через `self.mass.player_queues.get(self.player_id)`;
      - сравнивать текущий `queue.current_item.queue_item_id` с закэшированным в `MSXPlayer` значением;
      - при изменении — дергать новый метод провайдера `notify_track_updated(...)` с актуальными метаданными.
  - Вариант B (более тесная интеграция):
    - Добавить хук в контроллер очереди, но это сложнее и требует шире вмешиваться в ядро.
  - В плане остановиться на **варианте A** (poll‑подход в `MSXPlayer`) как на минимально инвазивном.
- **3. Расширить интерфейс провайдера MSX Bridge**
  - В `[music_assistant/providers/msx_bridge/provider.py](music_assistant/providers/msx_bridge/provider.py)`:
    - Добавить метод `notify_track_updated(player_id, *, title, artist, image_url, duration)`.
    - Прокинуть его в `MSXHTTPServer` как новый WebSocket‑эвент, например:
      - тип сообщения `{"type": "play_update", ...}` с тем же payload, что в `broadcast_play`.
  - В `[music_assistant/providers/msx_bridge/http_server.py](music_assistant/providers/msx_bridge/http_server.py)`:
    - Реализовать `broadcast_play_update(player_id, ...)`, который рассылает всем WS‑клиентам `type: "play_update"`.
- **4. Реализация отслеживания смены трека**
  - В `[music_assistant/providers/msx_bridge/player.py](music_assistant/providers/msx_bridge/player.py)`:
    - Добавить приватное поле, например `_last_queue_item_id: str | None`.
    - В `poll()`:
      - если `playback_state == PLAYING` и активна очередь:
        - получить `queue = self.mass.player_queues.get(self.player_id)`;
        - если `queue.flow_mode` и есть `queue.current_item`:
          - извлечь метаданные (title, artist, image, duration) аналогично тому, как это делается сейчас в `play_media` через `queue_item.media_item` и `self.mass.metadata.get_image_url`;
          - если `queue.current_item.queue_item_id != _last_queue_item_id`:
            - обновить `_last_queue_item_id`;
            - вызвать `provider.notify_track_updated(...)` с новыми данными.
- **5. Уточнение duration**
  - Для duration брать приоритетно:
    - `queue.current_item.media_item.duration` или `queue.current_item.duration`;
    - при отсутствии — можно оставить `None`, чтобы MSX отображал «без прогресса» (лучше, чем неверная длительность).
- **6. Тесты в ma-server**
  - В директории тестов MSX Bridge `[tests/providers/msx_bridge/](tests/providers/msx_bridge/)`:
    - Добавить юнит‑тест на `MSXPlayer.poll()` в flow‑режиме:
      - смоделировать очередь с двумя `QueueItem` с разными `queue_item_id`;
      - дернуть `poll()` так, чтобы имитировать смену текущего item;
      - проверить, что `notify_track_updated` вызывается ровно один раз на каждый новый трек с корректными полями.
    - Добавить тест на HTTP‑сервер, который проверяет, что `broadcast_play_update` рассылает WS‑клиентам сообщение `type: "play_update"` с нужными полями.

## Шаги по msx-music-assistant (реф‑проект)

- **7. Синхронизация изменений с референсным провайдером**
  - В `[provider/msx_bridge/player.py](provider/msx_bridge/player.py)` и `[provider/msx_bridge/http_server.py](provider/msx_bridge/http_server.py)` в проекте `msx-music-assistant` реализовать те же изменения (poll‑логика, `notify_track_updated`, `broadcast_play_update`).
  - Убедиться, что тесты в `[tests/providers/msx_bridge/](tests/providers/msx_bridge/)` покрывают:
    - генерацию `play_update` на смену трека;
    - отсутствие лишних вызовов, когда трек не меняется.

## Шаги по MSX плагину (frontend часть)

- **8. Обновление JS‑плагина для обработки play_update**
  - В `static/plugin.html` / `static/input.js` MSX Bridge:
    - Найти обработчик WebSocket‑сообщений, который сейчас реагирует на `type: "play"` / `type: "stop"`.
    - Добавить поддержку нового сообщения `type: "play_update"`:
      - обновлять заголовок/артиста/обложку в UI;
      - обновлять длительность/прогресс‑бар, не останавливая и не пересоздавая нативный плеер.
  - Убедиться, что логика, которая сейчас закрывает плеер по окончании трека, учитывает новую длительность из `play_update`, а не только из стартового `play`.
- **9. Локальное тестирование с MSX**
  - Запустить тестовый сервер через `[scripts/test-server.sh](scripts/test-server.sh)` в `msx-music-assistant`.
  - На MSX:
    - воспроизвести альбом и плейлист;
    - убедиться, что:
      - треки переходят автоматически;
      - длительность в UI обновляется при переключении трека;
      - плеер не закрывается до конца последнего трека или явного `stop`.

## Интеграция и PR

- **10. Завершение работы и обновление PR #3123**
  - После прохождения тестов в `msx-music-assistant` перенести изменения в `ma-server` (ветка `feat/msx-bridge-player-provider`, базированная на `upstream/dev`).
  - Прогнать `pre-commit` в `ma-server` и убедиться, что Ruff/mypy зелёные.
  - Запушить изменения и убедиться, что PR #3123 показывает только MSX‑файлы и новые сообщения WebSocket без сторонних провайдеров.

