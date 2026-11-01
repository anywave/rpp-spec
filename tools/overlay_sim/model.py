"""Scripted overlay policy, using abstract prior signature/tunnel verification results.

All times are integer scenario ticks, all link measurements are scripted observations.
No signature, cipher, discovery service, enrollment or actual transport is implemented.
"""

from dataclasses import asdict, dataclass
import csv
import io
import json
from itertools import count
from typing import Mapping

CONTROL_KINDS = frozenset({"ALIVE", "MEMBER-CHANGED", "STOP", "PAUSE", "ROUTE-AROUND", "RESUME"})
UNDERLAYS = frozenset({"LAN", "Wi-Fi", "internet", "Bluetooth", "LoRa"})
IP_UNDERLAYS = frozenset({"LAN", "Wi-Fi", "internet"})


@dataclass(frozen=True)
class Link:
    name: str
    left: str
    right: str
    underlay: str
    latency: int
    loss_ppm: int
    jitter: int
    available: bool
    observed: int
    failure_domain: str
    tunnel_verified: bool = True
    reviewed_adapter: bool = False
    observation_verified: bool = True

    def __post_init__(self):
        if any(type(x) is not bool for x in (self.available, self.tunnel_verified, self.reviewed_adapter, self.observation_verified)):
            raise ValueError("link availability and verification verdicts must be booleans")
        if not all(isinstance(x, str) and 0 < len(x) <= 64 for x in (self.name, self.left, self.right, self.failure_domain)):
            raise ValueError("link identifiers must be bounded nonempty strings")
        if not isinstance(self.underlay, str) or self.underlay not in UNDERLAYS:
            raise ValueError("unknown underlay")
        if self.left == self.right or not self.name or not self.failure_domain:
            raise ValueError("invalid link identity")
        if any(type(x) is not int for x in (self.latency, self.loss_ppm, self.jitter, self.observed)):
            raise ValueError("measurements must be integer scenario units")
        if min(self.latency, self.jitter, self.observed) < 0 or not 0 <= self.loss_ppm <= 1_000_000:
            raise ValueError("invalid link reading")

    @property
    def score(self):
        # IMPOSED demo cost: milliseconds scaled by 1000, loss at 1 point/ppm.
        return 1000 * (self.latency + 2 * self.jitter) + self.loss_ppm

    @property
    def supports_data(self):
        return self.tunnel_verified and (self.underlay in IP_UNDERLAYS or self.reviewed_adapter)


@dataclass(frozen=True)
class Auth:
    """Scripted outcome of verification by an existing reviewed protocol, not a signature."""
    issuer: str
    signature_verified: bool


@dataclass(frozen=True)
class Billboard:
    machine: str
    kind: str
    fact: str
    since: int
    until: int
    receipt: str

    def valid_shape(self):
        try:
            fact_bytes = self.fact.encode("utf-8") if isinstance(self.fact, str) else b""
        except UnicodeEncodeError:
            return False
        return (
            isinstance(self.machine, str) and 0 < len(self.machine) <= 64
            and isinstance(self.kind, str) and self.kind in {"fact", "rule"}
            and isinstance(self.fact, str) and 0 < len(fact_bytes) <= 256
            and type(self.since) is int and type(self.until) is int
            and 0 <= self.since < self.until
            and isinstance(self.receipt, str) and 0 < len(self.receipt) <= 64
            and self.receipt.isascii() and all(c.isalnum() or c in "-_." for c in self.receipt)
        )


class Simulator:
    """Selection never supplies consent or membership; caller fixtures supply both.

    Demo policy: readings expire after five ticks; two failures open a link breaker
    for two ticks. These local policy values are not protocol constants.
    """

    def __init__(self, members, consents, billboard_scopes=()):
        self.members = frozenset(members)
        self.consents = frozenset(tuple(x) for x in consents)
        self.scopes = frozenset(tuple(x) for x in billboard_scopes)
        self.rows = []
        self._ids = count(1)
        self._failures = {}
        self._open_until = {}
        self._billboards = {}
        self._receipts = set()
        self._control_sequences = {}
        self._clock = 0
        self._known_data_paths = set()

    def _meter(self, tick, request, traffic, source, target, path=(), status="OK", tokens=0, detail=""):
        row = dict(row=len(self.rows) + 1, tick=tick, request=request, traffic=traffic,
                   source=source, target=target, path="/".join(x.name for x in path),
                   status=status, tokens=tokens, detail=detail)
        self.rows.append(row)
        return row

    def _time_valid(self, tick):
        return type(tick) is int and self._clock <= tick < 2**64

    def _advance(self, tick):
        # Call only after the operation and its path have been accepted.
        self._clock = tick

    @staticmethod
    def _links_valid(links):
        return (isinstance(links, (list, tuple)) and all(isinstance(x, Link) for x in links)
                and len({x.name for x in links}) == len(links))

    @staticmethod
    def _identifier(value):
        return isinstance(value, str) and 0 < len(value) <= 64

    def _auth_valid(self, auth):
        return isinstance(auth, Auth) and self._identifier(auth.issuer) and auth.signature_verified is True

    def _authorized(self, source, target):
        return (self._identifier(source) and self._identifier(target) and source != target
                and source in self.members and target in self.members and (source, target) in self.consents)

    def _known_independent_reference(self, source, target, tick, data_path):
        return (isinstance(data_path, (list, tuple)) and bool(data_path)
                and all(isinstance(x, Link) and x.supports_data for x in data_path)
                and any(a == source and b == target and selected <= tick and path == tuple(data_path)
                        for a, b, selected, path in self._known_data_paths))

    def _usable(self, link, tick, traffic, excluded):
        return (link.name not in excluded and link.available and link.observation_verified
                and 0 <= tick - link.observed <= 5
                and tick >= self._open_until.get(link.name, 0)
                and link.left in self.members and link.right in self.members
                and link.tunnel_verified and (traffic == "control" or link.supports_data))

    def choose(self, source, target, tick, links, traffic="data", excluded=frozenset(), avoid_domains=frozenset()):
        """Best simple authorized path; optional independent failure-domain restriction."""
        if not self._authorized(source, target) or type(tick) is not int or tick < 0:
            return ()
        if not self._links_valid(links):
            raise ValueError("invalid or duplicate link identity")
        candidates = [x for x in links if self._usable(x, tick, traffic, excluded)
                      and x.failure_domain not in avoid_domains]
        paths = []

        def visit(node, seen, path):
            if node == target:
                paths.append(path)
                return
            for link in sorted(candidates, key=lambda x: x.name):
                other = link.right if link.left == node else link.left if link.right == node else None
                if other is not None and other not in seen:
                    # Relays are pre-authorized members; hop forwarding needs consent too.
                    if (node, other) in self.consents:
                        visit(other, seen | {other}, path + (link,))

        visit(source, {source}, ())
        chosen = min(paths, key=lambda p: (sum(x.score for x in p), len(p), tuple(x.name for x in p))) if paths else ()
        if chosen and traffic == "data":
            self._known_data_paths.add((source, target, tick, chosen))
        return chosen

    def send_data(self, tick, source, target, links, scripted_failures=None):
        """A failure value is the number of tokens already emitted; zero allows retry."""
        request = next(self._ids)
        scripted_failures = {} if scripted_failures is None else scripted_failures
        valid_script = (isinstance(scripted_failures, Mapping)
                        and all(isinstance(k, str) and type(v) is int and v >= 0 for k, v in scripted_failures.items()))
        if not self._time_valid(tick) or not self._links_valid(links) or not valid_script:
            self._meter(tick, request, "data", source, target, status="INVALID_INPUT")
            return
        if source == target:
            self._meter(tick, request, "data", source, target, status="DENIED_SELF_TARGET")
            return
        if not self._authorized(source, target):
            self._meter(tick, request, "data", source, target, status="DENIED")
            return
        scripted_failures = scripted_failures or {}
        excluded = set()
        while True:
            path = self.choose(source, target, tick, links, excluded=excluded)
            if not path:
                self._meter(tick, request, "data", source, target, status="NO_CHANNEL")
                return
            self._advance(tick)
            failure = next((x for x in path if x.name in scripted_failures), None)
            if failure is None:
                for link in path:
                    self._failures[link.name] = 0
                self._meter(tick, request, "data", source, target, path, tokens=3,
                            detail="relay" if len(path) > 1 else "direct")
                return
            tokens = scripted_failures[failure.name]
            self._failures[failure.name] = self._failures.get(failure.name, 0) + 1
            if self._failures[failure.name] >= 2:
                self._open_until[failure.name] = tick + 2
                self._failures[failure.name] = 0
            self._meter(tick, request, "data", source, target, path, "FAILED", tokens,
                        "retry-before-first-token" if tokens == 0 else "terminal-after-first-token")
            if tokens:
                return
            excluded.add(failure.name)

    def send_control(self, tick, message: Mapping, auth, links, data_path=()):
        request = next(self._ids)
        if not self._time_valid(tick) or not self._links_valid(links):
            return self._meter(tick, request, "control", "", "", status="INVALID_INPUT")
        # Exact field allowlist avoids payload smuggling, including signed unknown fields.
        message = message if isinstance(message, Mapping) else {}
        shape = set(message) == {"source", "target", "kind", "sequence"}
        source, target = message.get("source", ""), message.get("target", "")
        kind, sequence = message.get("kind"), message.get("sequence")
        identifiers = all(isinstance(x, str) and 0 < len(x) <= 64 for x in (source, target))
        if identifiers and source == target:
            return self._meter(tick, request, "control", source, target, status="DENIED_SELF_TARGET")
        good = (shape and identifiers and isinstance(kind, str) and kind in CONTROL_KINDS
                and type(sequence) is int and 0 <= sequence < 2**64
                and self._auth_valid(auth) and auth.issuer == source
                and self._authorized(source, target)
                and sequence > self._control_sequences.get((source, target), -1))
        if not good:
            return self._meter(tick, request, "control", source, target, status="DENIED")
        if not self._known_independent_reference(source, target, tick, data_path):
            return self._meter(tick, request, "control", source, target, status="DENIED", detail="unknown-data-path")
        domains = frozenset(x.failure_domain for x in data_path)
        path = self.choose(source, target, tick, links, "control", avoid_domains=domains)
        if not path:
            return self._meter(tick, request, "control", source, target, status="NO_INDEPENDENT_CHANNEL")
        self._advance(tick)
        self._control_sequences[source, target] = sequence
        # This records status only; RESUME never creates a request, consent or member.
        return self._meter(tick, request, "control", source, target, path, detail=kind)

    def deliver_billboard(self, tick, billboard, auth, source, target, links):
        request = next(self._ids)
        if not self._time_valid(tick) or not self._links_valid(links):
            return self._meter(tick, request, "billboard", source, target, status="INVALID_INPUT")
        if source == target:
            return self._meter(tick, request, "billboard", source, target, status="DENIED_SELF_TARGET")
        good = (isinstance(billboard, Billboard) and billboard.valid_shape()
                and self._auth_valid(auth) and auth.issuer in self.members
                and (auth.issuer, billboard.machine, billboard.kind) in self.scopes
                and billboard.machine == target and self._authorized(source, target)
                and (auth.issuer, billboard.receipt) not in self._receipts and self._delivery_current(tick, billboard))
        if not good:
            return self._meter(tick, request, "billboard", source, target, status="DENIED")
        path = self.choose(source, target, tick, links)
        if not path:
            return self._meter(tick, request, "billboard", source, target, status="NO_CHANNEL")
        self._advance(tick)
        receipt_key = (auth.issuer, billboard.receipt)
        self._receipts.add(receipt_key)
        self._billboards[receipt_key] = billboard
        return self._meter(tick, request, "billboard", source, target, path,
                           status="DELIVERED" if tick >= billboard.since else "HELD_UNTIL_SINCE",
                           detail=billboard.receipt)

    @staticmethod
    def _delivery_current(tick, billboard):
        return tick < billboard.until

    def active_billboards(self, tick, machine):
        if not self._identifier(machine) or machine not in self.members:
            raise ValueError("unknown billboard recipient")
        if not self._time_valid(tick):
            raise ValueError("billboard application time cannot move backwards")
        self._advance(tick)
        # Re-evaluate each time: delivered once does not mean permanently applied.
        return tuple(asdict(b) for _, b in sorted(self._billboards.items())
                     if b.machine == machine and b.since <= tick < b.until)


def serialize(rows):
    output = io.StringIO(newline="")
    fields = ["row", "tick", "request", "traffic", "source", "target", "path", "status", "tokens", "detail"]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
