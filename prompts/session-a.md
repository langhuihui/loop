# Session A — 开发

Hub 地址：`http://127.0.0.1:9900`（可通过环境变量 `COORD_HUB_URL` 覆盖）

## 启动 loop

将以下内容粘贴到 **Session A** 的 Cursor 聊天框：

```
/loop dynamic 你是 Session A（开发）。协调 Hub：http://127.0.0.1:9900

第一步：若尚未运行，启动后台 watcher（记录 PID）：
while true; do
  resp=$(curl -sf --max-time 3700 "http://127.0.0.1:9900/wait/A" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "AGENT_LOOP_WAKE_DEV {\"hub\":$resp}"
done

每轮被唤醒或首次执行时：
1. curl -s http://127.0.0.1:9900/state
2. 若 stopped=true → 总结后停止 loop
3. 若 epoch >= max_epochs → 停止
4. 若 payload.action == blocked → 停止，说明需人工介入
5. 若 payload.action == continue_dev（B 已 review/修完并提交）：
   - 阅读 payload.summary、b_commits、files
   - 在 B 提交基础上，继续 state.task 的下一项（不重复 B 已修内容）
   - 完成后 new_epoch = state.epoch + 1，通知 B：
     curl -sf -X POST http://127.0.0.1:9900/signal -H 'Content-Type: application/json' -d '{
       "target":"B","epoch":<new_epoch>,"turn":"B",
       "payload":{"action":"review","epoch":<new_epoch>,"branch":"<branch>",
         "summary":"<本轮摘要>","files":["..."],"commit":"<git rev-parse --short HEAD>"}
     }'
6. 若 turn == A 且尚无 B 回馈（首轮）：
   - 按 state.task 开发，完成后同样 POST 给 B（action=review）

规则：你不负责修 review 意见，那是 B 的工作。同一 epoch 只处理一次。不 push 除非用户要求。
```
