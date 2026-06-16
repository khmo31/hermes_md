# auto_thread 코드 분석 (adapter.py)

> Hermes Agent v0.16.0 (2026.6.5) 기준
> 파일: `/home/khmo31/.local/lib/python3.12/site-packages/plugins/platforms/discord/adapter.py`

## auto_thread 결정 트리 (lines 4797-4815)

```python
# Line 4797-4799:
# Auto-thread: when enabled, automatically create a thread for every
# @mention in a text channel so each conversation is isolated (like Slack).
# Messages already inside threads or DMs are unaffected.

auto_threaded_channel = None
if not is_thread and not isinstance(message.channel, discord.DMChannel):
    no_thread_channels_raw = os.getenv("DISCORD_NO_THREAD_CHANNELS", "")
    no_thread_channels = {ch.strip() for ch in no_thread_channels_raw.split(",") if ch.strip()}
    skip_thread = bool(channel_ids & no_thread_channels) or is_free_channel  # LINE 4805 — 핵심!
    auto_thread = os.getenv("DISCORD_AUTO_THREAD", "true").lower() in {"true", "1", "yes"}
    is_reply_message = getattr(message, "type", None) == discord.MessageType.reply
    if auto_thread and not skip_thread and not is_voice_linked_channel and not is_reply_message:
        thread = await self._auto_create_thread(message)
        if thread:
            parent_channel_id = str(message.channel.id)
            is_thread = True
            thread_id = str(thread.id)
            auto_threaded_channel = thread
            self._threads.mark(thread_id)
```

## 결정 조건 분석

### auto_thread 발동 조건 (AND):
1. `not is_thread` — 이미 스레드 내부가 아님
2. `not isinstance(message.channel, discord.DMChannel)` — DM이 아님
3. `not skip_thread` — 다음 모두 False:
   - 채널이 `DISCORD_NO_THREAD_CHANNELS`에 없음
   - **채널이 `free_response_channels`에 없음** ← `is_free_channel`
4. `not is_voice_linked_channel` — voice-linked channel이 아님
5. `not is_reply_message` — reply 메시지가 아님

### `is_free_channel` 계산 (lines 4777-4781)

```python
is_free_channel = (
    "*" in free_channels
    or bool(channel_ids & free_channels)
    or is_voice_linked_channel
)
```

`channel_ids`에는 현재 메시지 채널 ID와 부모 채널 ID(스레드인 경우)가 포함된다.

## _auto_create_thread 구현 (lines 4154-4193)

```python
async def _auto_create_thread(self, message: 'DiscordMessage') -> Optional[Any]:
    # 스레드명 = 메시지 앞 80자 (멘션 문법 제거)
    content = (message.content or "").strip()
    content = re.sub(r"<@[!&]?\d+>", "", content)
    content = re.sub(r"<#\d+>", "", content)
    content = re.sub(r"\s+", " ", content).strip()
    thread_name = content[:80] if content else "Hermes"

    try:
        # 1차 시도: message.create_thread()
        thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)
        return thread
    except Exception as direct_error:
        # 2차 시도: seed message + create_thread (fallback)
        seed_msg = await message.channel.send(f"🧵 Thread created by Hermes: **{thread_name}**")
        thread = await seed_msg.create_thread(
            name=thread_name,
            auto_archive_duration=1440,
            reason=f"Auto-threaded from mention by {display_name}",
        )
        return thread
        # 둘 다 실패 → None 반환, warning 로그
```

## config.yaml → 환경변수 주입 (lines 6410-6411)

```python
if "auto_thread" in discord_cfg and not os.getenv("DISCORD_AUTO_THREAD"):
    os.environ["DISCORD_AUTO_THREAD"] = str(discord_cfg["auto_thread"]).lower()

if "thread_require_mention" in discord_cfg and not os.getenv("DISCORD_THREAD_REQUIRE_MENTION"):
    os.environ["DISCORD_THREAD_REQUIRE_MENTION"] = str(discord_cfg["thread_require_mention"]).lower()
```

게이트웨이 시작 시 config.yaml → `DISCORD_AUTO_THREAD` 환경변수로 변환. 이미 환경변수가 있으면 덮어쓰지 않음.

## 진단: 로그에서 thread= 값 해석

```bash
grep "response ready.*discord" ~/.hermes/logs/gateway.log | tail -5
```

예시 출력:
```
response ready: platform=discord chat=xxxxxxxxxxxxxxxxx738 thread=None ...
```

- `thread=None` → auto_thread 미발동 (free 채널이거나 skip_thread 조건 충족)
- `thread=123456789` → 스레드 생성 성공
- 로그에 "Auto-thread creation failed" warning → 권한 부족 또는 API 오류

## 실제 사례: #일반 채널 (2026-06-16)

**설정 상태:**
```yaml
discord:
  auto_thread: true
  require_mention: true
  free_response_channels: xxxxxxxxxxxxxxxxx738,xxxxxxxxxxxxxxxxx962  # #일반 포함
  allowed_channels: ...xxxxxxxxxxxxxxxxx738...
```

**관찰된 동작:** 모든 응답이 `thread=None`으로 로깅됨 → 메인 채널에 직접 게시

**원인:** `#일반`(xxxxxxxxxxxxxxxxx738)이 `free_response_channels`에 등록되어 `is_free_channel = True`, 따라서 `skip_thread = True`, auto_thread가 발동하지 않음

**해결:** `#일반`을 `free_response_channels`에서 제거하면 auto_thread 발동. 단, @mention 필요.
