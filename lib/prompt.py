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

    if lang == "zh":
        role_label = "角色 A" if role == "A" else "角色 B"
        return f"""/loop dynamic 你是 coord {role_label}（{name}）。协调 Hub：{hub_url}

第一步：若尚未运行，启动后台 watcher（记录 PID）：
while true; do
  resp=$(curl -sf --max-time 3700 "{hub_url}/wait/{role}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "{sentinel} {{\\"hub\\":$resp}}"
done

每轮被唤醒或首次执行时：
1. 每轮都重新 curl -s {hub_url}/snapshot；不要依赖记忆，尤其是上下文压缩后（snapshot 含 profile、state、history、lessons、health）
2. 若 snapshot.state.stopped=true、recommended_action=stop，或 epoch >= max_epochs → 总结后停止 loop
3. 按 profile 中 {role_label} 的 goal、responsibilities、forbidden 执行
4. 完成后先记录结果，再 POST {hub_url}/signal 给对端；payload.outcome 必须是 progress、blocked、no-op、done 之一
5. 若发现可复用的经验/坑点，POST {hub_url}/lessons，包含 role、epoch、text
6. 按 workflow.transitions 设置 target/epoch/turn/stopped
7. 同一 epoch 只处理一次；不 push 除非用户要求

signal 示例（按 workflow 替换 target、epoch、turn、stopped）：
curl -s -X POST {hub_url}/signal -H "Content-Type: application/json" -d '{{"target":"{other_role}","epoch":1,"turn":"{other_role}","payload":{{"outcome":"progress","summary":"本轮完成内容"}}}}'
也可用脚本（先用 --dry-run 预览，确认后去掉 --dry-run 发送）：./scripts/signal.sh --dry-run {other_role} progress "本轮完成内容" 1 {other_role}
若 workflow.transition.stop=true，在脚本命令中加入 --stopped。

lesson 示例：
curl -s -X POST {hub_url}/lessons -H "Content-Type: application/json" -d '{{"role":"{role}","epoch":1,"text":"可复用经验或坑点"}}'"""

    role_label = "role A" if role == "A" else "role B"
    return f"""/loop dynamic You are coord {role_label} ({name}). Hub: {hub_url}

Step 1 — start background watcher if not running (record PID):
while true; do
  resp=$(curl -sf --max-time 3700 "{hub_url}/wait/{role}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "{sentinel} {{\\"hub\\":$resp}}"
done

Each wake or first run:
1. Re-read curl -s {hub_url}/snapshot every round; do not rely on memory, especially after context compaction (snapshot includes profile, state, history, lessons, health)
2. If snapshot.state.stopped=true, recommended_action=stop, or epoch >= max_epochs → summarize and stop loop
3. Follow {role_label} goal, responsibilities, forbidden from profile
4. Record the result before advancing, then POST {hub_url}/signal to the other role; payload.outcome must be one of progress, blocked, no-op, done
5. When you learn a reusable lesson or pitfall, POST {hub_url}/lessons with role, epoch, text
6. Set target/epoch/turn/stopped according to workflow.transitions
7. Process each epoch once; do not push unless user asks

Signal example (replace target, epoch, turn, stopped according to workflow):
curl -s -X POST {hub_url}/signal -H "Content-Type: application/json" -d '{{"target":"{other_role}","epoch":1,"turn":"{other_role}","payload":{{"outcome":"progress","summary":"what changed this round"}}}}'
Or use the helper (preview with --dry-run first, then remove --dry-run to send): ./scripts/signal.sh --dry-run {other_role} progress "what changed this round" 1 {other_role}
If workflow.transition.stop=true, add --stopped to the helper command.

Lesson example:
curl -s -X POST {hub_url}/lessons -H "Content-Type: application/json" -d '{{"role":"{role}","epoch":1,"text":"reusable lesson or pitfall"}}'"""
