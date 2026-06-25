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
1. curl -s {hub_url}/profile  → 读取 roles、workflow、task 约束
2. curl -s {hub_url}/state    → 读取 epoch、turn、stopped
3. 若 stopped=true 或 epoch >= max_epochs → 总结后停止 loop
4. 按 profile 中 {role_label} 的 goal、responsibilities、forbidden 执行
5. 按 workflow.transitions 在完成后 POST {hub_url}/signal 给对端
6. 同一 epoch 只处理一次；不 push 除非用户要求"""

    role_label = "role A" if role == "A" else "role B"
    return f"""/loop dynamic You are coord {role_label} ({name}). Hub: {hub_url}

Step 1 — start background watcher if not running (record PID):
while true; do
  resp=$(curl -sf --max-time 3700 "{hub_url}/wait/{role}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "{sentinel} {{\\"hub\\":$resp}}"
done

Each wake or first run:
1. curl -s {hub_url}/profile  → roles, workflow, task constraints
2. curl -s {hub_url}/state    → epoch, turn, stopped
3. If stopped=true or epoch >= max_epochs → summarize and stop loop
4. Follow {role_label} goal, responsibilities, forbidden from profile
5. On completion POST {hub_url}/signal per workflow.transitions
6. Process each epoch once; do not push unless user asks"""
