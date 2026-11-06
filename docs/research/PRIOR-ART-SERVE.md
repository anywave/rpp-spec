# PRIOR-ART-SERVE

## The five pieces that save the most time

These are proposals for original LatticeWorks Rust, not permission to copy,
translate, vendor, ship or run a reference implementation. S means one bounded
adapter/check; M means several bounded cards; L means a new runtime/protocol plus
hardware trials. These are scope estimates, not elapsed-time promises.

| Rank | Piece / verdict / size | Behaviour and interface to design ourselves | LatticeWorks fit / reason / sources studied |
|---|---|---|---|
| 1 | **Answer-bound token audit — REBUILD IN RUST, M** | An executor reports its actual token usage, requested and served model, completion state and separate processing durations. Our auditor joins that to the authenticated worker and exact answer, verifies one terminal receipt and reports absent fields as missing. Input: owned execution observations and existing signed stage rows; output: one answer audit plus its evidence gaps. | Extend `lw-gateway` meter/receipt and auditor join, not a second meter. The useful references separate prompt, cached prompt and generation counts; their public APIs do not supply our complete signed evidence. `CPP:tools/server/server-task.cpp:357-363`; `OL:llm/llama_server.go:1639-1652,1868-1878`; `LA:core/backend/llm.go:36-42,265-272`; existing `LW:crates/lw-gateway/src/lend.rs:3286-3297`. |
| 2 | **Explainable memory admission — REBUILD IN RUST, M** | Given local model metadata, context/batch/cache settings and a fresh per-device budget, report host/device requirements, uncertainty and an admit/wait reason. Reserve against concurrent admitted jobs, not just a prior availability reading. Unsupported architecture or stale readings refuse. | `lw-gateway` room-check plus task capability row; reuse our existing GGUF validation. Avoid discovering an OOM only after a person lends the machine. `P:file_estimate__llamacpp.go:108-164,168-205`; `G:gpustack/policies/candidate_selectors/gguf_resource_fit_selector.py:251-279`; `EX:src/exo/master/placement.py:81-112`. No port of their estimator formulas. |
| 3 | **Leased capability offers and warm-worker selection — REBUILD IN RUST, M** | A paired machine declares which owned executors/models it can run, available budget, current reservations, admission state and offer expiry. Filter consent, compatibility and freshness before ranking eligible whole-model workers; prefer a ready resident model without evicting the owner's model. Input: signed offers plus job requirements; output: a bounded selected offer/lease or wait. | Existing LW lend worker and the single fleet queue; optional Echo adapter, never a new mandatory worker service. `G:gpustack/policies/worker_filters/status_filter.py:18-50`; `LA:core/services/nodes/router.go:359-385`; `T:codex/PRODUCT_DESIGN_MAP.md:198-200`. |
| 4 | **Explicit interrupted-answer handling — REBUILD IN RUST, M** | Before any output is committed, an eligible retry may become a new attempt after proving the old attempt cannot continue. Once answer output is committed, return incomplete and retain its meter/receipt state; never splice another machine's answer into it. Input: attempt state, link health and cancellation; output: one terminal outcome per attempt. | Extend LW's existing breaker, lend Stop and queue reconciliation. Recovery is not transparent continuation of unknown remote KV state. `LA:core/services/failover/manager.go:760-789`; `EX:src/exo/api/tests/test_stream_error_codes.py:58-93`; `G:gpustack/routes/openai.py:482-542`; `T:codex/PRODUCT_DESIGN_MAP.md:196-200`. |
| 5 | **Qualified Windows capacity readings — REBUILD IN RUST, M** | Read adapter memory budgets/usage, engine activity and supported clock/temperature sensors with source, age, units and missing state. Keep dedicated and shared memory separate. Use observed throughput and throttling context, not a fixed clock-to-capacity multiplier. Input: read-only OS/driver observations; output: bounded local snapshots for admission and Hypervisor. | Rust replacements behind `apps/console/src/hyper*.mjs`; no LHM DLL, vendor SDK or tuning control. `HW:LibreHardwareMonitorLib/Hardware/D3DDisplayDevice.cs:64-139`; `HW:LibreHardwareMonitorLib/Hardware/Gpu/IntelIntegratedGpu.cs:44-79`; existing `LW:apps/console/src/hyper-gpu.mjs:26-59`. |

**Rebuild first: the Windows Rust terminal-answer auditor for one existing lend
call.** Join engine usage to the pinned solver and answer, then verify the one
terminal receipt and its existing stage chain on the asker. This is the core
RADIX named, and adds useful evidence before introducing sharding, another VPN
or a replacement fleet orchestrator. Inventory the current auditor/join work
before selecting the missing increment: the current map places schema/join and
the live loop on the delivery path (`T:codex/PRODUCT_DESIGN_MAP.md:15-21`).

The first slice uses synthetic engine observations for refusal tests, then needs
an approved real executor for its Windows acceptance run. It does not add any
reference server behind an adapter and call that our Rust. If a proposed engine
depends on one of these runtimes or ships NVIDIA files, it fails this card's
rule. Engine approval/implementation is a separate prerequisite, not satisfied
by a fake count or by successful compilation. Nothing is implemented here.

## Method, pins and licences

TR's PRIOR-ART-SERVE card, 2026-11-06, is the authority for this research.
Network access succeeded. Sources were read from immutable GitHub archives in
scratch, not installed, imported, built or run. Extraction retained selected
UTF-8 source/config/document files up to 1 MiB each; binaries, links and larger
files were omitted. No models, accounts, inference services or GPU drivers were
obtained. No target test result or live Windows/GPU performance is claimed.
All descriptions below are behavioural analysis, not pasted source or a
line-by-line translation. Named API fields are interoperability observations.

`ALIAS:path:line` refers to the immutable source tree below. All proposed
interfaces/algorithms in this report are DESIGN, not changes to an existing
contract. No licence here authorizes copying under RADIX's narrower instruction.
Root licences are recorded as source facts, not a transitive licence audit.

| Alias | Project / exact pin | Licence source |
|---|---|---|
| G | [gpustack/gpustack](https://github.com/gpustack/gpustack/tree/f9778ba5be4d1ff7373afbf5b9a1ea40d9cc0a66) `f9778ba5be4d1ff7373afbf5b9a1ea40d9cc0a66` | Apache-2.0 (`G:LICENSE:1-5`) |
| P | [gpustack/gguf-parser-go](https://github.com/gpustack/gguf-parser-go/tree/bfbadae51bbb0a78911c0bfa29ed642676a422eb) `bfbadae51bbb0a78911c0bfa29ed642676a422eb` | MIT (`P:LICENSE:1-5`) |
| LA | [mudler/LocalAI](https://github.com/mudler/LocalAI/tree/aec135eed3fcb6112bc4967e98350c885c15e918) `aec135eed3fcb6112bc4967e98350c885c15e918` | MIT (`LA:LICENSE:1-5`) |
| EV | [mudler/edgevpn](https://github.com/mudler/edgevpn/tree/fa89190c1c0c0ab20a82a7de5159e08effbd359a) `fa89190c1c0c0ab20a82a7de5159e08effbd359a` | Apache-2.0 root; mixed API headers (`EV:LICENSE:1-5`) |
| EX | [exo-explore/exo](https://github.com/exo-explore/exo/tree/1d72c2a7154929d87f20ba11829601c6c7a937ef) `1d72c2a7154929d87f20ba11829601c6c7a937ef` | Apache-2.0 (`EX:LICENSE:1-5`) |
| CPP | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/tree/6c01da6278ab6c69ed67d9124806b50d2b299ba7) `6c01da6278ab6c69ed67d9124806b50d2b299ba7` | MIT (`CPP:LICENSE:1-5`) |
| DL | [b4rtaz/distributed-llama](https://github.com/b4rtaz/distributed-llama/tree/9eb968d18ff48940f967335cad4a80fd93082ad7) `9eb968d18ff48940f967335cad4a80fd93082ad7` | MIT (`DL:LICENSE:1-5`) |
| OL | [ollama/ollama](https://github.com/ollama/ollama/tree/6362e0a30887bdd4f69e07a94e8a513383576204) `6362e0a30887bdd4f69e07a94e8a513383576204` | MIT (`OL:LICENSE:1-5`) |
| HW | [LibreHardwareMonitor/LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/tree/2808d80564b6761e1b01f42fabfd966ed695fcbc) `2808d80564b6761e1b01f42fabfd966ed695fcbc` | MPL-2.0; third-party notices (`HW:LICENSE:1-5`) |
| HS | [juanfont/headscale](https://github.com/juanfont/headscale/tree/48416ce0894ef7bef0ef9c064609b4aa76a0d9b6) `48416ce0894ef7bef0ef9c064609b4aa76a0d9b6` | BSD-3-Clause (`HS:LICENSE:1-5`) |
| NB | [slackhq/nebula](https://github.com/slackhq/nebula/tree/fb4ef139cbb4af67d142c72083fb735f56460e50) `fb4ef139cbb4af67d142c72083fb735f56460e50` | MIT (`NB:LICENSE:1-5`) |
| IR | [n0-computer/iroh](https://github.com/n0-computer/iroh/tree/a5e39c44d3d6dfaaff30b7292126e06ea0ab7a21) `a5e39c44d3d6dfaaff30b7292126e06ea0ab7a21` | MIT OR Apache-2.0 (`IR:LICENSE-APACHE:1-5`) |
| T | [anywave/trellis-channel](https://github.com/anywave/trellis-channel/tree/092bb1b07fe4a801c7e0a3844b92be57745a2a48) `092bb1b07fe4a801c7e0a3844b92be57745a2a48` | Internal evidence/map only |
| LW | Existing anywave/latticeworks snapshot `13a8dba2f4ba610f6225c91f47ca8d4a432dfa71` | Mapping baseline only; not current lane validation |

LocalAI main had advanced to `441f5e1e534b79638e16bf4a438f7a131eb3470c` when
queried. The study uses TR's `aec135ee` commit, resolved to its full SHA, not that
new head. EdgeVPN was an additional named reference without a TR pin: its
observed head is separately pinned above; LocalAI instead names EdgeVPN v0.34.0
(`LA:go.mod:46`). The independent EdgeVPN review is not a transitive audit of
that release. Iroh's manifest is **MIT OR Apache-2.0**, version
**1.4.1** (`IR:iroh/Cargo.toml:1-7`), more precise than the card's Apache label.
EdgeVPN's root is Apache-2.0 but API files carry GPL-2.0-or-later headers
(`EV:api/api.go:1-14`); LHM also has third-party notices
(`HW:THIRD-PARTY-NOTICES.txt:1-35`). Nothing from either is copied.

T is current pulled trellis-channel main. LW is an existing read-only snapshot,
not a claim to be current main: current lane fixes must be read before coding.
The map records Hypervisor fixes in flight, GPU sharing following the lending
switch, no GitHub dependency in the final product, and a single existing LW
worker/queue road (`T:codex/PRODUCT_DESIGN_MAP.md:63-86,196-200`).
No changes to LW, Mobius, their lanes or any upstream repo were made. No new
agent was spawned for this card. All source observations and the report were
checked by the main thread; no separate independent review is claimed.

## Serving mechanisms: discovery, placement, leaving and API

None of the inspected joins below implements LatticeWorks' full matching-code,
Accept, lending-switch, n2HO and fair-share contract. Authentication to a
cluster is not consent to run a particular job. Preserve the LW checks even
when a transport already authenticates a peer.

| Project | (a) Discovery / joining / auth | (b) Placement / estimate / split | (c) Health, failover and leaving mid-answer | (d) Served API / observed data formats |
|---|---|---|---|---|
| GPUStack | Configured server registration exchanges a registration credential for a worker credential; admin/cluster rules gate registration. Not a bilateral matching-code/Accept exchange (`G:gpustack/worker/worker_manager.py:88-147`; `G:gpustack/routes/workers.py:725-741`). | READY/bound-worker filter; resource-fit candidates, allocatable per-GPU VRAM and scoring/locality policies. GGUF selector has CPU/partial/full/distributed offload cases; it does not make heterogeneous GPU memory one shared device (`G:gpustack/policies/worker_filters/status_filter.py:18-50`; `G:gpustack/policies/candidate_selectors/gguf_resource_fit_selector.py:62-70,251-279`; `G:gpustack/scheduler/scheduler.py:1218-1242`; `G:gpustack/policies/scorers/model_file_locality_scorer.py:62-94`). | Controllers mark impacted instances unreachable. The inspected direct streaming proxy emits an error when its selected worker connection fails; it does not restore a partial decode on another worker. Gateway/other backend strategies must not be inferred from that one path (`G:gpustack/server/controllers.py:5490-5510,5594-5642`; `G:gpustack/routes/openai.py:482-542`). | OpenAI-style proxy plus management/usage APIs; backend instance/rank endpoint chosen before forwarding. Request/response JSON and SSE, management worker/model records (`G:gpustack/routes/openai.py:432-479`; `G:gpustack/routes/usage.py:869-880,1495-1512`). |
| gguf-parser-go | Not a machine pool, server or join mechanism. Local file parser plus optional remote readers (`P:file.go:258-309`; `P:file_from_remote.go:16-31`). | GGUF metadata/tensors and host/device weight, KV and compute estimates parameterized by context/batch/offload/cache options. Estimates are architecture/runtime-specific predictions, not live VRAM measurements (`P:file_estimate__llamacpp.go:108-205`). | File/read/estimate errors, not inference failover. No machine can leave an answer because it does not execute one. | Go library and CLI; GGUF input and structured estimate fields. No serving endpoint or completion stream (`P:file.go:258-309`; `P:cmd/gguf-parser/main.go:1-45`). |
| LocalAI | Distinguish three modes: shared-token EdgeVPN P2P discovery/exposed workers; federated HTTP services; distributed worker registry using PostgreSQL/NATS. Registry auth can be required, but configuration explicitly retains a permissive historical default and optional auto-approval. None is LW pairing (`LA:core/application/p2p.go:41-104`; `LA:core/cli/federated.go:11-16`; `LA:core/config/distributed_config.go:13-36`). | SmartRouter selects workers and tracks staging/loading/reserved replica state; it adjusts load options to the selected node, not the frontend GPU. Other workers can expose llama.cpp RPC or MLX distributed stages; these are distinct from whole-model routing (`LA:core/services/nodes/router.go:315-385`; `LA:core/cli/worker/worker_p2p.go:40-109`). | Per-node/model health and stale-worker handling; failover manager retries classified failures only before its output-commit callback. After commit it reports failure without retry. This is not proof every endpoint invokes that callback correctly, nor KV-state migration (`LA:core/services/nodes/health.go:20-75`; `LA:core/services/failover/manager.go:760-789`). | OpenAI-style JSON/SSE, backend gRPC and distributed control messages; optional response node-attribution header. Requested/served model routing can differ (`LA:core/http/routes/openai.go:21-34,68-77`; `LA:core/schema/openai.go:25-35`). |
| exo | IPv6 multicast hello/discovery with namespace, wire and build compatibility, followed by Zenoh TCP links. Inspected discovery/session configuration does not establish a human-approved pin or signed worker authorization; compatible namespace is not a secret authorization (`EX:rust/networking/src/discovery.rs:71-105,216-247`; `EX:rust/networking/src/lib.rs:24-45,48-95`). | Topology cycles, memory-filtered node sets and model-dependent layer/tensor placement. Master rechecks simultaneous placements against committed instance state. Memory-weighted layer allocation is an idea, not a bandwidth or latency guarantee (`EX:src/exo/master/placement.py:75-112`; `EX:src/exo/master/placement_utils.py:21-73`). | Membership state and deployment reconciliation remove broken instances and place replacements. A device leaving can terminate an active generation; tests expect an explicit `device_left` error, not a continued answer. Client disconnect also produces cancellation/finished cleanup (`EX:src/exo/master/main.py:830-894`; `EX:src/exo/api/tests/test_stream_error_codes.py:58-93`; `EX:src/exo/api/tests/test_task_finished_on_disconnect.py:81-100`). | OpenAI chat/models plus Responses/Claude/Ollama adapters and internal typed token/task events. Terminal/error chunks are distinct (`EX:src/exo/api/main.py:569-603`; `EX:src/exo/shared/types/chunks.py:19-48`). |
| llama.cpp | Explicit model/device/RPC endpoint configuration. HTTP bearer API-key validation is optional; health endpoints are public. RPC capability negotiation is not authenticated pairing: its own documentation calls the service insecure/fragile (`CPP:tools/server/server-http.cpp:261-290`; `CPP:tools/server/server.cpp:171-183`; `CPP:tools/rpc/README.md:1-8`). | Local slots/batching and backend device offload; remote RPC exposes operations on device buffers/graphs rather than a ready-made fleet job. CPU is exposed if no accelerator exists (`CPP:tools/rpc/README.md:8-43`; `CPP:ggml/src/ggml-rpc/ggml-rpc.cpp:377-432`). | RPC connection failure reaches abort/assert/error paths, not durable model-stage recovery. A healthy HTTP listener says little about every remote shard. No reviewed transparent mid-answer migration; close/cancel is an incomplete attempt (`CPP:ggml/src/ggml-rpc/ggml-rpc.cpp:641-697`; `CPP:tools/server/server.cpp:658-665`). | Native completion/tokenize/slot/health and OpenAI-style chat/models/Responses routes; JSON/SSE. RPC is a separate binary command/data channel (`CPP:tools/server/server.cpp:171-214`; `CPP:ggml/src/ggml-rpc/ggml-rpc.cpp:377-432`). |
| distributed-llama | Configured root and worker socket addresses, root distributes model/config/state. Inspected accept/transfer paths have no corresponding bilateral authentication/Accept gate; use as trusted-LAN reference only (`DL:src/nn/nn-network.cpp:144-168,298-329`; `DL:src/dllama-api.cpp:613-635`). | Tensor/attention/KV slices across a fixed participant set, root also computes. Model-specific divisibility/KV-head and quantization constraints; not dynamic capacity-weighted whole-job scheduling (`DL:src/llm.cpp:165-176`; `DL:src/app.cpp:233-241`). | Socket-transfer errors break worker execution; API outer loop can restart after failure. This reinitialization is not recovery of the same partial answer, and the HTTP path may already have emitted content (`DL:src/app.cpp:347-362`; `DL:src/dllama-api.cpp:627-635,679-690`). | OpenAI-shaped chat completion/models over a simple HTTP server, custom converted weights/tokenizer and raw worker packets. Not GGUF serving merely because the model name is similar (`DL:src/dllama-api.cpp:613-623,647-660`; `DL:src/nn/nn-network.cpp:298-329`). |
| Ollama | A local configured HTTP server, loopback by default; host/origin controls are not peer enrollment. Cloud model routing/sign-in is a different feature, not a self-hosted fleet membership layer (`OL:envconfig/config.go:20-31`; `OL:server/routes.go:2312-2340,2425-2441`). | Local runner queue, loaded-model reference counts, memory prediction and expiry/unload choices. Useful residency accounting, but its eviction behaviour must not displace an owner's running model in LW (`OL:server/sched.go:580-615,1706-1735`). | Request context cancels completion; runner failures surface as errors and later work can load another runner. Inspected local scheduler does not make worker-loss recovery a mesh feature or preserve a distributed partial answer (`OL:server/routes.go:3333-3355`; `OL:server/sched.go:615-623`). | Native generate/chat/embed/ps and OpenAI-compatible completions/chat/models/Responses; native metrics include prompt, cached prompt, output and duration fields (`OL:server/routes.go:2425-2441`; `OL:api/types.go:562-570`). |

### What the authored tests establish, before any execution

| Reference | Inspected test evidence / limit |
|---|---|
| GPUStack | Partial-usage tests assert the byte/chunk fallback and its completed-versus-interrupted distinction. This supports the described estimator behaviour, not its accuracy for arbitrary models (`G:tests/server/test_metrics_collector.py:312-340`). |
| gguf-parser-go | Some context-size tests fetch Hugging Face metadata and only print estimates; they are not numerical accuracy assertions. Later architecture-specific tests contain additional checks, but an estimator still needs our own measured-peak validation (`P:file_estimate__llamacpp_test.go:70-97,328-391`). |
| LocalAI | Fake failure/commit tests expect only one target after commit; reservation tests explicitly check no-inference cleanup and double-release. These are bounded lifecycle tests, not live heterogeneous serving or proof every endpoint uses the manager correctly (`LA:core/services/failover/manager_test.go:302-312`; `LA:core/services/nodes/router_reservation_test.go:50-87`). |
| exo | Synthetic token/error streams test `device_left`; cancelled API streams must send cancellation/finished cleanup. That is stronger than a README claim but does not demonstrate a live peer-loss run on MLX (`EX:src/exo/api/tests/test_stream_error_codes.py:58-93`; `EX:src/exo/api/tests/test_task_finished_on_disconnect.py:81-100`). |
| llama.cpp | Server test cases assert actual response usage and cache-detail fields with an engine test fixture; no such fixture was run in this research (`CPP:tools/server/tests/unit/test_chat_completion.py:35-73`). |
| distributed-llama | CPU/Vulkan arithmetic test targets exist; Vulkan checks compare results with tolerances. They do not demonstrate authenticated enrollment, signed answer evidence or recovery after a worker leaves (`DL:Makefile:60-89`; `DL:src/nn/nn-vulkan-test.cpp:13-30,976-987`). |
| Ollama | Fake backend HTTP tests assert prompt count including cache, cached count and output count. They test conversion, not independent physical execution or a multi-machine pool (`OL:llm/llama_server_test.go:229-259`). |
| Headscale / Nebula / iroh | Auth-state assertions, tunnel liveness tests and relay/link-outage tests respectively exist; none is an AI-serving test (`HS:hscontrol/auth_test.go:106-113`; `NB:connection_manager_test.go:92-112`; `IR:iroh/tests/patchbay/relay.rs:190-257`). |
| EdgeVPN / LHM | EdgeVPN has alive-node ledger tests, not work receipts. LHM has a Windows build workflow; neither establishes token accounting or arbitrary sensor availability on our boxes (`EV:pkg/services/alive_test.go:43-68`; `HW:.github/workflows/master.yml:9-23`). |

All these tests were **read, not run**. No pass count, performance ranking or
native Windows proof is inferred from their existence.

### The transport and sensor references are not serving engines

| Project | (a) Join / trust; (b) placement; (c) leaving; (d) API |
|---|---|
| EdgeVPN | Shared connection token/room data, optional mDNS/DHT, libp2p hole-punch/relay options and service announcements. Ledger health expires availability; link reconnection does not replay an AI request safely. It has VPN/service/ledger management APIs, no model scheduler or token contract (`EV:pkg/config/config.go:114-141,300-321,350-364`; `EV:pkg/services/alive.go:29-90`; `EV:api/api.go:217-230,422-462`). LocalAI's use of it is separately documented at the LA pin. |
| Headscale | Control plane for Tailscale clients: pre-auth keys or interactive/OIDC enrollment, node maps, admin APIs and optional DERP/STUN. No model placement or answer API. Disconnect events/route probes update network reachability, not executor health; an interrupted application still needs its own terminal outcome (`HS:hscontrol/auth.go:148-177`; `HS:hscontrol/app.go:348-364,530-565`; `HS:hscontrol/poll.go:175-257`; `HS:docs/ref/derp.md:3-29`). |
| Nebula | CA-signed certificate enrollment and encrypted overlay handshakes, lighthouses/static endpoints, punching and optional relays. Tunnel liveness can close/recreate a path; it cannot restore an inference context. VPN packets, optional identity HTTP socket and stats, no model placement or token API (`NB:handshake_manager.go:1270-1274`; `NB:cert/ca_pool.go:186-228`; `NB:connection_manager.go:346-435`; `NB:examples/config.yml:260-306`). |
| iroh | Endpoint-key authenticated QUIC, ALPN and address lookup/relay policy. Paths may change without an application changing its peer; complete endpoint loss is still an application failure. No model placement, token count or serving API; bidirectional streams/datagrams carry our protocol. Peer key authentication does not give human consent (`IR:iroh/src/endpoint/connection.rs:375-410,569-572`; `IR:iroh/src/endpoint.rs:534-545,827-843`; `IR:iroh/tests/patchbay/relay.rs:190-257`). |
| LibreHardwareMonitor | Local hardware enumeration/readings, optionally a user-enabled HTTP view; no peer discovery, workload scheduler, answer failover or inference API. A missing/failed sensor is unavailable data, not an idle GPU. Device/driver identity is not a signed executor identity (`HW:LibreHardwareMonitorLib/Hardware/Computer.cs:172-188`; `HW:LibreHardwareMonitorLib/Hardware/D3DDisplayDevice.cs:64-139`; `HW:LibreHardwareMonitor.Windows.Forms/Utilities/HttpServer.cs:38-55`; `HW:LibreHardwareMonitor.Windows.Forms/UI/MainForm.cs:332-340`). |

## Windows, non-NVIDIA paths and outside services

"Present" means a code/build/documented path was inspected, not that it ran here.
An import path containing `github.com` is not by itself a runtime connection;
download/update/control calls are. Conversely a local inference path does not
make the desktop updater or model gallery offline. No complete outbound-traffic
census or blocked-network runtime test was executed for any reference.

| Project | (e) Windows / CPU / Vulkan / AMD / Intel | (f) Outside dependencies and off controls |
|---|---|---|
| GPUStack | Current worker requirement is Linux, with WSL2 suggested for Windows; Docker Desktop support for the server is not native worker support. AMD ROCm is documented. Do not assume the current container/backend set supplies native Windows Vulkan or Intel serving (`G:docs/installation/installation.md:7-12`; `G:docs/installation/requirements.md:78-88`). | Tool manager probes GitHub/alternate storage to fetch dependencies; update checker contacts its update service. Download base URL, pre-staged tools/images/local models and update-disable settings are the offline directions, not proof every deployment is offline (`G:gpustack/worker/tools_manager.py:72-112`; `G:gpustack/config/config.py:166-191,255-258`; `G:gpustack/server/update_check.py:17-60`; `G:docs/installation/air-gapped.md:1-35`). |
| gguf-parser-go | Pure parsing/estimate library has no GPU dependency; platform/driver feasibility belongs to the executor, not its estimate. No native Windows execution performed (`P:file.go:258-309`; `P:file_estimate__llamacpp.go:168-205`). | Local parsing needs no registry. Explicit Hugging Face/URL/Ollama readers do network I/O; select only local files for our estimator. Cache is not a guarantee of no network (`P:file_from_remote.go:16-104`; `P:file_from_distro.go:19-55`). |
| LocalAI | Inspected release/build directions target Linux/macOS; Windows uses WSL. llama backend has a Vulkan build option and CPU path; that is not native Windows validation or proof its default package excludes NVIDIA (`LA:docs/content/reference/binaries.md:8`; `LA:backend/cpp/llama-cpp/Makefile:35-51`). | Galleries point to an index service with GitHub/OCI mirrors; automatic gallery loading defaults on. Disable autoload/backend installation/upgrades and use pre-staged models/backends; explicitly configure P2P bootstrap/relays or disable DHT. Distributed mode additionally requires configured NATS/PostgreSQL, optionally object storage (`LA:core/config/runtime_settings_startup.go:16-21`; `LA:core/cli/run.go:97-128`; `LA:core/p2p/p2p.go:400-458`; `LA:core/config/distributed_config.go:13-23`). |
| exo | Pin's supported environment is macOS/Linux; MLX Metal, Linux CPU and optional CUDA paths. No native Windows/Vulkan/ROCm serving path established (`EX:pyproject.toml:47-68,174-178`; `EX:src/exo/master/placement.py:75-78`). | Hugging Face models/downloads normally; offline mode uses pre-staged models and refuses missing ones. Local multicast/TCP discovery is not WAN NAT traversal. Offline is an implemented branch, not evidence of zero external calls in every extension (`EX:src/exo/download/huggingface_utils.py:9-16`; `EX:src/exo/download/coordinator.py:163-185`; `EX:src/exo/main.py:587-590`). |
| llama.cpp | Windows Vulkan build handling and CPU fallback are present; AMD/Intel-compatible Vulkan hardware depends on its installed driver/features and model operations. NVIDIA-specific backends are separate build choices; no release bundle audited here (`CPP:ggml/src/ggml-vulkan/CMakeLists.txt:9-22,59-123`; `CPP:tools/rpc/README.md:35-43`). | Local model paths need no model host. Optional URL/Hugging Face download modes contact outside hosts; use local artifacts, no download flags, and enforce an egress test. Configured RPC peers/optional RDMA are network requirements when used (`CPP:common/download.cpp:71-90,262-278`; `CPP:tools/rpc/README.md:76-111`). No updater/telemetry absence claimed globally. |
| distributed-llama | Windows socket/Makefile support, CPU and opt-in experimental Vulkan. Backend tests exist, but no native/hardware run here (`DL:Makefile:18-37,60-89`; `DL:src/dllama-api.cpp:15-22`). | Direct worker addresses and already-local model/tokenizer are enough for the inspected engine road. Convenience launcher downloads from Hugging Face; omit that path and pre-stage files (`DL:launch.py:6-30`; `DL:src/dllama-api.cpp:647-660`). No relay/NAT service or automatic mid-decode repair was established. |
| Ollama | Windows test matrix explicitly includes ROCm and Vulkan; CPU is another local execution path. This proves a build/test configuration exists, not that an arbitrary AMD/Intel board works or that default installers contain no NVIDIA payload (`OL:.github/workflows/test.yaml:209-221`; `OL:server/sched.go:580-615`). | Registry pulls and cloud inference/search are optional surfaces. `OLLAMA_NO_CLOUD` disables cloud features, not all downloads or the desktop updater. The updater still checks its external endpoint with auto-download off; local headless serving and explicit pre-staging are a narrower offline path (`OL:server/images.go:1193-1286`; `OL:envconfig/config.go:440-448`; `OL:app/updater/updater.go:33-36,53-105,388-403`). |
| LibreHardwareMonitor | Native Windows sensor paths, D3D memory/engine counters, AMD/Intel clocks/temperatures where driver APIs support them. Whole-library GPU enumeration also enables NVIDIA wrappers; do not ship that library or its driver dependencies. Do not change clocks, fans, drivers or power (`HW:LibreHardwareMonitorLib/Hardware/Computer.cs:172-188`; `HW:LibreHardwareMonitorLib/Hardware/Gpu/AmdGpu.cs:77-88,114-158`; `HW:LibreHardwareMonitorLib/Hardware/Gpu/IntelIntegratedGpu.cs:44-79`; `HW:LibreHardwareMonitorLib/Interop/NvApi.cs:28-29`; `HW:LibreHardwareMonitorLib/Interop/NvidiaML.cs:13-16`). | Inspected local sensor reads need installed OS/driver interfaces, not GitHub. Optional HTTP export is off by default; it is not a reason to open a new listener. Complete GUI/add-on/update behaviour is not certified by this library-path read (`HW:LibreHardwareMonitor.Windows.Forms/UI/MainForm.cs:332-340`; `HW:LibreHardwareMonitor.Windows.Forms/Utilities/HttpServer.cs:38-55`). |
| EdgeVPN | Windows VPN source exists; it is an OS-tunnel component, not a GPU backend or native Windows AI engine (`EV:pkg/vpn/interface_windows.go:1-47`). | DHT defaults include public bootstrap peers unless configured; relay service and relay-client use are separate controls. Custom bootstrap/static relays or DHT-off/local discovery are relevant ideas; do not silently inherit public discovery (`EV:pkg/discovery/dht.go:98-106`; `EV:pkg/config/config.go:114-164,350-364`). |
| Headscale | Windows is supported by its Tailscale **clients**; this does not mean the Headscale control server is a native Windows executor (`HS:docs/about/clients.md:1-15`). No GPU backend. | Default DERP map is an external Tailscale URL with refresh on. Embedded DERP plus an empty external URL list/local map removes that dependency; configured OIDC/ACME/DNS/client updates remain separate services. Auto-update policy and the client's retained setting both matter (`HS:config-example.yaml:113-137,410-419`; `HS:docs/ref/derp.md:13-43`; `HS:docs/about/clients.md:18-38`). |
| Nebula | Windows build/smoke path and local certificates/TUN; no inference/GPU dependency (`NB:.github/workflows/smoke-extra.yml:87-90`; `NB:.github/workflows/release.yml:32-56`). | Configured lighthouses/static mappings and optional relays, no required public GitHub control service in inspected handshake path. DNS names can need DNS; metrics can export to configured systems, so keep them off/local. No global telemetry-absence assertion (`NB:examples/config.yml:28-50,294-306`; `NB:stats.go:25-66`; `NB:handshake_manager.go:1270-1274`). |
| iroh | Rust Windows release matrix; no GPU backend. Public pin is 1.4.1 versus LW snapshot's exact 1.0.0 dependency, so source compatibility is not assumed (`IR:.github/workflows/release.yml:103-108`; `IR:iroh/Cargo.toml:1-7`; `LW:crates/lw-link/Cargo.toml:22-24`). | N0 preset enables public DNS/pkarr address lookup and default relays; Minimal alone adds only crypto-provider configuration, but other builder defaults still need review. LW explicitly uses Minimal, relays disabled and port mapping disabled. Do not switch to N0 as a NAT fix. `N0DisableRelay` still invokes N0 address lookup (`IR:iroh/src/endpoint/presets.rs:62-78,116-136,175-182`; `IR:iroh/src/defaults.rs:26-48`; `LW:crates/lw-link/src/link.rs:28-41`). |

## The token auditor: what exists and what we must add

The rows below describe the inspected producer/API path, not every plugin.
An engine-native count means the engine reported token operations; it is not
independent proof of honest execution. A signed receipt establishes attributable,
unchanged claims and binds an answer only to the fields actually signed. It
does not prove correct inference, energy, GPU use or fair-share compliance.
No reviewed serving path below supplies the complete answer-bound, pinned-worker
receipt contract proposed for LatticeWorks. Transport handshakes, API auth,
database rows and release signatures are different evidence.

| Project | (h) Input/output counts, model, work timing, executor attribution | What original Rust should measure / retain |
|---|---|---|
| GPUStack | Direct proxy consumes backend usage; per-request records retain model/route/provider/cluster, counts, start/end and request/response correlation. Gateway incomplete reports can be filled from body-byte/chunk estimates; those are not native counts. Recorded TTFT explicitly measures the first body chunk, which can be role-only. The inspected audit-row schema does not bind one signed worker/model digest to the answer (`G:gpustack/api/middlewares.py:226-294,330-405`; `G:gpustack/schemas/model_usage_details.py:38-121`; `G:gpustack/server/metrics_collector.py:247-268`). | Preserve provenance and a terminal record for incomplete work. Separate first-body from first-token latency; no chunk/byte estimate enters the authoritative usage total. Bind exact selected worker and served artifact independently of a route alias. |
| gguf-parser-go | Model/tokenizer metadata and resource estimates, not token operations, serving timing or machine-work records. It cannot report tokens actually consumed by an answer (`P:file.go:54-76`; `P:file_estimate__llamacpp.go:108-164`). | Record estimator version/input configuration, predicted bytes and measured peak separately. Never turn vocabulary size, context size, memory estimates or theoretical throughput into observed token usage. |
| LocalAI | Backend replies carry prompt/output counts plus prompt-processing/generation durations; HTTP stream usage trailer uses final cumulative backend usage when requested. Optional `X-LocalAI-Node` identifies the selected worker in routed calls; requested/served model can differ. Scalar defaults still need explicit absence handling in our protocol; a node header is not a signed work receipt (`LA:core/backend/llm.go:36-42,265-272,330-338`; `LA:core/http/endpoints/openai/chat.go:890-911`; `LA:core/http/routes/openai.go:28-34,68-73`). | Capture the terminal usage independently of whether the caller requests a usage trailer. Keep requested versus served model, actual worker key and adapter's source/presence flags. Do not count each SSE/tool fragment as one output token or lose earlier tool-call usage. |
| exo | MLX path counts tokenized prompt IDs and generated token operations, with cached-prefix detail and generation stats. Task placement identifies runner/node internally; token chunks carry model/token/usage, not a signed executor certificate. Adapters differ: Ollama helper preserves missing values, but a Claude whole-response fallback uses zero when usage is absent (`EX:src/exo/worker/engines/mlx/generator/generate.py:766-789`; `EX:src/exo/shared/types/chunks.py:19-48`; `EX:src/exo/api/adapters/ollama.py:73-81`; `EX:src/exo/api/adapters/claude.py:331-340`). | Keep cached versus newly evaluated prompt work separate; retain contributor mapping before converting the external API. Missing remains null through every adapter. Shards do not each get credited with a second full set of answer tokens. |
| llama.cpp | Engine task counters become OpenAI prompt/completion/total and cached-prompt detail; native result includes model label, slot, counts and timings. HTTP model/slot IDs identify execution context, not a signed machine or all RPC contributors (`CPP:tools/server/server-task.cpp:333-363`; `CPP:tools/server/server-context.cpp:2370-2380`). | Use engine counts and phase timings, including cache semantics, rather than retokenizing visible output. Record engine/model digest and authenticated executor separately. An answer assembled with RPC needs contributor evidence, not merely the frontend's model label. |
| distributed-llama | Root tokenizer produces prompt length; non-stream response uses generation positions for completion count. Streaming branch sends text/final chunk without that non-stream usage object. API model label is generic while model listing derives from a file basename; no signed worker attribution/phase timing in this response contract (`DL:src/dllama-api.cpp:446-456,513-563,590-596`; `DL:src/api-types.hpp:93-123`). | Retain final native counters even for streaming/error outcomes. Explicitly document stop/EOS/cache accounting; a generic model label is insufficient identity. Root byte-transfer statistics are not token counts or evidence each worker performed its shard. |
| Ollama | Native prompt/output counters and durations, optional cached count; inspected backend adapter reconstructs full prompt count from cached plus newly evaluated tokens. API returns model and local runner result, not a signed fleet executor. Errors/disconnects may prevent a final metrics object reaching the caller (`OL:api/types.go:562-570`; `OL:llm/llama_server.go:1639-1652,1868-1878`; `OL:server/routes.go:3333-3374`). | Keep total presented prompt, cache hits and actual prefill work distinct; do not add cache to an already-inclusive prompt count twice. Keep queue/load/prefill/decode/end-to-end durations separate and null if absent. |
| LibreHardwareMonitor | No LLM counts, model or answer timing. Sensor samples have hardware identity/query time and can show clocks, memory and temperature; none binds them to one answer or proves the process used a GPU (`HW:LibreHardwareMonitorLib/Hardware/D3DDisplayDevice.cs:64-139`; `HW:LibreHardwareMonitorLib/Hardware/Gpu/IntelIntegratedGpu.cs:44-79`). | Correlate bounded local samples with an admitted execution interval; label attribution/coverage. Never infer tokens or useful capacity solely from clock MHz, utilization or temperature. No person's wall-clock values need leave the box. |
| Headscale | Node identities, enrollment, connectivity and API state; no model, tokens or inference phase measurements (`HS:hscontrol/auth.go:148-177`; `HS:hscontrol/poll.go:175-257`; `HS:hscontrol/app.go:530-565`). | Network-path provenance only. A live node/map or DERP session cannot complete an answer receipt. |
| Nebula | Certificate/network identity and traffic/liveness statistics; no model/token/answer contract (`NB:handshake_manager.go:1270-1274`; `NB:stats.go:25-66`; `NB:connection_manager.go:346-435`). | Identify the transport peer separately from the pinned executor; byte counters are diagnostic only. |
| iroh | Endpoint identity, path/connection state and streams, no model/token accounting or per-answer application signature (`IR:iroh/src/endpoint/connection.rs:375-410,569-572`; `IR:iroh/src/endpoint.rs:827-843`). | Bind the already-paired endpoint to the existing LW signer; transport encryption does not replace a replay-safe terminal receipt. |
| EdgeVPN | Peer/service/health ledger and optional network metrics, no model/token/answer contract (`EV:pkg/services/alive.go:29-90`; `EV:api/api.go:217-230,317-326,422-462`). | Reachability is an input to selection only. Do not treat a shared room token or advertised service as execution evidence. |

### Proposed answer evidence, in plain words

This is a contract proposal for the owner of LW's schema, not an applied format
change. Extend the current receipt/auditor increment only where these facts are
not already signed; do not relabel an old signature as covering new fields.

- Bind the logical call and unique attempt, pinned executor key, requested and
  served model identities, model-artifact digest, approved backend/build, and
  answer digest. The asker's local verifier hashes the exact answer bytes and
  checks the pre-pinned signer. A valid signature by an unexpected machine fails.
- Record engine-reported input, output, cache and any supported reasoning/tool
  subdivisions with presence/source flags. Keep native and locally estimated
  diagnostics separate. Genuine reported zero is allowed; absent is null.
- Record local monotonic elapsed queue, load, prefill, generation and delivery
  intervals where observable. Distinguish first byte, first meaningful token and
  engine processing time. Do not subtract clocks from different computers or
  export a person's wall-clock readings. Sensor clock MHz is a different unit.
- Exactly one terminal signed receipt per execution attempt; the answer points
  to the successful one. Failed/abandoned attempts retain their signed terminal
  status and known work with missing final counts explicit; they do not create
  a second successful answer or disappear from the meter. Duplicate receipt
  delivery is deduplicated by signed attempt identity, not timing proximity.
- The solver writes terminal evidence before declaring audit completion; the
  asker verifies and durably joins it to existing request/claim/placement/run/
  result/settle rows. If receipt persistence/verification fails, mark incomplete;
  do not silently turn engine success into an auditor pass. Local recovery may
  reconcile the same terminal record, never rerun work just to recreate it.
- For later multi-machine inference, one canonical answer count plus a declared
  contributor/stage set. Stage receipts report their own role and measured work;
  they do not each multiply the prompt/completion total. A missing contributor
  makes that execution-evidence claim incomplete. Independently proving that a
  malicious worker computed correctly is a different, unbuilt capability.

Existing baseline caution: LW already signs reported counts for a call, but the
inspected signature covers call ID and two counts, not the entire proposed
envelope. If either count is absent, it retains a signed action row and omits
the numeric receipt; the Rust auditor must preserve that distinction
(`LW:crates/lw-gateway/src/lend.rs:3286-3297,3647-3666,3732-3757`). These are
reasons to extend the current schema/join work, not rebuild its provenance stack.

## Remaining piece verdicts and mapping

All rows below concern behaviour we studied, not third-party adoption. The top
five have the same required verdict/size/source/mapping fields above.

| Piece | Verdict / size | Reason and owned LW interface / target | Source studied |
|---|---|---|---|
| GGUF architecture-specific advanced estimator catalogue | **IDEA ONLY, L** beyond a supported first subset | Derive and validate our own supported-model sizing against measured peaks. Unknown architectures refuse. Do not translate the large Go estimator or its fitted constants. Target: existing GGUF gate plus room-check input. | `P:file_estimate__llamacpp.go:168-205,339-359`; `P:file_estimate__llamacpp_test.go:70-127,328-391`. |
| GPUStack candidate filter / scoring separation | **REBUILD IN RUST, M** | Eligibility precedes preference; expose why a candidate is excluded before ranking resident/locality choices. Input owned offers/requirements, output an explainable placement. Target: one fleet planner plus room-check. GPUStack's "pairing affinity" is placement terminology, not our human pairing. | `G:gpustack/policies/worker_filters/status_filter.py:18-50`; `G:gpustack/scheduler/scheduler.py:979-1009,1218-1242`. |
| LocalAI distributed staging/reservation lifecycle | **REBUILD IN RUST, M** | Claim a bounded capacity lease before expensive load, preserve its owner/attempt identity through failure/restart and release once. Existing LW queue owner must choose the missing increment; no extra PostgreSQL/NATS service is proposed. | `LA:core/services/nodes/router.go:359-395`; `LA:core/services/nodes/router_reservation_test.go:56-81`; target `T:codex/PRODUCT_DESIGN_MAP.md:198-200`. |
| exo topology-aware shard planning / compatibility gates | **IDEA ONLY, L** for shard runtime; **REBUILD IN RUST, S** for owned version/capability rejection | Reject incompatible protocol/build/model offers before admission. Later sharding needs an independently designed memory/communication plan, bandwidth trials, distributed cancellation and contributor receipts. Target: task-host capability row first, not replacement of the lend road. | `EX:rust/networking/src/lib.rs:48-61`; `EX:src/exo/master/placement.py:81-112`; `EX:src/exo/master/placement_utils.py:21-73`. |
| llama.cpp buffer/graph RPC and distributed-llama tensor split | **IDEA ONLY, L** | Useful proof that computation can be partitioned, not a safe production protocol to clone. Plan activation/weight/cache ownership and recovery from a written behavioural spec, then implement original Rust if a measured model-fit need justifies it. Target: later executor implementation. | `CPP:ggml/src/ggml-rpc/ggml-rpc.cpp:377-432`; `CPP:tools/rpc/README.md:1-8`; `DL:src/llm.cpp:165-176`; `DL:src/app.cpp:233-241`. |
| Raw unauthenticated RPC/worker wire and fixed trusted-LAN join | **SKIP, S** decision | No addition beside LW's paired, authenticated, consent-gated link; it would create a bypass. No new unguarded GPU listener. | `CPP:tools/rpc/README.md:1-8`; `DL:src/nn/nn-network.cpp:298-329`; compare `LW:crates/lw-link/src/pair.rs:5-34`. |
| Ollama local residency/refcount accounting | **REBUILD IN RUST, M**; eviction policy **SKIP, S** | Track held/running/idle/load cost for our executor; wait/refuse if capacity is unavailable. Do not evict another owner's active model or borrow cloud capacity automatically. Target: room-check/fair-share reservations, not a new runner supervisor by default. | `OL:server/sched.go:580-615,1706-1735`; target `LW:crates/lw-gateway/src/lend.rs:2682-2707`. |
| Headscale / Nebula overlay control planes | **IDEA ONLY, L**; second shipped VPN stack **SKIP, S** | Learn separation of enrollment, endpoint discovery, relay and data transport. Existing LW iroh pairing remains. A self-hosted relay requires an explicit operator design; no new trust CA, virtual adapter, account or background service here. | `HS:hscontrol/auth.go:148-177`; `HS:docs/ref/derp.md:13-43`; `NB:handshake_manager.go:1270-1274`; target `LW:crates/lw-link/src/link.rs:28-41`. |
| EdgeVPN shared-secret discovery and ambient public DHT | **IDEA ONLY, M** for service-expiry concept; default trust/discovery **SKIP, S** | Advertise only bounded capabilities while lending, expire stale offers, and keep membership separate from permission to execute. Do not replace LW matching-code Accept with a shared room token or expose network identities to public discovery. | `EV:pkg/services/alive.go:29-90`; `EV:pkg/discovery/dht.go:98-106`; `LA:core/cli/worker/worker_p2p.go:40-67`; target `LW:crates/lw-link/src/pair.rs:5-34`. |
| Iroh path state / relay diagnostics | **REBUILD IN RUST, S** for owned status adapter; transport rewrite **SKIP, L** | Use the already-approved transport's state to explain direct/unavailable/authorized-relay paths; keep application timeout/receipt logic separate. No source import from this new pin, no automatic version upgrade, no new cryptography or public lookup default. Target: `lw-link` and existing breaker. | `IR:iroh/src/endpoint.rs:827-843`; `IR:iroh/src/endpoint/presets.rs:116-136,175-182`; `LW:crates/lw-link/Cargo.toml:22-24`. |
| LHM sensor meaning, supported/unsupported readings | **REBUILD IN RUST, M** for read-only observation subset; tuning/driver-management **SKIP, L** | Derive our own OS adapter from platform documentation after understanding the quantities. Keep unknown values explicit; don't duplicate shared memory or confuse clock with delivered tokens. No C# translation, hardware controls or bundled vendor files. Target: Hypervisor inputs and fair-share, not evidence of GPU release. | `HW:LibreHardwareMonitorLib/Hardware/D3DDisplayDevice.cs:64-139`; `HW:LibreHardwareMonitorLib/Hardware/Gpu/IntelIntegratedGpu.cs:44-79`; `LW:apps/console/src/hyper-gpu.mjs:26-59`. |

### Binding integration boundaries

1. **One existing road.** `lw-link` already pins a human-accepted peer and bridges
   to the loopback lend target; preserve it. LW baseline explicitly disables
   relays and port mapping. Public iroh defaults are not an authorization to
   enable external discovery (`LW:crates/lw-link/src/pair.rs:5-34`;
   `LW:crates/lw-link/src/link.rs:21-41`).
2. **Lending switch, then consent, then live admission.** Re-read owner Stop,
   model sharing and room/fair-share constraints on the executor at use time;
   a task-host capability or old room answer is not a reservation or grant.
   The current map has an open counter-reread issue on the lend road; this
   research does not mark it fixed (`LW:crates/lw-gateway/src/lend.rs:24-27,2682-2707`;
   `T:codex/PRODUCT_DESIGN_MAP.md:21,75`). No silent owner-model eviction.
3. **Task host is a contract, not another service.** Machine offers declare
   supported task kinds, model artifacts and budgets, but every claim is
   revalidated locally. Echo is optional; the LW lend worker runs everywhere.
   Extend one queue with leases/expiry/attempt identities rather than creating
   a competing queue (`T:codex/PRODUCT_DESIGN_MAP.md:180-200`).
4. **Hypervisor is a consumer of qualified observations.** Current snapshot's
   GPU aggregation keeps the busiest engine after summing processes per engine;
   do not sum independent utilization percentages as capacity. Clock changes,
   throttling, sampling gaps and shared/unified memory need source/uncertainty,
   not a universal conversion to useful work. Port only the owner's reviewed
   maths, after checking in-flight fixes (`LW:apps/console/src/hyper-gpu.mjs:26-59`;
   `LW:apps/console/src/hyper-data.mjs:57-75`; `T:codex/PRODUCT_DESIGN_MAP.md:63-75`).
5. **No GitHub requirement.** The final build/install/run must use approved
   local artifacts without fetching from GitHub, including hidden galleries,
   updater fallback and build-time dependencies. Source links in this research
   are citations, not execution dependencies. Coordinate with the existing
   LW-NO-GITHUB lane; this card vendors nothing and changes no package
   (`T:codex/PRODUCT_DESIGN_MAP.md:86`). Check a future release manifest for
   NVIDIA files, and test CPU plus supported Vulkan hardware independently.

## Smallest acceptance plan for the first Rust capability

These are future tests, not results from this research. Reuse existing LW tests
and add only missing cases. All names are fixed and each identifies the rule
whose removal should make it fail; no generated titles from unbounded input.

| Proposed test / failing mutation | Required observation |
|---|---|
| `receipt_rejects_answer_change` / omit answer binding | The same signed terminal evidence cannot validate changed returned bytes. |
| `receipt_rejects_wrong_executor` / trust a response-supplied key | A valid signature outside the pre-pinned solver identity refuses. |
| `usage_missing_stays_missing` / replace absent with zero | Each missing count remains missing through writer, receipt verification, join and display. Genuine engine zero has its own positive control. |
| `cache_is_not_added_twice` / add cache to an inclusive prompt count | Engine-native total, cached and newly evaluated counts remain separate and reconcile according to the adapter contract. |
| `one_terminal_per_attempt` / allow duplicate terminal credit | Duplicate delivery or a reconnect cannot mint another counted answer. A reused attempt with changed content refuses. |
| `disconnect_keeps_incomplete_work` / discard failed meter row or synthesize success | Cut the worker link after output; retain known work and explicit missing final usage, never a complete audit or spliced retry. |
| `retry_before_commit_only` / remove output-commit gate | Retry after visible output refuses. Before-output retry is bounded, uses a new attempt and does not leave old work running. |
| `stop_or_no_consent_blocks_executor` / bypass the final owner/consent check | A matching peer/capability alone cannot run; Stop, lending-off, rejected pairing, missing n2HO approval or exhausted fair share prevents it. |
| `receipt_persistence_failure_is_incomplete` / ignore terminal write failure | Engine answer success does not produce a complete auditor statement without its durable verified terminal evidence. |
| `windows_offline_artifact_gate` / add a hidden download/update path | Build/install/run under GitHub and unapproved-service denial, with only local artifacts, and inspect the shipped files for NVIDIA payloads. No reference server is launched. |

The real pass requires a Windows requester and a different approved Windows
executor, matching pairing codes plus Accept, lending enabled, n2HO permission,
room/fair-share admission, one answer and its verified terminal receipt/stage
join. Repeat missing usage and worker-loss cases; capture auditor verdicts and
offsets/counts only. A fake engine can test rules but cannot establish a real
remote answer, GPU use or independently honest computation.

## Research validation and delivery

Only this Markdown report is committed, on `codex/PRIOR-ART-SERVE` from rpp-spec
`ae10d65a520d25958197f77e6cf784e6b8d177ce`. No product code, vector, constant,
header, layout, spec, dependency, workflow or existing outbox changes. Scratch
source is not vendored. No upstream issue/PR/comment or service write; only the
authorized report branch is pushed normally once. No merge or force push.

| Check | Observed result |
|---|---|
| Source pin verification | All 11 TR prefixes resolved to exact commits; additional EdgeVPN head pinned separately. Source archives read without execution. |
| Citation audit | 258 explicit file/line citations resolve within the stated trees and line bounds. This checks locators; the behavioural conclusions were separately read against the cited code. |
| RPP regressions | `python -m pytest tests/ -q -o addopts=`: **1256 passed**, one pre-existing legacy-format deprecation warning. |
| Golden checks | `python tests/test_golden_vectors_mobius32.py`: **5 passed / 0 failed**. |
| Lint | ruff **0.14.10**, `ruff check rpp/ tests/ --ignore E501`: exit 0. No changed Rust/Python source to format or compile. |
| Scope / whitespace | One new Markdown file; `git diff --check`: exit 0. No copied code blocks or reference binaries in the committed diff. |
| Report drift | `python -m tools.drift check --base ae10d65a520d25958197f77e6cf784e6b8d177ce --head <report-sha> --output-dir <scratch-dir>`: **0 HIGH / 0 MEDIUM / 0 LOW**, exit 0; 239 pending baselines and 1 advisory remain visible. |
| Hygiene | Report scan clear for prohibited vocabulary, person clock values and private-key markers. No test corpus or byte-hashed artifact added. |

Windows cargo/GPU/NAT/peer-loss acceptance is **NOT RUN**; the proposed future
checks above are not results. Existing RPP regressions protect the report
branch baseline, not any claim about an upstream engine. No foreign benchmark
was used to claim a speedup. The first five choices rank engineering value and
scope under our constraints, not measured cross-project throughput.
