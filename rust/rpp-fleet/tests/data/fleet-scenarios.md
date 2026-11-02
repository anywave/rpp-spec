# Scripted fleet endpoint selection

The existing merged overlay policy chooses paths from these supplied readings.
Identity assignments and prior verification are fixtures; no radio, discovery or cryptography runs.

Fourteen core-derived rows; three fleet-boundary contract rows are not independent core parity.

| Scenario | Traffic | Status | Endpoint | Kind | URI | Failover order |
|---|---|---|---:|---|---|---|
| lan-up | data | OK | 1 | LAN | ipv4://192.0.2.10:9000/rpp | 1,2,3 |
| wifi-before-spike | data | OK | 2 | Wi-Fi | ipv4://192.0.2.20:9000/rpp | 2,1,3 |
| wifi-spike | data | OK | 1 | LAN | ipv4://192.0.2.10:9000/rpp | 1,3,2 |
| ble-control-only-data | data | NO_CHANNEL | - | - | - | - |
| ble-control-only-control | control | OK | 4 | BLE | bt://voice-device/control | 4 |
| ble-reviewed-data | data | OK | 4 | BLE | bt://voice-device/control | 4 |
| partition-data | data | NO_CHANNEL | - | - | - | - |
| partition-control | control | NO_CHANNEL | - | - | - | - |
| xiaozhi-websocket-lan-gateway | data | OK | 6 | WebSocketGateway | ws://voice-gateway.lan/xiaozhi | 6 |
| equal-score-tie | data | OK | 1 | LAN | ipv4://192.0.2.10:9000/rpp | 1,2 |
| invalid-latency-u64max-update | fleet-update | INVALID_READING | - | - | - | - |
| invalid-loss-ppm-update | fleet-update | INVALID_READING | - | - | - | - |
| control-replay | control | DENIED | - | - | - | - |
| clock-rollback | control | CLOCK_ROLLBACK | - | - | - | - |
| xiaozhi-ws-lost | data | NO_CHANNEL | - | - | - | - |
| xiaozhi-ws-lost-lan-fallback | data | OK | 1 | LAN | ipv4://192.0.2.10:9000/rpp | 1 |
| empty-endpoints-no-channel | data | NO_CHANNEL | - | - | - | - |
