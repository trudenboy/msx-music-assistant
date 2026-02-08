# План: Динамическая регистрация MSX players

## 1. Результаты анализа документации MSX

### 1.1 Device ID (MSX Plugin API)

В [Plugin API Reference](https://msx.benzac.de/wiki/index.php?title=Plugin_API_Reference) документально описаны методы:

```
TVXVideoPlugin.clearDeviceId();   // Очищает device ID
TVXVideoPlugin.getDeviceId(data); // Возвращает (или создаёт) device ID
TVXVideoPlugin.requestDeviceId(callback); // Запрашивает device ID асинхронно
```

**Вывод**: MSX предоставляет стабильный Device ID на стороне клиента. Это предпочтительный идентификатор для уникальной привязки TV к player в MA.

### 1.2 TVXSettings (платформа и версия)

Статический класс `TVXSettings` экспортирует:
- `TVXSettings.ID` — идентификатор
- `TVXSettings.PLATFORM` — платформа (например Tizen, webOS)
- `TVXSettings.VERSION` — версия MSX

**Вывод**: Версия клиента и платформа доступны в JavaScript-контексте плагина. Можно использовать для:
- Проверки совместимости
- Отображения в UI (`Samsung Tizen / MSX 0.1.163`)
- Логирования

### 1.3 Ограничения native audio flow

Текущий flow: `action: "audio:http://host/msx/audio/msx_default?uri=..."`

- MSX native player выполняет HTTP GET по этому URL
- Запрос идёт напрямую с TV — сервер видит только `request.remote` (IP)
- Native player **не** выполняет наш JavaScript — device ID в запрос не подставляется автоматически

**Вывод**: Чтобы использовать Device ID, его нужно явно добавить в URL на этапе формирования контента. Это делается в Interaction Plugin при построении menu/content.

### 1.4 MAC-адрес

- MAC **не** передаётся в HTTP-запросах
- Получить MAC можно только: (a) если клиент сам отправит в заголовке, (b) через ARP на сервере (хрупко, только в одной подсети)
- На Smart TV доступ к MAC из JavaScript обычно ограничен политиками приватности

**Вывод**: Идентификация по MAC в MSX нереалистична. Device ID — надёжная альтернатива.

---

## 2. Стратегия идентификации клиентов

| Приоритет | Источник | Формат player_id | Устойчивость | Доступность |
|-----------|----------|------------------|--------------|-------------|
| 1 | Device ID (MSX API) | `msx_{sanitized_device_id}` | Высокая | Через Interaction Plugin |
| 2 | IP-адрес | `msx_{ip_sanitized}` | Средняя | Всегда |
| 3 | IP + User-Agent hash | `msx_{ip}_{ua_hash}` | Средняя | При коллизии IP |

**Рекомендация**: Использовать Device ID как основной идентификатор. IP — fallback, когда Device ID недоступен (старые версии MSX, нативная загрузка контента без плагина).

---

## 3. Архитектура реализации

### 3.1 Требуемые изменения в MSX flow

Чтобы Device ID попадал на сервер, все ссылки на контент и audio должны содержать `device_id` в query string:

```
/msx/albums.json?device_id=abc123xyz
/msx/audio/msx_abc123xyz?uri=...
```

Варианты:

**A) Interaction Plugin формирует все URL**

- Menu: `content:request:interaction:init@plugin.html`
- Plugin при `handleRequest("init")` вызывает `TVXVideoPlugin.requestDeviceId(callback)`
- В callback возвращает menu с URL вида `{prefix}/msx/albums.json?device_id={deviceId}`
- Все content pages загружаются с `?device_id=...` в URL

**B) Плагин только при старте регистрирует device_id**

- При первом init плагин вызывает `/api/register-device` с `device_id` в body
- Сервер создаёт mapping `IP -> device_id` (TTL 30–60 мин)
- Content pages загружаются по IP (без device_id в URL) — сервер определяет player по IP из кэша

Вариант A прозрачнее и не зависит от кэша IP. Вариант B проще для нативного контента, но требует синхронизации по времени.

**Рекомендация**: Вариант A — единообразно передаём `device_id` во всех URL.

### 3.2 Серверная логика

1. **Middleware / хелпер**  
   Для каждого MSX-запроса:
   - Извлечь `device_id` из `request.query.get("device_id")`
   - Если есть — `player_id = "msx_" + sanitize(device_id)`
   - Если нет — `player_id = "msx_" + sanitize(request.remote)` (fallback)

2. **get_or_register_player(request)**  
   - Определить `player_id` по device_id или IP
   - Если player не зарегистрирован — создать `MSXPlayer`, вызвать `mass.players.register(player)`
   - Вернуть player

3. **Все MSX content handlers**  
   - Перед обработкой вызывать `get_or_register_player(request)`
   - Передавать `player_id` в `_format_msx_track(..., player_id)` для формирования `action: "audio:{prefix}/msx/audio/{player_id}?uri=..."`

4. **Unregister по таймауту**  
   - Хранить `last_activity` у каждого MSX player
   - Фоновая задача: если прошло > N минут без запросов → `mass.players.unregister(player_id)`
   - Защита от гонок по аналогии с Sendspin (`_pending_unregisters`)

### 3.3 Изменения в plugin.html / input.js

- При `handleRequest("init")` вызвать `TVXVideoPlugin.requestDeviceId(callback)`
- В callback: кэшировать deviceId в переменной
- При формировании menu items добавлять `?device_id=` + deviceId ко всем content URL
- Если `requestDeviceId` недоступен (старая MSX) — формировать URL без device_id (fallback на IP)

---

## 4. Затрагиваемые файлы

| Файл | Изменения |
|------|-----------|
| `provider/msx_bridge/provider.py` | Убрать статический player; добавить `get_or_register_player()`, background task для timeout unregister |
| `provider/msx_bridge/http_server.py` | Middleware/хелпер для player_id; прокинуть player_id во все MSX handlers; `_format_msx_track(..., player_id)` |
| `provider/msx_bridge/constants.py` | `CONF_PLAYER_IDLE_TIMEOUT` (минуты) |
| `provider/msx_bridge/static/plugin.html` или `input.js` | Вызов `requestDeviceId`, добавление `device_id` в URL |

---

## 5. Оценка трудозатрат

| Компонент | Сложность | Часы (оценка) |
|-----------|-----------|---------------|
| Provider: register/unregister логика | Низкая | 2–3 |
| HTTP: middleware, прокидывание player_id | Средняя | 2–3 |
| Plugin: requestDeviceId + URL builder | Низкая | 1–2 |
| Timeout unregister + race handling | Средняя | 1–2 |
| Тесты | Низкая | 1–2 |
| **Итого** | | **7–12** |

---

## 6. Риски и проверки

- **TVXVideoPlugin в Interaction Plugin**: Нужно убедиться, что `requestDeviceId` доступен в контексте Interaction Plugin (тот же `tvx-plugin.min.js`). При необходимости — минимальный тест в браузере/TV.
- **Минимальная версия MSX**: Уточнить, с какой версии есть `requestDeviceId`; при её отсутствии — fallback на IP.
- **Обратная совместимость**: При отсутствии `device_id` в запросе использовать IP, сохраняя работу с текущим и старым контентом.

---

## 7. Ссылки на документацию MSX

- [Plugin API Reference](https://msx.benzac.de/wiki/index.php?title=Plugin_API_Reference) — TVXVideoPlugin.getDeviceId, requestDeviceId
- [Interaction Plugin](https://msx.benzac.de/wiki/index.php?title=Interaction_Plugin) — handleRequest, init flow
- [Actions](https://msx.benzac.de/wiki/index.php?title=Actions) — audio:URL, content:request:interaction:
- [Content Item Object](https://msx.benzac.de/wiki/index.php?title=Content_Item_Object) — action property
