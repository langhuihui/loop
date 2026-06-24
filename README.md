# cursor-ab-coord

Coordinate two [Cursor](https://cursor.com) chat sessions (A = dev, B = review) via a local HTTP hub and `/loop` dynamic wake.

```
Session A (dev)  ──POST /signal──►  Coord Hub (:9900)  ──GET /wait/B──►  Session B (review)
       ▲                                      │                                    │
       └──────────── POST /signal (continue) ─┘◄──── review → fix → commit ────────┘
```

## Why

Cursor `/loop` only wakes **the current session**. Cross-session work needs an external bus. This hub lets each session run a background `curl /wait/<role>` watcher; when the other side POSTs a signal, the watcher prints a sentinel and the agent wakes up.

**Workflow**

1. **A** implements on `state.branch`
2. **A** signals **B** (`action: review`)
3. **B** reviews, fixes issues directly, commits
4. **B** signals **A** (`action: continue_dev`)
5. **A** continues the next slice of work

## Requirements

- Python 3.9+ (stdlib only)
- `curl`
- Cursor with `/loop` support (local Agents window)

## Quick start

```bash
git clone <your-repo-url>
cd cursor-ab-coord

# 1. Start hub
./scripts/start.sh

# 2. Set task + branch
./scripts/reset.sh "Implement feature X" main

# 3. Open two Cursor chats in the same repo
#    - Session B first: paste prompts/session-b.md
#    - Session A second: paste prompts/session-a.md
```

## Scripts

| Script | Description |
|--------|-------------|
| `./scripts/start.sh` | Start hub on `127.0.0.1:9900` |
| `./scripts/stop.sh` | Stop hub |
| `./scripts/status.sh` | Print hub state |
| `./scripts/reset.sh "<task>" [branch]` | Reset epoch, set task, `turn=A` |

Environment overrides:

| Variable | Default |
|----------|---------|
| `COORD_HUB_URL` | `http://127.0.0.1:9900` |
| `COORD_HUB_HOST` | `127.0.0.1` |
| `COORD_HUB_PORT` | `9900` |
| `COORD_MAX_EPOCHS` | `20` |

## HTTP API

### `GET /state`

Current coordination state (`epoch`, `turn`, `task`, `branch`, `stopped`, …).

### `GET /wait/A` · `GET /wait/B`

Long-poll (up to 1h). Returns `200` with `{ "epoch", "payload" }` when a message arrives, or `204` on timeout.

### `POST /signal`

```json
{
  "target": "B",
  "epoch": 1,
  "turn": "B",
  "payload": { "action": "review", "summary": "..." }
}
```

### `POST /reset`

```json
{
  "task": "Implement feature X",
  "branch": "main",
  "turn": "A",
  "epoch": 0,
  "max_epochs": 20
}
```

See `examples/` for sample payloads.

## Prompts

Copy-paste ready `/loop` prompts:

- [`prompts/session-a.md`](prompts/session-a.md) — developer
- [`prompts/session-b.md`](prompts/session-b.md) — reviewer (fix + commit)

Optional standalone watchers (if not embedded in the prompt):

```bash
./watchers/wait-a.sh   # Session A
./watchers/wait-b.sh   # Session B
```

## Payload actions

| `payload.action` | From | Meaning |
|------------------|------|---------|
| `review` | A → B | A finished a slice; B should review |
| `continue_dev` | B → A | B reviewed (and fixed if needed); A continues |
| `blocked` | B → A | Stop loop; human intervention needed |

## Stop

- Say "stop loop" in either session (agent should kill watcher + optionally `POST /signal` with `"stopped": true`)
- Or: `./scripts/stop.sh`

## License

MIT — see [LICENSE](LICENSE).
