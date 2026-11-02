# UDP underlay (experimental, std only)

This adapter sends real UDP datagrams. It uses numeric `SocketAddr` values and
opens sockets only after validating both bind and peer addresses and the kind.
Allowed: 127.0.0.0/8, ::1, 100.64.0.0/10 and fd7a:115c:a1e0::/48. Wildcard,
plain LAN, public and IPv4-mapped IPv6 addresses are refused. Only configured
Lan, Wifi and Internet kinds are accepted; the kind does not identify a radio.
The range test is a **heuristic, not proof of encryption** or Tailscale presence.
D7 requires externally managed Tailscale for IP underlays; this crate creates no
tunnel, keys, discovery, relay, identity, consent or trust. Plain-LAN UDP needs
RADIX and is not implemented. Loopback tests do not prove encrypted transport.

## Informative adapter-local envelope (not an RPP specification)

Every datagram starts with version byte 1 and class byte:

| Class | Value | Body |
|---|---:|---|
| Probe | 1 | Exactly one big-endian u64 counter |
| Probe reply | 2 | The same counter; total size stays 10 bytes |
| Control | 3 | Existing complete 112-byte rpp-control envelope |
| Data | 4 | Opaque caller-classified application bytes |

The maximum WHOLE datagram is 1200 bytes, so data has at most 1198 bytes.
IPv6's 1280-byte minimum minus 40 IPv6 and 8 UDP bytes leaves 1232; 1200 leaves
32 bytes of margin. This conservative local cap does not establish path MTU.
Data sends once: no stream or retransmission. Core failover still permits retry
only before the first token. `dispatch` rejects data on the control path first.

Unconnected `recv_from` captures a full standard UDP datagram in a bounded 64 KiB
buffer, then drops/counts any source other than the exact configured IP AND port
before examining prefix, length or body. Oversized/unknown frames are dropped.
Incoming control reaches `Received::Control` only through `rpp_control::decode`
with the caller's recipient and verifier. Invalid/forged frames are counted and
dropped. Repeated valid sequence numbers can decode: freshness remains host policy.

## Measurements and bounded echo

`read(tick)` sends one probe with a checked, per-adapter counter (no RNG). RTT is
elapsed monotonic host time, floored to milliseconds, not one-way latency. Zero
means less than one millisecond at this resolution, not zero network delay.
The last 32 completed probe attempts determine loss in ppm; before 32 attempts,
the denominator is the number observed. No observations means unavailable and
loss 1,000,000. `available` means the latest probe succeeded. Observation tick
comes from the caller and is not a clock synchronization or freshness grant.

Jitter applies RFC 3550's integer estimator to successive RTT transit samples:
Q4 state J += abs(RTT - previous_RTT) - ((J + 8) >> 4); report J >> 4 ms.
A loss clears RTT/jitter and its previous RTT; the next success starts a new series.
This is RTT variation, not an RTP one-way jitter measurement. u128 arithmetic
preserves fractional state and avoids unsigned delta overflow.

Timeout, ConnectionReset/Refused/Aborted and HostUnreachable/NetworkUnreachable/
NetworkDown are loss notices, not completion of a pending probe. Idle receive
ignores them; ConnectionReset increments its named counter. Other errors propagate.
Pending reads continue across notices and foreign/malformed packets until a reply
or absolute deadline (nonzero, at most 250 ms); only an unanswered probe is lost.
The configured timeout is restored. Scheduling can extend wall time. Four opaque
application packets can wait for `receive`; overflow is counted. Probes stay internal.

Echo is inspired by BFD echo [RFC 5880](https://www.rfc-editor.org/rfc/rfc5880)
and [RFC 5881](https://www.rfc-editor.org/rfc/rfc5881), not BFD wire compatibility.
Only exact-peer, 10-byte probes get a same-size reply. Nonces increase within an
active episode; one second since the last accepted echo attempt resets nonce
state, allowing a same-address prober to restart. Refused probes do not refresh
that timer; the independent 32-reply/second limit remains.
There is no amplification, outside-source reflection or automatic consent.
[Jitter reference: RFC 3550 §6.4.1 / A.8](https://www.rfc-editor.org/rfc/rfc3550#appendix-A.8).

## Run

`cargo +1.85.1 run -p rpp-link-udp --example loopback_pair` runs two real loopback
pairs, prints readings, closes the currently selected peer, then uses measured
loss to make the existing fleet resolver select the survivor. Policy verification
flags, membership and consent are explicit fixtures; no tunnel is measured.
The same flow test has one total two-second bound and no latency threshold.

Default `fleet-demo` uses only existing workspace path crates; no external
dependency is added. Without defaults the UDP crate still needs std. Both
riscv32 workspace builds therefore use `--exclude rpp-link-udp`; the std-only
adapter is not empty no_std code and is not ESP32 firmware.

Receive is currently adapter-local. A shared borrowed-buffer receive trait,
closed inbound enum, error/buffer ownership and verifier placement are a proposal
for TR/PL to decide, not a change to the existing public adapter traits.

## Loopback TCP fallback (CX-027)

`FallbackConfig::new(udp_config, tcp_peer)` validates every numeric address as
loopback before opening sockets. `FallbackAdapter::connect(config, tick)` probes
UDP once, then connects and probes TCP only if UDP is unavailable. Each timeout
is nonzero and at most 250 ms. Selection precedes all application/control sends;
the selected transport is permanent. No failed or ambiguous application write
is replayed, and no connection is automatically reopened. A successful write
means the local kernel accepted bytes, not that the peer delivered the frame.

`TcpAdapter::connect` validates before connect. `from_stream` checks both actual
endpoints of a caller-accepted stream before frame I/O. Lan/Wifi/Internet labels
remain metadata. There is no TLS, QUIC, encryption, peer authentication, tunnel,
key exchange, consent or admission. TCP is currently refused even on tailnet.

The two-byte big-endian length excludes itself and includes the unchanged UDP
version/class envelope (2..=1200 bytes); data remains at most 1198 bytes. Probe
and reply envelopes remain exactly ten bytes, with checked increasing u64
nonces and exact-current reply matching. Echo quiet reset, 32-reply/second cap,
four pending application frames and the existing 32-attempt measurement model
are retained. Control passes the same caller recipient/verifier codec; replay
policy remains outside the adapter. `framed` also provides pure encode/decode.

One absolute monotonic deadline covers all prefix/body chunks of each frame,
including Interrupted calls and final completion. Every frame I/O failure closes
the stream, including idle timeout and clean EOF; malformed lengths/envelopes
close it too. There is no resynchronization. TCP kernel retransmission and head
of line blocking hide packet losses: readings describe application probe RTT
and success, not raw IP loss. Unlike UDP's unavailable reading after probe
loss, TCP frame failures propagate an error and leave the session closed.

Tests use only prebound loopback peers, including an open-but-silent UDP socket
and a ready TCP listener; fallback must complete within two seconds. Blocking
workers receive explicit wake connections and are joined. These are host tests,
not firewall, internet, radio, Windows or board measurements.

Literal proptest 1.6.0 lives only in detached `tools/tcp_scaffold`, with fixed
ChaCha seed, 256 cases, bounded shrinking and no persistence. Production Cargo
metadata/lock remain registry-free. CI fetches its locked test graph once and
runs properties offline; the checker/test runner never installs dependencies.
Run `cargo +1.85.1 test --manifest-path tools/tcp_scaffold/Cargo.toml --offline --locked`
from the repository root after the locked dependencies are cached.
