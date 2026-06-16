---
name: hermes-discord-integration
description: Configure and troubleshoot Hermes Agent's Discord platform integration — auto_thread, free_response_channels, permissions, thread behavior, and config pitfalls.
version: 1.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, discord, gateway, config, threads, troubleshooting]
---

# Hermes Discord Integration

Hermes Gateway의 Discord 플랫폼 어댑터 설정, auto_thread 동작 방식, 권한 요구사항, 그리고 자주 마주치는 설정 함정을 다룬다.

## 설정 구조

Discord 설정은 `~/.hermes/config.yaml`의 `discord:` 섹션에 정의된다. 게이트웨이 시작 시 `DISCORD_*` 환경변수로 주입된다 (adapter.py:6410).

```yaml
discord:
  require_mention: true            # @mention 필수 여부
  free_response_channels: "id1,id2"  # @mention 없이 응답하는 채널
  allowed_channels: "id1,id2,id3"    # 봇이 청취하는 채널 (빈값=전체)
  auto_thread: true                  # @mention 시 자동 스레드 생성
  thread_require_mention: false      # 스레드 내 @mention 필수 여부
  no_thread_channels: ""             # 스레드 생성 안 할 채널
  history_backfill: true             # 과거 메시지 백필
  history_backfill_limit: 50
  reactions: true                    # 이모지 리액션
  channel_prompts: {}                # 채널별 프롬프트
  dm_role_auth_guild: "guild_id"    # DM 인증 길드
  server_actions: ""                 # 서버 액션 (slash commands)
  allow_any_attachment: false
  max_attachment_bytes: 33554432
```

### require_mention + free_response_channels 우선순위

1. `free_response_channels`에 등록된 채널 → @mention 없이 응답
2. 그 외 채널 + `require_mention: true` → @mention 필수
3. `allowed_channels`가 설정된 경우 → 해당 채널만 응답 (화이트리스트)

## auto_thread 동작 방식

### 기본 메커니즘 (adapter.py:4797-4814)

```
if not is_thread and not is_DM:
    skip_thread = bool(no_thread_channels에 포함) or is_free_channel  ← 핵심!
    if auto_thread and not skip_thread:
        thread = await _auto_create_thread(message)
```

**auto_thread가 발동하는 조건 (모두 충족):**
1. `auto_thread: true`
2. 메시지가 DMedit:thread가 아님
3. `skip_thread = False` — 즉:
   - 채널이 `no_thread_channels`에 없음 AND
   - 채널이 `free_response_channels`에 **없음** AND
   - 채널이 voice-linked channel이 아님 AND
   - 메시지가 reply 타입이 아님

### ⚠️ 핵심 함정: free_response_channels ≠ auto_thread

**`free_response_channels`에 등록된 채널에서는 auto_thread가 절대 발동하지 않는다.** 코드 레벨에서 `skip_thread = is_free_channel`로 명시적으로 차단된다.

```python
# adapter.py:4805
skip_thread = bool(channel_ids & no_thread_channels) or is_free_channel
```

**설계 의도:** auto_thread는 @mention으로 봇을 호출했을 때 해당 메시지 밑에 스레드를 생성하는 기능이다. free_response_channels에서는 @mention이 없으므로 스레드 생성 기준점이 되는 메시지가 없다는 논리.

**영향:** `#일반` 채널을 `free_response_channels`에 등록해두면 @mention 없이 자유롭게 응답하지만, 모든 응답이 메인 채널에 직접 게시된다.

### 원하는 동작별 설정법

| 원하는 동작 | free_response_channels | require_mention | auto_thread | 결과 |
|------------|----------------------|----------------|-------------|------|
| 메인 채널 직접 응답 | 채널ID 포함 | true | any | @mention 없이 메인 채널에 응답 |
| @mention + 스레드 | 채널ID 제외 | true | true | @mention 시 스레드 자동 생성 |
| 모든 메시지 스레드화 | (코드 수정 필요) | false | true | adapter.py:4805 수정 필요 |

## 스레드 생성 진단

### 게이트웨이 로그 확인

```bash
# 모든 응답의 thread= 값 확인
grep "response ready.*discord" ~/.hermes/logs/gateway.log | tail -10
```

- `thread=None` → auto_thread가 발동하지 않음 (free 채널이거나 @mention 없음)
- `thread=123456789` → 스레드 생성 성공

### 실패 원인 진단

```bash
# auto_thread 실패 로그 확인
grep -i "auto.thread\|thread.*fail\|create_thread" ~/.hermes/logs/gateway.log | tail -20
```

### Discord 권한 확인

봇이 스레드를 생성하려면 Discord Developer Portal에서 다음 권한이 필요하다:
- **Create Public Threads** — `CREATE_PUBLIC_THREADS` (0x8000000000)
- **Send Messages in Threads** — `SEND_MESSAGES_IN_THREADS` (0x4000000000)

권한이 없으면 `_auto_create_thread()`가 조용히 실패하고 (direct_error catch), 폴백으로 seed message + 스레드 생성을 시도한다. 둘 다 실패하면 warning 로그가 남는다.

## 채널 ID 확인

```bash
# channel_directory.json에서 채널 목록 확인
cat ~/.hermes/channel_directory.json | python3 -m json.tool
```

채널이 목록에 없으면 봇에 `View Channels` 권한이 없는 것이다.

## 게이트웨이 재시작

config.yaml 변경 후 반드시 필요:
```bash
systemctl --user restart hermes-gateway
```

## 참조

- `references/auto-thread-code-analysis.md` — adapter.py 소스코드 분석 및 auto_thread 결정 트리
- `hermes-agent` skill의 `references/discord-troubleshooting.md` — 연결 문제 진단 (401, Message Content Intent 등)
- Hermes docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
