# PARL Success Criteria

**Phase-Aware Routing Layer - Validation Metrics**

Version: RPPv0.9-beta
Date: 2026-01-04

---

## 1. Core Performance Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| **Routing Accuracy** | ≥ 95% | Tokens successfully delivered to intended destination |
| **End-to-End Latency** | < 2000ms | Maximum acceptable latency for token delivery |
| **Coherence Preservation** | ≥ 97% | Token coherence values preserved through routing |
| **Crypto Success Rate** | ≥ 99% | AEAD encrypt/decrypt operations succeed |
| **Emergence Accuracy** | ≥ 97% | Correct detection of emergence threshold conditions |

---

## 2. Field State Metrics

### 2.1 Saturation Thresholds

| Field | Saturation Threshold | Action |
|-------|---------------------|--------|
| Theta | 85% | Begin load balancing |
| Phi | 80% | Begin load balancing |
| Combined | 95% | Drop with logging |

### 2.2 Coherence Tiers

| Coherence Range | Routing Behavior |
|-----------------|------------------|
| ≥ 0.90 | Forward immediately (fast path) |
| 0.70 - 0.89 | Standard routing |
| 0.50 - 0.69 | Delay 100ms before forward |
| 0.30 - 0.49 | Probabilistic forward |
| < 0.30 | Reject/drop |

### 2.3 Emergence Conditions

| Parameter | Threshold | Description |
|-----------|-----------|-------------|
| Global emergence | 0.97 | System-wide coherence for emergence event |
| Local buffer | 20 tokens | Minimum tokens before emergence check |
| Cooldown | 5000ms | Minimum time between emergence triggers |

---

## 3. Network Performance

### 3.1 Connection Limits

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max connections | 50 | Per-node connection limit |
| Socket timeout | 30s | Connection timeout |
| Hop timeout | 2000ms | Single-hop timeout |
| Max hops | 10 | Maximum routing depth |
| Retry count | 3 | Failed transmission retries |

### 3.2 Latency Targets

| Percentile | Target |
|------------|--------|
| P50 | < 100ms |
| P90 | < 500ms |
| P99 | < 1500ms |
| Max | < 2000ms |

---

## 4. Security Requirements

### 4.1 Encryption

- **Algorithm**: ChaCha20-Poly1305 (primary) or AES-256-GCM (fallback)
- **Key rotation**: Every 24 hours
- **Authentication**: Required for all non-observe operations
- **Anonymous observe**: Disabled by default

### 4.2 Integrity

- **Field hash**: SHA-256 truncated to 16 characters
- **Packet authentication**: AEAD tag verification
- **Replay protection**: Timestamp + nonce validation

---

## 5. Test Scenarios

### 5.1 Basic Routing Test
- **Objective**: Verify token delivery between nodes
- **Pass criteria**: ≥ 95% delivery rate
- **Token count**: 100 minimum

### 5.2 Emergence Test
- **Objective**: Verify emergence detection accuracy
- **Pass criteria**: Emergence triggers at coherence ≥ 0.97
- **Method**: Gradually increase coherence, verify trigger point

### 5.3 Stress Test
- **Objective**: Verify performance under load
- **Pass criteria**: < 2000ms latency maintained
- **Duration**: 30 seconds continuous
- **Rate**: Maximum sustainable throughput

### 5.4 Saturation Test
- **Objective**: Verify field saturation handling
- **Pass criteria**: Graceful degradation at saturation
- **Method**: Flood single node, verify drop policy

### 5.5 Crypto Roundtrip Test
- **Objective**: Verify encryption layer
- **Pass criteria**: ≥ 99% successful encrypt/decrypt
- **Token count**: 100 minimum

### 5.6 Multi-Hop Test
- **Objective**: Verify multi-hop routing
- **Pass criteria**: Tokens traverse expected path
- **Hops**: 3-10 per token

---

## 6. Validation Commands

```bash
# Run all scenarios
python simulate_mesh.py --nodes 5 --tokens 100

# Specific scenario
python simulate_mesh.py --scenario emergence_test --verbose

# Stress test with JSON output
python simulate_mesh.py --scenario stress_test --duration 60 --json

# Large mesh test
python simulate_mesh.py --nodes 20 --tokens 1000
```

---

## 7. Result Interpretation

### 7.1 PASS Conditions
All of the following must be true:
- Routing accuracy ≥ 95%
- Average latency < 2000ms
- Coherence preservation ≥ 97%
- Crypto success rate ≥ 99%

### 7.2 WARN Conditions
- Routing accuracy 90-95%
- Average latency 1500-2000ms
- Any crypto failures

### 7.3 FAIL Conditions
- Routing accuracy < 90%
- Average latency > 2000ms
- Coherence preservation < 95%
- Crypto success rate < 95%

---

## 8. Ra-Canonical Address Validation

Token address components must map correctly:

| Component | Range | Ra-Canonical Mapping |
|-----------|-------|---------------------|
| Theta (0-1) | 5 bits | Repitan 1-27 |
| Phi (0-1) | 3 bits | RAC 1-6 |
| Coherence (0-1) | 3 bits | Omega tier 0-4 |
| Entropy delta (-1 to 1) | 8 bits | Radius 0-255 |

### Omega Tier Mapping

| Coherence | Omega Tier | Color |
|-----------|------------|-------|
| ≥ 0.90 | 2 | GREEN (stable) |
| 0.70 - 0.89 | 1 | OMEGA_MAJOR |
| 0.50 - 0.69 | 3 | OMEGA_MINOR |
| 0.30 - 0.49 | 4 | BLUE |
| < 0.30 | 0 | RED (alert) |

---

## 9. Hardware Compatibility

Target platforms must achieve:

| Platform | Min Throughput | Max Latency |
|----------|----------------|-------------|
| ESP32-S3 | 10 tokens/sec | 500ms |
| OpenWRT | 100 tokens/sec | 200ms |
| Adafruit Feather | 5 tokens/sec | 1000ms |
| Helium (LoRaWAN) | 1 token/sec | 5000ms |
| Desktop (Python) | 1000 tokens/sec | 50ms |

---

*Generated for PARL RPPv0.9-beta implementation validation*
