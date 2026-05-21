# Provision ISR — Work Done (2026-05-21)

**Branch:** `dev`
**Last commit:** 9c25583

---

## Phases Completed

### Phase 0 — API Understanding
- Auth method: HTTP Basic Auth (confirmed in provision_client.py, `httpx.BasicAuth`)
- Existing endpoints mapped: GetDeviceInfo, GetChannelList, GetDiskInfo, GetStreamCaps, GetSnapshot, GetMotionConfig, SetMotionConfig, GetAlarmStatus
- Subscription flow: SetSubscribe → GetPullMessages (long polling, not push webhook) — this is confirmed working pattern

### Phase 1 — Core Integration Loads in HA
- Config flow complete: manual entry + network discovery
- GetDeviceInfo → device entity with name, serial, MAC, firmware
- GetChannelList → channels stored in coordinator
- DataUpdateCoordinator added — polls every 30s, shared state across entities
- **Bug fixed:** switch.py called `_get_motion_config()` and `async_time_validate()` which didn't exist — caused AttributeError on load
- **Bug fixed:** `set_motion_enabled()` was broken (sent GET, ignored toggle) — rewrote as read-modify-write: GET config → modify switch → POST SetMotionConfig
- **Bug fixed:** `_request()` now raises `AuthenticationError` on 401 (was incorrectly raising ProvisionConnectionError)
- **Bug fixed:** `_execute()` had double-slash in endpoint (lstrip fix)

### Phase 2 — Camera Entities
- camera.py complete: main + sub stream per channel, RTSP URL, snapshot
- IPC and NVR both handled
- Device hierarchy: NVR channels as sub-devices via `via_device`

### Phase 3 — Motion Detection (Long Polling)
- ProvisionLongPolling: subscribe, poll GetPullMessages, renew every 5min, unsubscribe on stop
- binary_sensor: CoordinatorEntity, callbacks registered after entity add
- Motion state held in coordinator.motion_state dict
- Fallback polling removed — all motion state flows through coordinator

---

## Phases Skipped

- **Phase 3 webhook model**: AGENT_PLAN mentioned HA HTTP webhook as callback, but the existing long-polling model (GetPullMessages) is already working and well-tested. The webhook model would require reading the LongPolling PDF to implement correctly. Kept existing model.
- **Phase 4** (Smart Detection sensors) — needs API docs / real device to verify event types
- **Phase 5** (Analytics sensors) — needs real device
- **Phase 6** (Device health sensors) — endpoint names unverified without docs
- **Phase 7** (README) — skipped full README rewrite, Hikvision grep clean (only in README attribution text, not code)

---

## What Dave Should Test First

1. HA → HACS → Provision ISR → reload integration
2. Check HA logs — should see "Connected to Provision ISR [model] at [ip]:[port]"
3. HA → Devices & Services → Provision ISR → should show NVR device + channel sub-devices
4. Camera entity should stream via RTSP
5. Motion in front of camera → `binary_sensor.provision_isr_ch1_motion` should turn on
6. Motion Detection switch (switch.provision_isr_ch1_motion_detection) → toggle off/on

---

## Known Issues for Next Pass

- Long polling endpoint port 8080 assumed — verify against real device
- `GetMotionConfig/N` channel endpoint format unverified for NVR (may just be `GetMotionConfig` with channel param)
- SetMotionConfig POST response parsing not verified (returns True unconditionally)
- `support_api_long_polling` must be True in GetDeviceInfo response for long polling to start — if False, motion sensors show Unknown forever
