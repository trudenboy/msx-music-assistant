# MSX Music Assistant Integration - Полный анализ и разработка

## Оглавление

1. [Первоначальный анализ feasibility](#первоначальный-анализ)
2. [Проработка interaction plugin без middleware](#interaction-plugin-подход)
3. [Гибридный подход с Home Assistant Addon](#гибридный-подход)
4. [Структура репозитория](#структура-репозитория)

---

## Первоначальный анализ

[Исходный документ загружен пользователем]

**Основные выводы из feasibility analysis:**

- MSX и Music Assistant имеют фундаментально разные архитектуры стриминга
- MSX ожидает прямые HTTP audio URLs
- MA генерирует ephemeral flow URLs привязанные к registered players
- Требуется middleware для bridge между двумя системами
- Существует precedent: Alexa bridge для MA демонстрирует работоспособность flow URLs

**Три возможных подхода:**
1. Stream proxy approach (наиболее перспективный)
2. MPD relay approach (проще, но теряет контроль)
3. Interaction plugin approach (самый мощный, но сложный)

---

## Interaction plugin подход

### Запрос пользователя
> Изучи и проработай вариант интеграции с использованием interaction plugin без middleware

### Архитектура прямой интеграции

**Основная концепция:**
TypeScript/JavaScript приложение работает в iframe внутри MSX, напрямую подключается к WebSocket API Music Assistant и использует встроенный HTML5 Audio API для воспроизведения.

#### Компонентная структура

**1. WebSocket менеджер**
```typescript
class MusicAssistantClient {
  private ws: WebSocket;
  private messageId = 0;
  private pendingRequests = new Map();
  
  connect(host: string, token: string) {
    this.ws = new WebSocket(`ws://${host}:8095/ws`);
    this.ws.onopen = () => this.authenticate(token);
    this.ws.onmessage = (evt) => this.handleMessage(JSON.parse(evt.data));
  }
  
  async call(command: string, args: any): Promise<any> {
    const msgId = String(++this.messageId);
    return new Promise((resolve, reject) => {
      this.pendingRequests.set(msgId, { resolve, reject });
      this.ws.send(JSON.stringify({
        message_id: msgId,
        command,
        args
      }));
    });
  }
}
```

**2. Virtual Player регистрация**

Ключевой момент: plugin регистрируется как BuiltinPlayer (Web Audio API player):

```typescript
class MSXPlayer {
  private playerId: string;
  private audio: HTMLAudioElement;
  
  async register(client: MusicAssistantClient) {
    const result = await client.call('players/cmd/register_builtin_player', {
      player_id: 'msx_tv_' + Date.now(),
      player_name: 'MSX TV Player',
      device_info: {
        model: 'MSX Interaction Plugin',
        manufacturer: 'MSX',
        address: window.location.hostname
      }
    });
    
    this.playerId = result.player_id;
    this.setupAudioElement();
  }
  
  private setupAudioElement() {
    this.audio = new Audio();
    this.audio.preload = 'auto';
    
    this.audio.onplay = () => this.reportState('playing');
    this.audio.onpause = () => this.reportState('paused');
    this.audio.ontimeupdate = () => this.reportProgress();
    this.audio.onended = () => this.nextTrack();
  }
}
```

**3. Получение flow URL**

```typescript
async playTrack(trackUri: string) {
  await this.client.call('player_queues/play_media', {
    queue_id: this.playerId,
    media: [trackUri]
  });
  
  const queueState = await this.client.call('player_queues/get_state', {
    queue_id: this.playerId
  });
  
  const streamUrl = queueState.current_item?.stream_url;
  const mp3Url = streamUrl.replace('.flac', '.mp3');
  
  this.audio.src = mp3Url;
  this.audio.play();
}
```

### Критические технические ограничения

**1. CORS на MA stream server**
- Проблема: MA stream server (порт 8097) не отдает CORS headers по умолчанию
- Решение: Конфигурация MA или nginx reverse proxy

**2. Ограничения Smart TV браузеров**

| Платформа | WebSocket | HTML5 Audio | FLAC | MSE |
|-----------|-----------|-------------|------|-----|
| Samsung Tizen (Chromium 94) | ✅ | ✅ MP3/AAC | ⚠️ | ❌ |
| LG webOS (Chromium 79) | ✅ | ✅ базовый | ❌ | ❌ |
| Android TV / Fire TV | ✅ | ✅ полный | ✅ | ✅ |

**Вывод:** Обязательно запрашивать MP3 encoding от MA, не FLAC.

**3. Server-side seeking**

```typescript
async seek(position: number) {
  await this.client.call('player_queues/seek', {
    queue_id: this.playerId,
    position: position
  });
  
  const queueState = await this.client.call('player_queues/get_state', {
    queue_id: this.playerId
  });
  
  this.audio.src = queueState.current_item.stream_url;
  this.audio.play();
}
```

**4. Управление жизненным циклом player**

```typescript
class QueueManager {
  async subscribeToQueueEvents() {
    this.client.on('player_queue_items_update', (event) => {
      if (event.queue_id === this.playerId) {
        this.handleQueueUpdate(event);
      }
    });
  }
  
  async handleQueueUpdate(event: any) {
    const currentItem = event.queue_items[event.current_index];
    
    if (currentItem.uri !== this.currentTrackUri) {
      this.currentTrackUri = currentItem.uri;
      
      const queueState = await this.client.call('player_queues/get_state', {
        queue_id: this.playerId
      });
      
      this.audio.src = queueState.current_item.stream_url;
      this.audio.play();
      this.updateMSXNowPlaying(currentItem);
    }
  }
}
```

### Вывод по прямой интеграции

**✅ Реализуемо без middleware** для современных Smart TV (Android TV, Fire TV, Apple TV)

**⚠️ Требует дополнительных решений** для Samsung Tizen и LG webOS из-за ограничений браузеров

**🔧 Необходимые доработки на стороне MA:**
1. CORS headers на stream server (порт 8097)
2. Возможность запроса MP3 encoding
3. Документация по BuiltinPlayer registration

---

## Гибридный подход

### Запрос пользователя
> Проработай гибридный подход с установкой лёгкого middleware в качестве аддона к homeassistant

### Концепция архитектуры

**Разделение ответственности:**

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   MSX Client    │ ◄─────► │  MSX-MA Addon    │ ◄─────► │ Music Assistant │
│ (Smart TV)      │ WebSock │  (Lightweight)   │ Internal│    (HA Addon)   │
│                 │         │                  │ Network │                 │
│ - UI/Navigation │         │ - Stream Proxy   │         │ - Library API   │
│ - TypeScript    │         │ - CORS Headers   │         │ - Audio Streams │
│ - Interaction   │         │ - Codec Convert  │         │ - Queue Control │
│   Plugin        │         │ - Auth Relay     │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                            │
        │                            │
        └────── HTTP Audio ──────────┘
              (только стримы)
```

**Ключевые преимущества:**
- MSX plugin делает всю навигацию и UI (быстро, нативно)
- Addon проксирует только аудио потоки (решает CORS, кодеки, совместимость)
- Единая установка через Home Assistant Supervisor
- Доступ к internal network (MA доступен как `http://music-assistant:8095`)
- Минимальные ресурсы (только stream proxy)

### Home Assistant Addon структура

#### config.yaml

```yaml
name: MSX Music Assistant Bridge
version: "1.0.0"
slug: msx-ma-bridge
description: Stream Music Assistant library to Smart TVs via MSX
arch:
  - aarch64
  - amd64
  - armhf
  - armv7
  - i386
init: false
startup: services
services:
  - music-assistant:need

ports:
  8099/tcp: 8099

webui: "http://[HOST]:[PORT:8099]"

options:
  log_level: info
  enable_transcoding: true
  output_format: mp3
  output_quality: 320
  cors_allowed_origins:
    - "*"
```

#### Dockerfile

```dockerfile
FROM python:3.11-alpine

RUN apk add --no-cache \
    ffmpeg \
    curl \
    jq \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY bridge/ ./bridge/
COPY rootfs/ /

RUN adduser -D -u 1000 addon && \
    chown -R addon:addon /app

USER addon

EXPOSE 8099

CMD ["/usr/bin/run.sh"]
```

### Python Bridge Implementation

#### server.py (Основной сервер)

```python
class MSXBridgeServer:
    def __init__(self, config):
        self.config = config
        self.app = web.Application()
        self.ma_client = MusicAssistantClient(
            host=config['ma_host'],
            port=config['ma_port']
        )
        self.stream_proxy = StreamProxy(
            ma_client=self.ma_client,
            codec_handler=CodecHandler(config)
        )
        
        self.setup_routes()
        self.setup_cors()
    
    def setup_routes(self):
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/start.json', self.handle_start_json)
        self.app.router.add_get('/msx-plugin.js', self.handle_plugin_js)
        self.app.router.add_get('/stream/{track_uri}', self.handle_stream)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/ws', self.handle_websocket)
```

#### stream_proxy.py (Ключевая логика)

```python
class StreamProxy:
    async def proxy_stream(self, track_uri: str, request: web.Request):
        """
        1. Получаем flow URL от MA
        2. Транскодируем если нужно (FLAC→MP3)
        3. Проксируем с правильными headers
        """
        
        session_id = hashlib.md5(track_uri.encode()).hexdigest()
        flow_url = await self._get_flow_url(track_uri)
        
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': f'audio/{self.codec_handler.output_format}',
                'Accept-Ranges': 'none',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )
        
        await response.prepare(request)
        
        async with ClientSession() as session:
            async with session.get(flow_url) as ma_response:
                if self.codec_handler.needs_transcoding(ma_response.headers):
                    await self._transcode_stream(ma_response, response)
                else:
                    async for chunk in ma_response.content.iter_chunked(8192):
                        await response.write(chunk)
        
        await response.write_eof()
        return response
    
    async def _get_flow_url(self, track_uri: str) -> str:
        player_id = f"msx_proxy_{hashlib.md5(track_uri.encode()).hexdigest()[:8]}"
        
        await self.ma_client.call('players/cmd/register_builtin_player', {
            'player_id': player_id,
            'player_name': f'MSX Proxy {player_id}',
            'device_info': {
                'model': 'MSX Bridge',
                'manufacturer': 'Home Assistant Addon'
            }
        })
        
        await self.ma_client.call('player_queues/play_media', {
            'queue_id': player_id,
            'media': [track_uri],
            'option': {'auto_play': True}
        })
        
        queue_state = await self.ma_client.call('player_queues/get_state', {
            'queue_id': player_id
        })
        
        stream_url = queue_state['current_item']['stream_url']
        
        if self.codec_handler.output_format == 'mp3':
            stream_url = stream_url.replace('.flac', '.mp3')
        
        return stream_url
```

### MSX Interaction Plugin (упрощенная версия)

```typescript
const BRIDGE_HOST = window.location.hostname;
const BRIDGE_PORT = 8099;
const BRIDGE_URL = `http://${BRIDGE_HOST}:${BRIDGE_PORT}`;

class MSXMusicAssistantPlugin {
  async playTrack(data: any) {
    // Аудио идет через addon stream proxy!
    const streamUrl = `${BRIDGE_URL}/stream/${encodeURIComponent(data.track_uri)}`;
    
    await this.player.play(streamUrl, {
      title: data.title,
      artist: data.artist,
      image: data.image
    });
    
    TVXInteractionPlugin.executeAction(`player:label:${data.title} - ${data.artist}`);
    TVXInteractionPlugin.executeAction(`player:image:${data.image}`);
  }
}

class SimpleAudioPlayer {
  async play(streamUrl: string, metadata: any) {
    this.audio.src = streamUrl;
    await this.audio.play();
  }
}
```

### Преимущества гибридного подхода

**✅ Минимальные ресурсы**
- Addon занимает ~50MB RAM
- Нет дублирования API логики
- Plugin делает тяжелую работу на клиенте

**✅ Единая экосистема**
- Устанавливается через HA Supervisor
- Использует internal network с MA
- Автоматические обновления

**✅ Максимальная совместимость**
- Addon решает проблемы CORS
- Транскодирование FLAC→MP3
- Работает на всех MSX платформах

---

## Структура репозитория

### Запрос пользователя
> Разработай структуру репозитория для всех компонентов интеграции

### Полная структура

```
msx-music-assistant/
├── .github/
│   ├── workflows/
│   │   ├── build-addon.yml
│   │   ├── build-frontend.yml
│   │   ├── release.yml
│   │   └── test.yml
│   ├── ISSUE_TEMPLATE/
│   └── dependabot.yml
│
├── addon/                    # Home Assistant Addon
│   ├── config.yaml
│   ├── Dockerfile
│   ├── build.yaml
│   ├── rootfs/
│   ├── bridge/
│   │   ├── server.py
│   │   ├── stream_proxy.py
│   │   ├── ma_client.py
│   │   ├── codec_handler.py
│   │   └── utils/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/                 # MSX Interaction Plugin
│   ├── src/
│   │   ├── index.ts
│   │   ├── types/
│   │   ├── core/
│   │   ├── ui/
│   │   ├── services/
│   │   └── utils/
│   ├── dist/
│   ├── tests/
│   ├── package.json
│   ├── tsconfig.json
│   └── webpack.config.js
│
├── docs/
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── TROUBLESHOOTING.md
│   ├── DEVELOPMENT.md
│   └── API.md
│
├── scripts/
│   ├── build-addon.sh
│   ├── build-frontend.sh
│   ├── test-local.sh
│   └── setup-dev.sh
│
├── examples/
│   ├── docker-compose.yml
│   └── ha-config/
│
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── repository.json
```

### GitHub Actions Workflows

#### build-addon.yml

```yaml
name: Build Addon

on:
  push:
    branches: [main, dev]
    paths:
      - 'addon/**'

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        arch: [amd64, aarch64, armv7]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./addon
          platforms: linux/${{ matrix.arch }}
          push: ${{ github.event_name != 'pull_request' }}
```

#### release.yml

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  create-release:
    runs-on: ubuntu-latest
    steps:
      - name: Create Release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ steps.get_version.outputs.version }}
```

### Development Scripts

#### setup-dev.sh

```bash
#!/bin/bash

echo "🚀 Setting up MSX Music Assistant development..."

# Python environment
cd addon
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Node environment
cd frontend
npm install
cd ..

# Create local config
cat > .env.local << EOF
MA_HOST=localhost
MA_PORT=8095
LOG_LEVEL=debug
ENABLE_TRANSCODING=true
OUTPUT_FORMAT=mp3
