# Планы по проекту MSX Music Assistant

В этой папке хранятся планы разработки и анализа, связанные с провайдером MSX Bridge и интеграцией Music Assistant с Media Station X (MSX).

| Файл | Описание |
|------|----------|
| `msx-hybrid-mode-followup.plan.md` | Доработка гибридного режима (playback_mode, очередь MA, тесты) |
| `msx-hybrid-playlist-ma-queue.plan.md` | Гибридный режим: MSX плейлист + MA очередь, архитектура и шаги |
| `msx-native-playlist-integration.plan.md` | Нативный плейлист MSX, радио без duration, направления интеграции |
| `msx-queue-autoplay-fix.plan.md` | Исправление автоперехода треков (flow, play_update, poll) |
| `msx-provider-icon.plan.md` | Добавление иконки провайдера MSX Bridge |
| `msx-search-ux-and-ui.plan.md` | Поиск в один клик из меню, соответствие MSX Showcases |
| `msx-stop-delay-solutions.plan.md` | Варианты уменьшения задержки Stop на MSX |
| `ma-to-msx-play-push-analysis.plan.md` | Анализ push-воспроизведения MA → MSX (WebSocket vs callback) |
| `instant-stop-on-ma-ui.plan.md` | Мгновенная остановка при Stop в MA (порядок broadcast/cancel) |
| `pr-3123-cleanup.plan.md` | Очистка PR #3123 от посторонних изменений |
| `pr-msx-provider-ma-server.plan.md` | План PR добавления MSX Bridge в ma-server |
| `prs-for-msx-bridge.plan.md` | План PR в server и документации в beta.music-assistant.io |
| `pr-3034-vs-msx-stop.plan.md` | Анализ PR #3034 (group volume mute) и задержка Stop на MSX |

Файлы в формате Markdown с опциональным YAML frontmatter (name, overview, todos). Исходные планы могут дублироваться в `~/.cursor/plans/`.
