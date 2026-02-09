# План: Группировка MSX-плейеров (play same track on multiple TVs)

> **Цель:** Включить поддержку группировки в MSX Bridge, чтобы один и тот же трек воспроизводился на нескольких Smart TV одновременно. Без синхронизации потока — каждый TV получает свой stream и стартует с небольшой задержкой относительно других.

## 1. Обзор

При группировке MSX TV 1 и MSX TV 2 в MA UI:
- Воспроизведение, запущенное на группе, запускается на всех участниках
- Play, Pause, Stop, Next, Previous распространяются на все устройства в группе
- Каждый TV воспроизводит один и тот же контент независимо (своя очередь, свой stream)

## 2. Затрагиваемые компоненты

### 2.1 `provider/msx_bridge/__init__.py`

| Изменение | Описание |
|-----------|----------|
| Импорт | `from music_assistant_models.enums import ProviderFeature` |
| Константа | `SUPPORTED_FEATURES = {ProviderFeature.SYNC_PLAYERS}` |

### 2.2 `provider/msx_bridge/player.py`

| Изменение | Описание |
|-----------|----------|
| `_attr_supported_features` | Добавить `PlayerFeature.SET_MEMBERS` |
| `_attr_can_group_with` | Инициализировать `{provider.instance_id}` — группировка только внутри MSX провайдера |
| `set_members()` | Реализовать: обновлять `_attr_group_members`, вызывать `update_state()` |
| `play_media()` | После настройки своего playback — для каждого `group_members` вызывать `mass.players.play_media(member_id, media)` (только когда `synced_to is None` — мы лидер) |
| `stop()` | Аналогично — propagate stop на `group_members` |
| `pause()` | Propagate pause на `group_members` |
| `play()` | Propagate play (resume) на `group_members` |

### 2.3 Propagation команд: Next / Previous

Команды Next и Previous в MA идут через `mass.player_queues` (смена трека в очереди), а не через `player.next()` напрямую. Нужно проверить, как MA обрабатывает next/previous для групп.

- Если MA вызывает `cmd_next_track` на лидере — то смена трека произойдёт в очереди лидера. У каждого MSX своя очередь. Значит при группировке: когда лидер переключает трек, очереди членов группы не обновляются автоматически.
- Для «play same track» при next нужно: когда лидер получает next, следующий трек должен начаться и на членах. Это может идти через `play_media` с новым media — MA при next вызовет `play_media` на лидере с новым треком. Наш `play_media` propagates на members — значит члены тоже получат `play_media`. Хорошо.
- Но `play_media` вызывается из player_queues при смене трека — нужно убедиться, что наш propagate не создаёт циклов и что MA корректно обрабатывает группу.

**Вывод:** Next/Previous обрабатываются через очередь и `play_media` при смене трека. Наш propagate в `play_media` должен покрыть этот сценарий. Отдельная реализация `next`/`previous` в player может не потребоваться — проверить при реализации.

## 3. Детальная реализация

### 3.1 `set_members()`

```python
async def set_members(
    self,
    player_ids_to_add: list[str] | None = None,
    player_ids_to_remove: list[str] | None = None,
) -> None:
    """Handle SET_MEMBERS — update group membership."""
    for pid in player_ids_to_remove or []:
        if pid in self._attr_group_members:
            self._attr_group_members.remove(pid)
    for pid in player_ids_to_add or []:
        if pid not in self._attr_group_members and pid != self.player_id:
            # Validate: only MSX players from same provider
            other = self.mass.players.get(pid)
            if other and isinstance(other, MSXPlayer):
                self._attr_group_members.append(pid)
    self.update_state()
```

### 3.2 Propagate-helper

Чтобы избежать дублирования, вынести propagation в хелпер:

```python
async def _propagate_to_group_members(
    self, command: str, *args: Any, **kwargs: Any
) -> None:
    """Propagate command to group members when we are the leader."""
    if self.synced_to is not None:
        return  # We are follower, not leader
    for member_id in self.group_members:
        member = self.mass.players.get(member_id)
        if not member or not isinstance(member, MSXPlayer) or not member.available:
            continue
        if command == "play_media":
            await self.mass.players.play_media(member_id, kwargs["media"])
        elif command == "stop":
            await member.stop()
        # ... etc
```

### 3.3 Изменения в `play_media()`

В конце `play_media()`, после `notify_play_started()`:

```python
# Propagate to group members (we are leader)
await self._propagate_to_group_members("play_media", media=media)
```

### 3.4 Изменения в `stop()`, `pause()`, `play()`

Аналогично вызывать `_propagate_to_group_members` перед/после основной логики. Для `stop` — после `notify_play_stopped`; для `pause`/`play` — после `update_state()`.

### 3.5 Рекурсия и циклы

- При propagate `play_media(member_id, media)` MA вызовет `member.play_media(media)`. У member `synced_to` не None (он synced к нам), и `group_members` может быть пуст или не содержать нас. Важно: не вызывать propagate, когда мы follower (`synced_to is not None`), и не добавлять себя в propagate targets.
- Исключить из propagate тех, кто уже synced к нам (они и так получат команду через MA? Нет — MA шлёт команду только лидеру). Мы сами шлём команды членам — корректно.

### 3.6 Next / Previous

MA: `cmd_next_track(player_id)` → player_queues переключает очередь и вызывает play_media с новым треком на player_id (лидере). Наш `play_media` propagates. Значит next/previous уже покрыты через `play_media`. Отдельный `next()`/`previous()` в MSXPlayer, если он вызывается MA — проверить. Сейчас MSXPlayer не имеет `next`/`previous` в supported_features, так что MA их не вызывает. Смена трека идёт через очередь → play_media. Ок.

## 4. Файлы для изменения

| Файл | Изменения |
|------|-----------|
| `provider/msx_bridge/__init__.py` | Добавить `ProviderFeature.SYNC_PLAYERS` в `SUPPORTED_FEATURES` |
| `provider/msx_bridge/player.py` | SET_MEMBERS, can_group_with, set_members(), propagate в play_media/stop/pause/play |

## 5. Тесты

- Unit: `set_members` обновляет `group_members` корректно
- Unit: `play_media` при наличии group_members вызывает `mass.players.play_media` для каждого member (mock)
- Integration: группировка двух MSX players в MA, play на группе — оба получают play_media (проверка логов/моков)
- Ручная проверка: два TV, группировка в MA UI, воспроизведение — оба играют один трек

## 6. Риски и ограничения

| Риск | Митигация |
|------|-----------|
| Рекурсия/циклы при propagate | Проверять `synced_to is None`, не добавлять self в targets |
| Member недоступен | Проверять `member.available` перед propagate, логировать skip |
| Разные очереди у members | По дизайну — у каждого своя очередь, играют один трек (тот же uri), без синхронизации |
| Idle timeout и grouped players | При unregister лидера — члены остаются; при unregister члена — убрать из group_members лидера (MA sync layer может обработать) |

## 7. Порядок реализации

1. **Шаг 1:** Provider — добавить `SYNC_PLAYERS`; Player — добавить `SET_MEMBERS`, `can_group_with`.
2. **Шаг 2:** Реализовать `set_members()`.
3. **Шаг 3:** Добавить `_propagate_to_group_members()` и интеграцию в `play_media`.
4. **Шаг 4:** Добавить propagation в `stop()`, `pause()`, `play()`.
5. **Шаг 5:** Unit-тесты.
6. **Шаг 6:** Integration-тест и ручная проверка.
