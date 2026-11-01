# Homelab DevOps

Домашняя лаборатория на базе Proxmox VE с полным стеком DevOps: виртуализация, контейнеризация, CI/CD, мониторинг, VPN и локальные LLM.

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Proxmox VE (anton)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  CT 107  │  │  CT 110  │  │  CT 105  │  │ CT 106 │  │
│  │  GitLab  │  │  Runner  │  │Prometheus│  │ Grafana│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  CT 103  │  │  CT 108  │  │  CT 116  │  │ CT 129 │  │
│  │  Ollama  │  │  Nginx   │  │ OpenCode │  │Code-Srv│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  VM 111: docker-host (open-webui, GPU passthrough)│   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Стек

- **Виртуализация:** Proxmox VE, LXC-контейнеры, KVM VM
- **CI/CD:** GitLab + GitLab Runner
- **Контейнеризация:** Docker, Docker Compose
- **Мониторинг:** Prometheus + Grafana (дашборды VPN, GPU, peers)
- **LLM:** Ollama (qwen2.5-coder, qwen3-coder) на AMD RX 7700S
- **Сеть:** AmneziaWG, Xray, gost, WARP, TPROXY, DNAT
- **Автоматизация:** Python-скрипты, systemd-юниты, bash

## Сервисы

### Docker Compose стек (`/opt/docker-build/`, `/opt/ml-stack/`)
- PostgreSQL 14
- MLflow (tracking server)
- ml-api (FastAPI, Ollama integration)
- telegram-bot

### Мониторинг
- Prometheus: сбор метрик с LXC, VM, GPU, VPN-пиров
- Grafana: дашборды (VPN туннели, AmneziaWG peers, GPU)

### VPN и сеть
- AmneziaWG (awg1) — телефоны, Meta/Google/Telegram через Xray TPROXY
- Xray — проксирование на LikeVPS (FR)
- gost — SOCKS5 форвардинг
- WARP — байпас (TCP мёртв)

## Структура репозитория

```
homelab-devops/
├── docker-compose.yml          # ML-стек
├── prometheus.yml              # конфиг Prometheus
├── scripts/
│   ├── phase2-watchdog.sh      # watchdog
│   ├── iperf3-lan-open.sh      # тест пропускной способности
│   ├── run.sh                  # запуск сервисов
│   ├── server_info.py          # сбор информации о сервере
│   ├── updater.py              # обновление
│   └── orchestrator.py         # оркестратор задач
├── grafana/                    # дашборды (JSON)
└── README.md
```

## Безопасность

Все секреты (пароли, токены, ключи) вынесены в переменные окружения или `.env` файлы, которые не коммитятся в репозиторий.

## CI/CD

GitLab CI/CD пайплайн (`.gitlab-ci.yml`) включает:
- **Lint**: проверка синтаксиса docker-compose
- **Build**: сборка Docker-образов
- **Deploy**: ручной деплой стека (кнопка в GitLab UI)

Runner: CT 110 (GitLab Runner на Proxmox)

### Скриншоты

| Grafana Dashboard | Prometheus Targets |
|---|---|
| ![Grafana](screenshots/grafana.png) | ![Prometheus](screenshots/prometheus.png) |

> Скриншоты можно добавить в папку `screenshots/`
