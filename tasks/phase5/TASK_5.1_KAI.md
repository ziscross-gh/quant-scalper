# Task 5.1: IBKR Gateway Testing

**Owner:** Kai (squad-kai)
**Status:** 🔴 NOT STARTED
**Priority:** 🔥 CRITICAL
**Deadline:** Complete within 1 hour
**Assigned:** February 3, 2026 10:35 AM GMT+8

---

## 🎯 Objective

Verify the bot can connect to IBKR Gateway reliably in paper mode and handle connection lifecycle.

---

## 📋 Configuration

- **Account:** DUO779750 (paper trading)
- **Host:** 127.0.0.1
- **Port:** 4002
- **Client ID:** 1
- **Reconnect delay:** 10s
- **Max reconnect attempts:** 5

---

## ✅ Checklist

- [ ] Verify IBKR Gateway is running on port 4002
- [ ] Test initial connection
- [ ] Verify connection stays alive for 10+ minutes
- [ ] Test graceful disconnection
- [ ] Test auto-reconnect (stop/restart Gateway)
- [ ] Verify connection error handling

---

## 🚀 Steps to Execute

### Step 1: Verify Gateway is Running
```bash
# Check if port 4002 is listening
lsof -i :4002
```

**Expected:** IBKR Gateway process listening on port 4002

---

### Step 2: Test Basic Connection
```bash
cd /Users/ziscross/.openclaw/workspace/quant-scalper
source venv/bin/activate
python -c "
from bot.ibkr.client import IBKRClient
import asyncio

async def test_connection():
    client = IBKRClient('127.0.0.1', 4002, 1)
    try:
        print('Attempting to connect...')
        await client.connect()
        print('✅ Connected successfully!')
        await asyncio.sleep(10)  # Stay connected for 10 seconds
        await client.disconnect()
        print('✅ Disconnected successfully!')
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_connection())
"
```

**Expected Output:**
```
Attempting to connect...
✅ Connected successfully!
✅ Disconnected successfully!
```

---

### Step 3: Test Connection Stability
```bash
python -c "
from bot.ibkr.client import IBKRClient
import asyncio

async def test_stability():
    client = IBKRClient('127.0.0.1', 4002, 1)
    try:
        await client.connect()
        print('✅ Connected!')
        for i in range(6):
            await asyncio.sleep(60)  # 1 minute intervals
            if await client.is_connected():
                print(f'✅ Still connected after {i+1} minute(s)')
            else:
                print('❌ Connection lost!')
                break
        await client.disconnect()
        print('✅ Test completed!')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test_stability())
"
```

**Expected:** Connection stays alive for 6 minutes with no drops

---

### Step 4: Test Auto-Reconnect

1. Start the connection test
2. While connected, stop IBKR Gateway
3. Wait 10 seconds
4. Start IBKR Gateway
5. Verify auto-reconnect works

```bash
python -c "
from bot.ibkr.client import IBKRClient
import asyncio

async def test_reconnect():
    client = IBKRClient('127.0.0.1', 4002, 1)
    try:
        await client.connect()
        print('✅ Connected!')
        print('⚠️  Please stop IBKR Gateway now and restart after 10 seconds...')
        for i in range(60):
            await asyncio.sleep(1)
            if not await client.is_connected():
                print(f'🔌 Connection lost at second {i+1}')
                break
        print('Waiting for auto-reconnect...')
        for i in range(30):
            await asyncio.sleep(1)
            if await client.is_connected():
                print(f'✅ Auto-reconnected after {i+1} seconds!')
                break
        await client.disconnect()
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test_reconnect())
"
```

**Expected:** Auto-reconnect within 10-30 seconds after Gateway restart

---

## 📊 Success Criteria

- [ ] Connection established successfully
- [ ] Connection stays stable for 10+ minutes
- [ ] Graceful disconnection works
- [ ] Auto-reconnect functions correctly
- [ ] No connection-related errors in logs

---

## 📝 Report Template

When complete, update this file with your findings:

```markdown
## Results

**Status:** ✅ PASSED / ❌ FAILED

**Connection Test:**
- ✅ / ❌ Connected successfully
- ✅ / ❌ Stayed connected for 10+ minutes
- ✅ / ❌ Disconnected gracefully

**Auto-Reconnect Test:**
- ✅ / ❌ Detected Gateway shutdown
- ✅ / ❌ Reconnected within 30 seconds
- ✅ / ❌ No errors during reconnection

**Errors/Issues:**
- [List any errors or issues encountered]

**Logs:**
[Attach relevant log excerpts]

**Recommendations:**
[Any suggestions for improvement]
```

---

## 🆘 Troubleshooting

### Gateway not running
**Error:** `Connection refused` or `Connection timed out`

**Solution:**
1. Start IBKR Gateway
2. Ensure it's in paper mode
3. Verify port 4002 is open
4. Check firewall settings

### Connection drops
**Error:** Connection lost after a few seconds

**Solution:**
1. Check Gateway logs for errors
2. Verify account credentials
3. Check network stability
4. Ensure paper trading account is active

### Auto-reconnect fails
**Error:** Cannot reconnect after Gateway restart

**Solution:**
1. Check `max_reconnect_attempts` in config
2. Verify `reconnect_delay` is appropriate
3. Check for errors in client reconnection logic

---

## 📚 References

- IBKR API Docs: https://interactivebrokers.github.io/tws-api/
- Bot Config: `/Users/ziscross/.openclaw/workspace/quant-scalper/config/config.yaml`
- IBKR Client Code: `/Users/ziscross/.openclaw/workspace/quant-scalper/bot/ibkr/client.py`

---

**Once complete, report to Marcus and proceed to Task 5.2!**
