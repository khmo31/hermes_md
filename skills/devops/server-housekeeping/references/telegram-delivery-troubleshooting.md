# Telegram Delivery Troubleshooting

When Telegram cron deliveries fail, here's the debugging sequence.

## Step 1: Check cron status

```bash
cronjob action=list
```

Look for `last_delivery_error` field on the job.

## Step 2: Common Telegram delivery failures

### "no delivery target resolved for deliver=telegram"

**Cause:** Bare platform name `"telegram"` is ambiguous — the scheduler can't resolve it to a specific chat.

**Fix:** Always include chat ID:
- DM: `"telegram:USER_CHAT_ID"` (user's Telegram chat ID)
- Group: `"telegram:-100GROUP_ID"` (group ID with -100 prefix)
- Topic: `"telegram:-100GROUP_ID:TOPIC_ID"` (group_id:topic_id)

### Multiple cron jobs flooding Telegram DM

**Problem:** All cron jobs deliver to the same Telegram DM, creating an unreadable stream.

**Solutions (in order of practicality):**

1. **Route to Discord channels instead** — Discord supports channel categorization natively. Route different cron outputs to different channels by using per-channel delivery targets.

2. **Telegram Folders** (client-side) — User creates folders in Telegram app settings. Each folder contains specific chats. User must set up manually.

3. **Telegram Group with Topics** — Create a Telegram supergroup with Topics enabled, then route to specific topic IDs. Requires user to create the group and add the bot.

## Step 3: Verify delivery at fire time

After fixing, check the next run:

```bash
cronjob action=list
# Verify next_run_at is upcoming, last_delivery_error is empty, last_status is "ok"
```
