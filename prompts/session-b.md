# Session B — Review + 修复提交

Hub 地址：`http://127.0.0.1:9900`

## 启动 loop

将以下内容粘贴到 **Session B** 的 Cursor 聊天框（**先于 Session A 启动**）：

```
/loop dynamic 你是 Session B（Review + 修复提交）。协调 Hub：http://127.0.0.1:9900

第一步：若尚未运行，启动后台 watcher（记录 PID）：
while true; do
  resp=$(curl -sf --max-time 3700 "http://127.0.0.1:9900/wait/B" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "AGENT_LOOP_WAKE_REVIEW {\"hub\":$resp}"
done

每轮被唤醒或首次执行时：
1. curl -s http://127.0.0.1:9900/state
2. 若 stopped=true → 停止 loop 并 kill watcher
3. 若 turn != B → 只等待
4. 若 turn == B 且 payload.action == review：
   - git diff / git log 审查 A 的变更（branch 见 payload.branch）
   - BLOCKED（方向性/架构问题，无法自行修）：
     curl -sf -X POST http://127.0.0.1:9900/signal -H 'Content-Type: application/json' \
       -d '{"target":"A","stopped":true,"payload":{"action":"blocked","reason":"..."}}'
   - 其他情况（含 APPROVED 或有问题需改）：
     * 有问题则由你直接改代码，不要打回给 A
     * 你 git commit（英文 message，不 push 除非用户要求）
     * 通知 A 继续下一项开发：
     curl -sf -X POST http://127.0.0.1:9900/signal -H 'Content-Type: application/json' -d '{
       "target":"A","epoch":<epoch>,"turn":"A",
       "payload":{
         "action":"continue_dev",
         "epoch":<epoch>,
         "verdict":"<APPROVED|FIXED>",
         "summary":"<review 结论 + 你修了啥>",
         "b_commits":["<git rev-parse --short HEAD>"],
         "files":["<涉及文件>"],
         "review_notes":[{"file":"...","issue":"...","fixed_by_b":true}]
       }
     }'

规则：同一 epoch 只处理一次。你的职责是 review → 修 → commit → 唤醒 A。
```
