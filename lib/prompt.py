from __future__ import annotations

from typing import Any


def build_prompt(role: str, profile: dict[str, Any], hub_url: str) -> str:
    role = role.upper()
    if role not in ("A", "B"):
        raise ValueError("role must be A or B")

    r = profile["roles"][role]
    lang = profile.get("lang", "en")
    sentinel = r.get("wakeSentinel", f"AGENT_LOOP_WAKE_{role}")
    name = r.get("name", role)
    hub_url = hub_url.rstrip("/")
    other_role = "B" if role == "A" else "A"
    watcher_snippet = f"""last_wake_id=0
while true; do
  resp=$(curl -sf --max-time 3700 "{hub_url}/wait/{role}?since=${{last_wake_id}}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  next_wake_id=$(printf '%s' "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id", 0))' 2>/dev/null || echo 0)
  if [ "$next_wake_id" -gt "$last_wake_id" ] 2>/dev/null; then last_wake_id="$next_wake_id"; fi
  echo "{sentinel} {{\\"hub\\":$resp}}"
done"""

    if lang == "zh":
        role_label = "角色 A" if role == "A" else "角色 B"
        return f"""/loop dynamic 你是 coord {role_label}（{name}）。协调 Hub：{hub_url}

第一步：若尚未运行，启动后台 watcher（记录 PID）。watcher 必须输出到当前 agent 终端 stdout；不要重定向到文件，否则 /loop 看不到唤醒。watcher 使用 wake id 自愈去重，多个 watcher 不会抢走彼此的消息：
{watcher_snippet}

每轮被唤醒或首次执行时：
1. 每轮都重新 curl -s {hub_url}/snapshot；不要依赖记忆，尤其是上下文压缩后（snapshot 含 profile、state、history、lessons、health）
2. 若 snapshot.state.stopped=true、recommended_action=stop，或 epoch >= max_epochs → 总结后停止 loop
3. 判断是否轮到你：被 watcher 唤醒（收到发给你的 signal）即表示轮到你，继续执行；若为首次启动且未收到唤醒，仅当 state.turn == {role} 时才执行，否则不要动作，回到 watcher 等待对端 signal
4. 按 profile 中 {role_label} 的 goal、responsibilities、forbidden 执行
5. 完成后先记录结果，再 POST {hub_url}/signal 给对端；payload.outcome 必须是 progress、blocked、no-op、done 之一
6. 若发现可复用的经验/坑点，POST {hub_url}/lessons，包含 role、epoch、text
7. 按 workflow.transitions 设置 target/epoch/turn/stopped（hub 默认把 turn 设为 signal 的 target，省略 turn 也不会留下错误回合）
8. 同一 epoch 只处理一次；不 push 除非用户要求

signal 示例（按 workflow 替换 target、epoch、turn、stopped）：
curl -s -X POST {hub_url}/signal -H "Content-Type: application/json" -d '{{"target":"{other_role}","epoch":1,"turn":"{other_role}","payload":{{"outcome":"progress","summary":"本轮完成内容"}}}}'
也可用脚本（先用 --dry-run 预览，确认后去掉 --dry-run 发送）：./scripts/signal.sh --dry-run {other_role} progress "本轮完成内容" 1 {other_role}
若 workflow.transition.stop=true，在脚本命令中加入 --stopped。

lesson 示例：
curl -s -X POST {hub_url}/lessons -H "Content-Type: application/json" -d '{{"role":"{role}","epoch":1,"text":"可复用经验或坑点"}}'"""

    role_label = "role A" if role == "A" else "role B"
    return f"""/loop dynamic You are coord {role_label} ({name}). Hub: {hub_url}

Step 1 — start background watcher if not running (record PID). The watcher must print to this agent terminal's stdout; do not redirect it to a file, or /loop will not see the wake. The watcher uses wake ids for self-healing dedupe, so duplicate watchers cannot steal each other's wake:
{watcher_snippet}

Each wake or first run:
1. Re-read curl -s {hub_url}/snapshot every round; do not rely on memory, especially after context compaction (snapshot includes profile, state, history, lessons, health)
2. If snapshot.state.stopped=true, recommended_action=stop, or epoch >= max_epochs → summarize and stop loop
3. Decide whether it is your turn: being woken by the watcher (a signal addressed to you) means it is your turn — proceed. On a first run without a wake, only act when state.turn == {role}; otherwise do nothing and return to the watcher to wait for the other role's signal
4. Follow {role_label} goal, responsibilities, forbidden from profile
5. Record the result before advancing, then POST {hub_url}/signal to the other role; payload.outcome must be one of progress, blocked, no-op, done
6. When you learn a reusable lesson or pitfall, POST {hub_url}/lessons with role, epoch, text
7. Set target/epoch/turn/stopped according to workflow.transitions (the hub defaults turn to the signal target, so omitting turn never leaves a stale turn)
8. Process each epoch once; do not push unless user asks

Signal example (replace target, epoch, turn, stopped according to workflow):
curl -s -X POST {hub_url}/signal -H "Content-Type: application/json" -d '{{"target":"{other_role}","epoch":1,"turn":"{other_role}","payload":{{"outcome":"progress","summary":"what changed this round"}}}}'
Or use the helper (preview with --dry-run first, then remove --dry-run to send): ./scripts/signal.sh --dry-run {other_role} progress "what changed this round" 1 {other_role}
If workflow.transition.stop=true, add --stopped to the helper command.

Lesson example:
curl -s -X POST {hub_url}/lessons -H "Content-Type: application/json" -d '{{"role":"{role}","epoch":1,"text":"reusable lesson or pitfall"}}'"""
