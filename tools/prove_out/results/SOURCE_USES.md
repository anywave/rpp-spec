# All lexical source uses (read-only inventory)

## coherence

```text
rpp/__init__.py:26:    coherence,
rpp/__init__.py:49:    encode_coherence,
rpp/__init__.py:50:    decode_coherence,
rpp/__init__.py:76:    verify_self_coherence,
rpp/__init__.py:133:    "coherence",
rpp/__init__.py:152:    "encode_coherence",
rpp/__init__.py:153:    "decode_coherence",
rpp/__init__.py:181:    "verify_self_coherence",
rpp/address_canonical.py:185:    Omega format tiers (coherence/precision levels).
rpp/address_canonical.py:221:        omega: Omega tier 0-4 (coherence level)
rpp/address_canonical.py:517:# Coherence Functions
rpp/address_canonical.py:527:        w_h = 0.20 (coherence tier)
rpp/address_canonical.py:548:def coherence(a: RPPAddress, b: RPPAddress) -> float:
rpp/address_canonical.py:550:    Calculate coherence score between two addresses.
rpp/address_canonical.py:702:    # Coherence
rpp/address_canonical.py:703:    print(f"\n  Coherence(addr1, addr2): {coherence(addr1, addr2):.4f}")
rpp/biofield.py:22:    MAX_COHERENCE,
rpp/biofield.py:36:    BOUND = 2         # Fully bound (coherence >= 137)
rpp/biofield.py:37:    DEPHASING = 3     # Lost coherence, within KHAT window
rpp/biofield.py:58:    coherence: int
rpp/biofield.py:59:    """Coherence score at time of event."""
rpp/biofield.py:76:    Binding requires coherence score >= 137 (alpha-inverse threshold).
rpp/biofield.py:77:    This represents approximately 20.3% of maximum coherence.
rpp/biofield.py:79:    When coherence drops below threshold, the system enters
rpp/biofield.py:84:    def __init__(self, initial_coherence: int = 0):
rpp/biofield.py:89:            initial_coherence: Starting coherence score (0-674)
rpp/biofield.py:91:        self._coherence: int = max(0, min(MAX_COHERENCE, initial_coherence))
rpp/biofield.py:98:        # Initialize status based on coherence
rpp/biofield.py:106:    def coherence(self) -> int:
rpp/biofield.py:107:        """Get current coherence score (0-674)."""
rpp/biofield.py:108:        return self._coherence
rpp/biofield.py:115:        kappa_bind = coherence / MAX_COHERENCE
rpp/biofield.py:120:        return self._coherence / MAX_COHERENCE
rpp/biofield.py:130:            True if coherence meets binding threshold
rpp/biofield.py:178:    # Coherence Updates
rpp/biofield.py:181:    def update_coherence(self, coherence: int) -> BindingStatus:
rpp/biofield.py:183:        Update coherence score and recalculate binding status.
rpp/biofield.py:186:            coherence: New coherence score (0-674)
rpp/biofield.py:191:        self._coherence = max(0, min(MAX_COHERENCE, coherence))
rpp/biofield.py:197:        """Recalculate binding status based on coherence."""
rpp/biofield.py:232:                f"Binding established (coherence={self._coherence})",
rpp/biofield.py:234:                f"Binding initiated (coherence={self._coherence})",
rpp/biofield.py:236:                f"Binding completed (coherence={self._coherence})",
rpp/biofield.py:238:                f"Binding failed (coherence={self._coherence})",
rpp/biofield.py:240:                f"Dephasing started (coherence={self._coherence})",
rpp/biofield.py:242:                f"Recovered from dephase (coherence={self._coherence})",
rpp/biofield.py:246:                f"Re-binding initiated (coherence={self._coherence})",
rpp/biofield.py:258:            coherence=self._coherence,
rpp/biofield.py:294:        Called when coherence drops below threshold.
rpp/biofield.py:312:    def attempt_resync(self, coherence: int) -> bool:
rpp/biofield.py:317:            coherence: New coherence score
rpp/biofield.py:322:        self.update_coherence(coherence)
rpp/biofield.py:329:        Sets coherence to binding threshold and status to BOUND.
rpp/biofield.py:331:        self._coherence = int(BINDING_THRESHOLD * MAX_COHERENCE) + 1  # 138
rpp/biofield.py:342:        Sets coherence to 0 and status to UNBOUND.
rpp/biofield.py:344:        self._coherence = 0
rpp/biofield.py:354:        self._coherence = 0
rpp/biofield.py:371:    PMAs store coherence snapshots that fragments can use
rpp/biofield.py:378:    coherence_snapshot: int
rpp/biofield.py:379:    """Coherence score at anchor creation."""
rpp/biofield.py:428:        coherence: int,
rpp/biofield.py:435:            coherence: Current coherence score
rpp/biofield.py:443:            coherence_snapshot=coherence,
rpp/biofield.py:466:        Get best anchor for resync (highest coherence).
rpp/biofield.py:469:            Anchor with highest coherence, or None
rpp/biofield.py:474:        return max(valid, key=lambda a: a.coherence_snapshot)
rpp/biofield.py:493:    Compute the minimum coherence score for binding.
rpp/biofield.py:496:        Minimum coherence (137) for binding
rpp/biofield.py:498:    return int(BINDING_THRESHOLD * MAX_COHERENCE)
rpp/biofield.py:501:def is_coherence_binding(coherence: int) -> bool:
rpp/biofield.py:503:    Check if coherence score meets binding threshold.
rpp/biofield.py:506:        coherence: Coherence score to check
rpp/biofield.py:509:        True if coherence >= 137
rpp/biofield.py:511:    return coherence >= compute_binding_threshold_score()
rpp/coherence.py:2:Coherence Module
rpp/coherence.py:5:Ra-symbolic coherence computation for SPIRAL protocol.
rpp/coherence.py:6:Implements the coherence formula: (φ × E) + (𝔄 × C) = 674 max
rpp/coherence.py:8:Reference: SPIRAL-Architecture.md Section 6 (Coherence Scoring)
rpp/coherence.py:20:    MAX_COHERENCE,
rpp/coherence.py:32:    Complecount state based on coherence level.
rpp/coherence.py:35:    - 0: No coherence (fragmented)
rpp/coherence.py:50:# Coherence Result
rpp/coherence.py:54:class CoherenceResult:
rpp/coherence.py:55:    """Result of coherence computation."""
rpp/coherence.py:58:    """Raw coherence score (0-674)."""
rpp/coherence.py:61:    """Binding coefficient (score / MAX_COHERENCE)."""
rpp/coherence.py:86:def compute_coherence_score(
rpp/coherence.py:91:    Compute coherence score using Ra-symbolic formula.
rpp/coherence.py:93:    Formula: coherence = (φ × E) + (𝔄 × C)
rpp/coherence.py:105:        Coherence score (0 to 674)
rpp/coherence.py:118:    return min(MAX_COHERENCE, max(0, score))
rpp/coherence.py:123:    Compute binding coefficient from coherence score.
rpp/coherence.py:129:        score: Coherence score (0-674)
rpp/coherence.py:136:    return min(1.0, score / MAX_COHERENCE)
rpp/coherence.py:143:    Threshold is α⁻¹ / MAX_COHERENCE = 137/674 ≈ 0.203
rpp/coherence.py:157:    Compute complecount from coherence score.
rpp/coherence.py:163:        score: Coherence score (0-674)
rpp/coherence.py:172:    # Each complecount level represents ~96 points of coherence
rpp/coherence.py:174:    complecount = int((score / MAX_COHERENCE) * 7)
rpp/coherence.py:197:def compute_coherence(
rpp/coherence.py:200:) -> CoherenceResult:
rpp/coherence.py:202:    Compute full coherence result with all derived values.
rpp/coherence.py:204:    This is the primary API for coherence computation, returning
rpp/coherence.py:205:    a complete CoherenceResult with score, binding, complecount,
rpp/coherence.py:213:        CoherenceResult with all computed values
rpp/coherence.py:216:        >>> result = compute_coherence(0.8, 0.9)
rpp/coherence.py:229:    score = compute_coherence_score(engagement, completion)
rpp/coherence.py:240:    return CoherenceResult(
rpp/coherence.py:258:    Convert coherence score to percentage.
rpp/coherence.py:261:        score: Coherence score (0-674)
rpp/coherence.py:266:    return (score / MAX_COHERENCE) * 100.0
rpp/coherence.py:271:    Convert percentage to coherence score.
rpp/coherence.py:277:        Coherence score (0-674)
rpp/coherence.py:280:    return int((percentage / 100.0) * MAX_COHERENCE)
rpp/coherence.py:288:        Minimum coherence score (137)
rpp/coherence.py:293:def describe_coherence(result: CoherenceResult) -> str:
rpp/coherence.py:295:    Generate a human-readable description of coherence state.
rpp/coherence.py:298:        result: CoherenceResult to describe
rpp/coherence.py:306:        status = "COMPLETE - Full coherence achieved"
rpp/coherence.py:313:        f"Coherence: {result.score}/{MAX_COHERENCE} ({percentage:.1f}%)\n"
rpp/consent.py:150:    coherence_score: float = 0.0
rpp/consent.py:161:            "coherence_score": self.coherence_score,
rpp/consent.py:174:        """Check if coherence score meets threshold (0.4)."""
rpp/consent.py:175:        return self.coherence_score >= 0.4
rpp/consent.py:301:            # Ethereal zone needs high coherence
rpp/consent.py:308:                    reason="Write to ethereal zone requires coherence >= 0.4",
rpp/consent.py:335:    coherence: float = 0.0,
rpp/consent.py:345:        coherence: Coherence score (0.0-1.0)
rpp/consent.py:363:        coherence_score=coherence,
rpp/consent_header.py:178:        Bytes 14-15: Coherence Window ID (16 bits)
rpp/consent_header.py:206:    coherence_window_id: int = 0        # 16 bits (PMA link)
rpp/consent_header.py:295:        return self.coherence_window_id != 0
rpp/consent_header.py:373:        # Bytes 14-15: Coherence Window ID
rpp/consent_header.py:374:        struct.pack_into('>H', header, OFF_WINDOW_ID, self.coherence_window_id & 0xFFFF)
rpp/consent_header.py:443:        coherence_window_id = struct.unpack_from('>H', data, OFF_WINDOW_ID)[0]
rpp/consent_header.py:458:            coherence_window_id=coherence_window_id,
rpp/consent_header.py:487:        coherence_window_id: int = 0,
rpp/consent_header.py:498:            coherence_window_id: PMA link (0 = none)
rpp/consent_header.py:515:            coherence_window_id=coherence_window_id,
rpp/consent_header.py:550:            f"window={self.coherence_window_id:04X})"
rpp/consent_header.py:568:            'coherence_window_id': f"0x{self.coherence_window_id:04X}",
rpp/consent_header.py:640:        coherence_window_id=0x1A2B,
rpp/continuity.py:12:While crossing, the origin holds a complete copy. Only after coherence is
rpp/continuity.py:29:# T2 coherence times in nanoseconds for spintronic substrates
rpp/continuity.py:33:    0: 25,    # Hot  — spintronic T2 decoherence time
rpp/continuity.py:97:    COPY_AND_COLLECT = 4  # Partial state held at coherence gate; consent unlock required
rpp/continuity.py:181:    # Minimum T2 coherence time destination must provide (nanoseconds).
rpp/continuity.py:192:    # URI hash of last node that confirmed coherence.
rpp/continuity.py:276:    For Shell 0, the returned value is the physical T2 spintronic decoherence
rpp/continuity.py:326:            "Origin receives CoherenceConfirmed from destination, verifies the "
rpp/geometry.py:10:- Self-observation: the state verifies its own coherence geometrically
rpp/geometry.py:129:        coherence_volume: Physical coherence volume (nm³); 0 = software simulation.
rpp/geometry.py:135:    coherence_volume: float = 0.0
rpp/geometry.py:274:    Both strands rotate together — coherence is preserved. The
rpp/geometry.py:371:        coherence_volume=ssv.coherence_volume,
rpp/geometry.py:558:# Self-observation and coherence verification
rpp/geometry.py:561:def verify_self_coherence(tsv: ToroidalStateVector,
rpp/geometry.py:576:            'coherence_score': float — 0.0 (fully incoherent) to 1.0 (perfect).
rpp/geometry.py:582:    coherence_sum = 0.0
rpp/geometry.py:605:            coherence_sum += 1.0 - (drift / (tolerance * PHI_GOLDEN))
rpp/geometry.py:607:    coherence_score = coherence_sum / len(tsv.primary) if tsv.primary else 0.0
rpp/geometry.py:611:        'coherence_score': coherence_score,
rpp/geometry.py:685:    (0.1 radians). Consensus = coherence: no single observer has authority, quorum does.
rpp/geometry.py:723:    to decoherence. Coherence volume scales as the cube root of energy
rpp/geometry.py:739:        New SkyrmionStateVector with increased amplitudes and coherence volume.
rpp/geometry.py:760:        coherence_volume=ssv.coherence_volume * (gain_factor ** (1 / 3)),
rpp/geometry.py:830:        coherence_volume=0.0,
rpp/geometry.py:870:    # Coherence / self-observation
rpp/geometry.py:871:    "verify_self_coherence",
rpp/hnc.py:5:Global coherence orchestrator across all active fragments.
rpp/hnc.py:6:Handles master coherence aggregation, conflict adjudication,
rpp/hnc.py:21:    MAX_COHERENCE,
rpp/hnc.py:35:    DEPHASED = 3     # Lost coherence, attempting recovery
rpp/hnc.py:46:    coherence: int = 0
rpp/hnc.py:47:    """Current coherence score (0-674)."""
rpp/hnc.py:66:        self.coherence = max(0, min(MAX_COHERENCE, self.coherence))
rpp/hnc.py:72:        """Get priority-weighted coherence score."""
rpp/hnc.py:73:        return self.coherence * self.priority
rpp/hnc.py:78:        coefficient = self.coherence / MAX_COHERENCE
rpp/hnc.py:122:    Global coherence orchestrator across all active fragments.
rpp/hnc.py:125:    - Master coherence score aggregation
rpp/hnc.py:135:        self._master_coherence: float = 0.0
rpp/hnc.py:148:        initial_coherence: int = 0,
rpp/hnc.py:151:        Register a new fragment for coherence tracking.
rpp/hnc.py:156:            initial_coherence: Initial coherence score
rpp/hnc.py:164:            coherence=initial_coherence,
rpp/hnc.py:206:    # Coherence Updates
rpp/hnc.py:209:    def update_fragment_coherence(
rpp/hnc.py:212:        coherence: int,
rpp/hnc.py:216:        Update coherence for a specific fragment.
rpp/hnc.py:220:            coherence: New coherence score (0-674)
rpp/hnc.py:230:        fragment.coherence = max(0, min(MAX_COHERENCE, coherence))
rpp/hnc.py:234:        # Update status based on coherence
rpp/hnc.py:255:    # Master Coherence
rpp/hnc.py:259:        """Recalculate master coherence as weighted average."""
rpp/hnc.py:262:            self._master_coherence = 0.0
rpp/hnc.py:269:            self._master_coherence = sum(
rpp/hnc.py:270:                f.coherence * f.priority for f in active
rpp/hnc.py:279:            self._master_coherence = 0.0
rpp/hnc.py:286:    def master_coherence(self) -> float:
rpp/hnc.py:287:        """Get master coherence (weighted average)."""
rpp/hnc.py:288:        return self._master_coherence
rpp/hnc.py:291:    def master_coherence_int(self) -> int:
rpp/hnc.py:292:        """Get master coherence as integer."""
rpp/hnc.py:293:        return int(self._master_coherence)
rpp/hnc.py:307:        """Check if master coherence is above binding threshold."""
rpp/hnc.py:308:        coefficient = self._master_coherence / MAX_COHERENCE
rpp/hnc.py:328:        Uses weighted coherence score (coherence × priority).
rpp/hnc.py:353:                reason=f"Higher weighted coherence ({score1:.1f} vs {score2:.1f})",
rpp/hnc.py:361:                reason=f"Higher weighted coherence ({score2:.1f} vs {score1:.1f})",
rpp/hnc.py:376:                # Conflict if priorities are similar but coherence differs significantly
rpp/hnc.py:378:                    coherence_diff = abs(f1.coherence - f2.coherence)
rpp/hnc.py:379:                    if coherence_diff > MAX_COHERENCE * 0.2:  # >20% difference
rpp/hnc.py:432:    def get_coherence_summary(self) -> dict:
rpp/hnc.py:433:        """Get summary of coherence across all fragments."""
rpp/hnc.py:438:                'master_coherence': 0,
rpp/hnc.py:447:            'master_coherence': self.master_coherence_int,
rpp/hnc.py:455:                    'coherence': f.coherence,
rpp/hnc.py:490:    initial_coherence: int = 0,
rpp/hnc.py:497:        initial_coherence: Initial coherence for all fragments
rpp/hnc.py:504:        hnc.register_fragment(fid, initial_coherence=initial_coherence)
rpp/hrda.py:29:WEIGHT_EEG: Final[float] = 0.30      # Brainwave coherence
rpp/hrda.py:47:        somatic_coherence: 4 bits (0-15) - Overall body-aligned consent
rpp/hrda.py:61:    somatic_coherence: int = 0          # 4 bits (0-15)
rpp/hrda.py:79:        self.somatic_coherence = max(0, min(15, self.somatic_coherence))
rpp/hrda.py:94:            Byte 0: [7:4] somatic_coherence, [3:0] verbal + temporal
rpp/hrda.py:100:        byte0 = ((self.somatic_coherence & 0x0F) << 4) | \
rpp/hrda.py:122:        somatic_coherence = (data[0] >> 4) & 0x0F
rpp/hrda.py:137:            somatic_coherence=somatic_coherence,
rpp/hrda.py:155:            self.somatic_coherence ^
rpp/hrda.py:277:    def compute_somatic_coherence(
rpp/hrda.py:285:        Compute 4-bit somatic coherence from biometric inputs.
rpp/hrda.py:292:            eeg: Brainwave coherence (0.0-1.0)
rpp/hrda.py:297:            Somatic coherence (0-15)
rpp/hrda.py:366:            eeg: Brainwave coherence (0.0-1.0)
rpp/hrda.py:377:        somatic = self.compute_somatic_coherence(hrv, eeg, breath)
rpp/hrda.py:381:            somatic_coherence=somatic,
rpp/hrda.py:383:            complecount_trace=0,  # Set externally based on coherence
rpp/hrda.py:416:        somatic: Somatic coherence (0-15)
rpp/hrda.py:425:        somatic_coherence=somatic,
rpp/hrda.py:441:    return (signals.somatic_coherence, signals.verbal_signal_strength)
rpp/mesh.py:5:Fragment mesh addressing and routing for multi-fragment coherence.
rpp/mesh.py:25:from rpp.ra_constants import MAX_COHERENCE, BINDING_THRESHOLD
rpp/mesh.py:112:    COHERENCE = 1      # Coherence update
rpp/mesh.py:188:    coherence: int = 0
rpp/mesh.py:189:    """Current coherence score."""
rpp/mesh.py:208:        """Check if node coherence is above binding threshold."""
rpp/mesh.py:209:        return (self.coherence / MAX_COHERENCE) >= BINDING_THRESHOLD
rpp/mesh.py:213:        """Get priority-weighted coherence score."""
rpp/mesh.py:214:        return self.coherence * self.priority
rpp/mesh.py:233:    - Coherence-aware routing priorities
rpp/mesh.py:274:        initial_coherence: int = 0,
rpp/mesh.py:283:            initial_coherence: Starting coherence
rpp/mesh.py:296:            coherence=initial_coherence,
rpp/mesh.py:531:    # Coherence Operations
rpp/mesh.py:534:    def update_node_coherence(
rpp/mesh.py:537:        coherence: int,
rpp/mesh.py:541:        Update node coherence and optionally broadcast.
rpp/mesh.py:545:            coherence: New coherence score
rpp/mesh.py:555:        node.coherence = max(0, min(MAX_COHERENCE, coherence))
rpp/mesh.py:561:                message_type=MessageType.COHERENCE,
rpp/mesh.py:562:                payload={'coherence': coherence},
rpp/mesh.py:569:    def get_mesh_coherence(self) -> float:
rpp/mesh.py:571:        Get aggregate mesh coherence (weighted average).
rpp/mesh.py:574:            Weighted average coherence across connected nodes
rpp/mesh.py:585:            n.coherence * n.priority for n in connected
rpp/mesh.py:588:    def get_highest_coherence_node(self) -> Optional[FragmentNode]:
rpp/mesh.py:589:        """Get node with highest weighted coherence score."""
rpp/mesh.py:606:            'mesh_coherence': self.get_mesh_coherence(),
rpp/mesh.py:636:    initial_coherence: int = 0,
rpp/mesh.py:644:        initial_coherence: Initial coherence for all fragments
rpp/mesh.py:651:        mesh.register_fragment(fid, initial_coherence=initial_coherence)
rpp/network.py:102:    t2_ns:              int     # T2 coherence time in ns (0 = software simulation)
rpp/pma.py:4:Temporal-coherence ledger within the SPIRAL protocol.
rpp/pma.py:95:# Coherence Encoding
rpp/pma.py:98:def encode_coherence(normalized: float) -> int:
rpp/pma.py:99:    """Encode 0.0-1.0 coherence to 6-bit field (0-63)."""
rpp/pma.py:103:def decode_coherence(score: int) -> float:
rpp/pma.py:104:    """Decode 6-bit coherence (0-63) to 0.0-1.0."""
rpp/pma.py:136:        window_id:          12 bits - Links to coherence_window_id
rpp/pma.py:141:        coherence_score:     6 bits - PMQ/scalar coherence (0-63)
rpp/pma.py:153:    coherence_score: int     # 6 bits (0-63)
rpp/pma.py:163:        if not 0 <= self.coherence_score <= 63:
rpp/pma.py:164:            raise ValueError(f"coherence_score must be 0-63, got {self.coherence_score}")
rpp/pma.py:176:    def coherence_normalized(self) -> float:
rpp/pma.py:177:        """Get coherence as 0.0-1.0."""
rpp/pma.py:178:        return decode_coherence(self.coherence_score)
rpp/pma.py:201:            Byte 13:   [consent_state(2)] [complecount_score(5)] [coherence_hi(1)]
rpp/pma.py:202:            Byte 14:   [coherence_lo(5)] [payload_type_hi(3)]
rpp/pma.py:224:        # Byte 13: consent_state(2) + complecount_score(5) + coherence_hi(1)
rpp/pma.py:227:        coh_hi = (self.coherence_score >> 5) & 0x01
rpp/pma.py:230:        # Byte 14: coherence_lo(5) + payload_type_hi(3)
rpp/pma.py:231:        coh_lo = (self.coherence_score & 0x1F) << 3
rpp/pma.py:289:        coherence_score = (coh_hi << 5) | coh_lo
rpp/pma.py:303:            coherence_score=coherence_score,
rpp/pma.py:318:        coherence: float,
rpp/pma.py:327:            window_id: Coherence window ID from header
rpp/pma.py:330:            coherence: Coherence score 0.0-1.0
rpp/pma.py:344:            coherence_score=encode_coherence(coherence),
rpp/pma.py:357:            f"θ={addr.theta}, coherence={self.coherence_normalized:.2f}, "
rpp/pma.py:371:            'coherence_score': self.coherence_normalized,
rpp/pma.py:530:    Provides allocate/get/put interface for coherence windows.
rpp/pma.py:553:        coherence: float,
rpp/pma.py:566:            coherence=coherence,
rpp/pma.py:606:        coherence=0.85,
rpp/pma.py:613:    print(f"  Coherence: {record.coherence_normalized:.3f}")
rpp/pma.py:629:    assert decoded.coherence_score == record.coherence_score
rpp/pma.py:646:            coherence=0.7 + i * 0.05,
rpp/ra_constants.py:5:Mathematical foundation for SPIRAL protocol addressing and coherence.
rpp/ra_constants.py:21:# Golden Ratio - coherence attractor, entropy modulation
rpp/ra_constants.py:23:"""Golden Ratio (φ). Governs coherence thresholds and harmonic scaling."""
rpp/ra_constants.py:39:"""Ankh constant (𝔄). Master harmonic for coherence completion weight."""
rpp/ra_constants.py:64:# Coherence Constants
rpp/ra_constants.py:67:MAX_COHERENCE: Final[int] = 674
rpp/ra_constants.py:68:"""Maximum coherence score (GREEN_PHI_SCALED + ANKH_SCALED = 165 + 509)."""
rpp/ra_constants.py:70:BINDING_THRESHOLD: Final[float] = ALPHA_INV_SCALED / MAX_COHERENCE
rpp/ra_constants.py:162:        "MAX_COHERENCE": {
rpp/ra_constants.py:163:            "value": MAX_COHERENCE,
rpp/ra_constants.py:164:            "digital_root": digital_root(MAX_COHERENCE),
rpp/ra_constants.py:166:            "valid": digital_root(MAX_COHERENCE) == 8,
rpp/resolver.py:174:                coherence_score=context.get("coherence_score", 0.0),
rpp/resolver.py:184:                coherence=context.get("coherence_score", 0.0),
rpp/resolver.py:194:                coherence_score=consent_ctx.coherence_score,
rpp/sector_router.py:29:    VOID is a special state accessible only when coherence = 0.
rpp/sector_router.py:38:    VOID = 0       # Reset/phase collapse (coherence=0 only)
rpp/sector_router.py:131:    coherence: int = 674,
rpp/sector_router.py:139:        coherence: Current coherence score (0-674)
rpp/sector_router.py:145:        - VOID sector requires coherence = 0
rpp/sector_router.py:148:    # VOID is only accessible at coherence = 0
rpp/sector_router.py:150:        return coherence == 0
rpp/sector_router.py:281:    coherence: int = 674,
rpp/sector_router.py:290:        coherence: Current coherence score (0-674)
rpp/sector_router.py:298:        if coherence == 0:
rpp/sector_router.py:303:                reason="coherence=0 enables VOID access",
rpp/sector_router.py:312:                    reason=f"VOID requires coherence=0, redirected to {fallback.name}",
rpp/sector_router.py:318:                reason="VOID requires coherence=0",
rpp/sector_router.py:322:    if can_access_sector(consent_state, requested_sector, coherence):
rpp/transitions.py:284:    When coherence drops below threshold, waits KHAT_DURATION (12 cycles)
rpp/transitions.py:294:            threshold: Coherence threshold for fallback (default: 137)
rpp/transitions.py:315:    def update(self, coherence: int) -> bool:
rpp/transitions.py:317:        Update fallback gate with current coherence.
rpp/transitions.py:320:            coherence: Current coherence score
rpp/transitions.py:325:        if coherence < self._threshold:
rpp/transitions.py:464:        coherence: int,
rpp/transitions.py:472:            coherence: Current coherence score
rpp/transitions.py:481:        fallback_trigger = self._fallback_gate.update(coherence)
```

## sector

```text
rpp/__init__.py:20:    ThetaSector,
rpp/__init__.py:24:    create_from_sector,
rpp/__init__.py:27:    same_sector,
rpp/__init__.py:28:    adjacent_sectors,
rpp/__init__.py:127:    "ThetaSector",
rpp/__init__.py:131:    "create_from_sector",
rpp/__init__.py:134:    "same_sector",
rpp/__init__.py:135:    "adjacent_sectors",
rpp/address.py:11:  [25:17] Theta (9 bits, 0-511) — data type sector (continuous)
rpp/address.py:51:        theta: Angular sector (0-511)
rpp/address.py:97:    def sector_name(self) -> str:
rpp/address.py:98:        """Return canonical sector name for theta."""
rpp/address.py:141:        theta: Angular sector (0-511)
rpp/address.py:193:        theta: Angular sector (0-511)
rpp/address_canonical.py:83:class ThetaSector(IntEnum):
rpp/address_canonical.py:85:    Semantic sectors mapped to Repitan ranges.
rpp/address_canonical.py:104:    def from_theta(cls, theta: int) -> ThetaSector:
rpp/address_canonical.py:105:        """Map theta value to semantic sector."""
rpp/address_canonical.py:128:        """Get the Repitan range for this sector."""
rpp/address_canonical.py:143:        """Get center Repitan for this sector."""
rpp/address_canonical.py:219:        theta: Repitan index 1-27 (semantic sector)
rpp/address_canonical.py:351:    def sector(self) -> ThetaSector:
rpp/address_canonical.py:352:        """Get semantic sector from theta."""
rpp/address_canonical.py:353:        return ThetaSector.from_theta(self.theta)
rpp/address_canonical.py:449:        sector = self.sector.name
rpp/address_canonical.py:453:        return f"RPP(θ={self.theta}[{sector}], φ={rac}, h={tier}, r={self.radius:.2f})"
rpp/address_canonical.py:498:def create_from_sector(
rpp/address_canonical.py:499:    sector: ThetaSector,
rpp/address_canonical.py:505:    Create address from semantic sector.
rpp/address_canonical.py:507:    Uses the center Repitan of the sector range.
rpp/address_canonical.py:509:    theta = sector.center_repitan
rpp/address_canonical.py:511:        theta = 14  # Default to DREAM center for invalid sectors
rpp/address_canonical.py:557:def same_sector(a: RPPAddress, b: RPPAddress) -> bool:
rpp/address_canonical.py:558:    """Check if two addresses are in the same semantic sector."""
rpp/address_canonical.py:559:    return a.sector == b.sector
rpp/address_canonical.py:562:def adjacent_sectors(a: RPPAddress, b: RPPAddress) -> bool:
rpp/address_canonical.py:563:    """Check if two addresses are in adjacent sectors."""
rpp/address_canonical.py:564:    # Sector adjacency based on Ra topology
rpp/address_canonical.py:566:        ThetaSector.CORE: {ThetaSector.GENE, ThetaSector.MEMORY},
rpp/address_canonical.py:567:        ThetaSector.GENE: {ThetaSector.CORE, ThetaSector.GUARDIAN, ThetaSector.BRIDGE},
rpp/address_canonical.py:568:        ThetaSector.MEMORY: {ThetaSector.CORE, ThetaSector.WITNESS, ThetaSector.BRIDGE},
rpp/address_canonical.py:569:        ThetaSector.WITNESS: {ThetaSector.MEMORY, ThetaSector.BRIDGE},
rpp/address_canonical.py:570:        ThetaSector.DREAM: {ThetaSector.BRIDGE, ThetaSector.SHADOW},
rpp/address_canonical.py:571:        ThetaSector.BRIDGE: {ThetaSector.GENE, ThetaSector.MEMORY, ThetaSector.WITNESS,
rpp/address_canonical.py:572:                            ThetaSector.GUARDIAN, ThetaSector.DREAM},
rpp/address_canonical.py:573:        ThetaSector.GUARDIAN: {ThetaSector.GENE, ThetaSector.BRIDGE},
rpp/address_canonical.py:574:        ThetaSector.SHADOW: {ThetaSector.DREAM},
rpp/address_canonical.py:577:    return b.sector in adjacency.get(a.sector, set())
rpp/address_canonical.py:690:    print("\n  Memory sector address:")
rpp/address_canonical.py:696:    # Create from sector
rpp/address_canonical.py:697:    addr2 = create_from_sector(ThetaSector.GUARDIAN, phi=2, omega=1, radius=0.9)
rpp/address_canonical.py:698:    print("\n  Guardian sector address:")
rpp/address_canonical.py:704:    print(f"  Same sector: {same_sector(addr1, addr2)}")
rpp/address_canonical.py:705:    print(f"  Adjacent: {adjacent_sectors(addr1, addr2)}")
rpp/cli.py:105:            sector_name = t(f"sector_{addr.sector_name.lower()}", lang)
rpp/cli.py:129:                    sector_name, grounding, fancy
rpp/cli.py:133:                output(f"  {t('theta', lang)}: {addr.theta} ({sector_name})")
rpp/cli.py:163:            sector_name = t(f"sector_{addr.sector_name.lower()}", lang)
rpp/cli.py:186:                    sector_name, grounding, fancy
rpp/cli.py:190:                output(f"  {t('theta', lang)}: {addr.theta} ({sector_name})")
rpp/cli.py:373:    output("  * WHAT type it is (Theta: semantic sector)")
rpp/cli.py:416:    # Section 4: Theta Sectors
rpp/cli.py:418:    output("  SECTION 4: Theta Sectors (Semantic Classification)")
rpp/cli.py:543:    encode_parser.add_argument("--theta", "-t", type=int, required=True, help=f"Theta sector (0-{MAX_THETA})")
rpp/consent.py:8:- DIMINISHED_CONSENT: Read-only, some sectors blocked
rpp/consent.py:12:Sector Requirements:
rpp/consent.py:52:class Sector(Enum):
rpp/consent.py:54:    Semantic sectors with consent requirements.
rpp/consent.py:56:    Based on theta ranges (0-511 divided into 8 sectors of 64 each).
rpp/consent.py:69:    def from_theta(cls, theta: int) -> "Sector":
rpp/consent.py:70:        """Get sector from theta value."""
rpp/consent.py:90:        """Get sensitivity level for sector."""
rpp/consent.py:91:        high = {Sector.GENE, Sector.GUARDIAN, Sector.META}
rpp/consent.py:92:        medium = {Sector.MEMORY, Sector.EMERGENCE}
rpp/consent.py:102:        """Check if sector requires full consent for writes."""
rpp/consent.py:188:    sector: Sector
rpp/consent.py:198:            "sector": self.sector.value,
rpp/consent.py:215:        theta: Angular sector (0-511)
rpp/consent.py:223:    sector = Sector.from_theta(theta)
rpp/consent.py:232:                sector=sector,
rpp/consent.py:240:                sector=sector,
rpp/consent.py:252:                sector=sector,
rpp/consent.py:261:                sector=sector,
rpp/consent.py:267:    # Diminished consent: read-only, excludes high-sensitivity sectors
rpp/consent.py:273:                sector=sector,
rpp/consent.py:278:        if sector.sensitivity == "high":
rpp/consent.py:282:                sector=sector,
rpp/consent.py:284:                reason=f"Diminished consent: {sector.value} sector requires full consent",
rpp/consent.py:288:    # Full consent: check sector and zone requirements for writes
rpp/consent.py:291:            # High-sensitivity sectors need verified identity
rpp/consent.py:292:            if sector.requires_full_consent_for_write and not context.is_verified:
rpp/consent.py:296:                    sector=sector,
rpp/consent.py:298:                    reason=f"Write to {sector.value} requires verified identity",
rpp/consent.py:306:                    sector=sector,
rpp/consent.py:317:                    sector=sector,
rpp/consent.py:326:        sector=sector,
rpp/consent.py:328:        reason=f"{operation} permitted in {sector.value}/{zone.value}",
rpp/consent_header.py:67:    FULL_CONSENT = 0       # Full operation, all sectors accessible
rpp/consent_header.py:70:    SUSPENDED_CONSENT = 3  # Blocked, minimal sectors
rpp/consent_header.py:624:    from rpp.address_canonical import ThetaSector, create_from_sector
rpp/consent_header.py:630:    addr = create_from_sector(ThetaSector.MEMORY, phi=3, omega=2, radius=0.75)
rpp/extended.py:53:        theta: Angular sector, fine precision (0-1048575)
rpp/extended.py:146:    def sector_name(self) -> str:
rpp/extended.py:147:        """Return canonical sector name for theta (using core resolution)."""
rpp/extended.py:192:        theta: Angular sector, fine (0-1048575)
rpp/extended.py:254:        theta: Angular sector, fine (0-1048575)
rpp/i18n.py:54:        # Sector names
rpp/i18n.py:55:        "sector_gene": "Gene",
rpp/i18n.py:56:        "sector_memory": "Memory",
rpp/i18n.py:57:        "sector_witness": "Witness",
rpp/i18n.py:58:        "sector_dream": "Dream",
rpp/i18n.py:59:        "sector_bridge": "Bridge",
rpp/i18n.py:60:        "sector_guardian": "Guardian",
rpp/i18n.py:61:        "sector_emergence": "Emergence",
rpp/i18n.py:62:        "sector_meta": "Meta",
rpp/i18n.py:127:        # Sector names
rpp/i18n.py:128:        "sector_gene": "الجين",
rpp/i18n.py:129:        "sector_memory": "الذاكرة",
rpp/i18n.py:130:        "sector_witness": "الشاهد",
rpp/i18n.py:131:        "sector_dream": "الحلم",
rpp/i18n.py:132:        "sector_bridge": "الجسر",
rpp/i18n.py:133:        "sector_guardian": "الحارس",
rpp/i18n.py:134:        "sector_emergence": "الظهور",
rpp/i18n.py:135:        "sector_meta": "ميتا",
rpp/i18n.py:200:        # Sector names
rpp/i18n.py:201:        "sector_gene": "الجين",
rpp/i18n.py:202:        "sector_memory": "الذاكرة",
rpp/i18n.py:203:        "sector_witness": "الشاهد",
rpp/i18n.py:204:        "sector_dream": "الحلم",
rpp/i18n.py:205:        "sector_bridge": "الجسر",
rpp/i18n.py:206:        "sector_guardian": "الحارس",
rpp/i18n.py:207:        "sector_emergence": "الظهور",
rpp/i18n.py:208:        "sector_meta": "ميتا",
rpp/i18n.py:273:        # Sector names
rpp/i18n.py:274:        "sector_gene": "Gen",
rpp/i18n.py:275:        "sector_memory": "Memoria",
rpp/i18n.py:276:        "sector_witness": "Testigo",
rpp/i18n.py:277:        "sector_dream": "Sueño",
rpp/i18n.py:278:        "sector_bridge": "Puente",
rpp/i18n.py:279:        "sector_guardian": "Guardián",
rpp/i18n.py:280:        "sector_emergence": "Emergencia",
rpp/i18n.py:281:        "sector_meta": "Meta",
rpp/i18n.py:346:        # Sector names
rpp/i18n.py:347:        "sector_gene": "Ген",
rpp/i18n.py:348:        "sector_memory": "Память",
rpp/i18n.py:349:        "sector_witness": "Свидетель",
rpp/i18n.py:350:        "sector_dream": "Сон",
rpp/i18n.py:351:        "sector_bridge": "Мост",
rpp/i18n.py:352:        "sector_guardian": "Страж",
rpp/i18n.py:353:        "sector_emergence": "Возникновение",
rpp/i18n.py:354:        "sector_meta": "Мета",
rpp/memory_bridge.py:46:# Theta sectors for memory classification (matches spec/SEMANTICS.md)
rpp/memory_bridge.py:126:            theta:   Semantic sector [0-511]. Use THETA_* constants.
rpp/mesh.py:10:- Sector-scoped multicast
rpp/mesh.py:26:from rpp.sector_router import RoutableSector
rpp/mesh.py:39:    SECTOR = 3       # All fragments in a sector
rpp/mesh.py:51:    Address format: SOUL_ID.FRAGMENT_ID.SECTOR
rpp/mesh.py:61:    sector: RoutableSector = RoutableSector.BRIDGE
rpp/mesh.py:62:    """Current sector assignment."""
rpp/mesh.py:66:        return f"{self.soul_id}.{self.fragment_id}.{self.sector.name}"
rpp/mesh.py:74:            address_str: Address string in format "soul.frag.SECTOR"
rpp/mesh.py:83:        soul_id, fragment_id, sector_name = parts
rpp/mesh.py:85:            sector = RoutableSector[sector_name]
rpp/mesh.py:89:        return cls(soul_id=soul_id, fragment_id=fragment_id, sector=sector)
rpp/mesh.py:100:    def same_sector(self, other: FragmentAddress) -> bool:
rpp/mesh.py:101:        """Check if addresses are in same sector."""
rpp/mesh.py:102:        return self.sector == other.sector
rpp/mesh.py:117:    SECTOR_CHANGE = 6  # Sector routing change
rpp/mesh.py:232:    - Sector-based grouping
rpp/mesh.py:272:        sector: RoutableSector = RoutableSector.BRIDGE,
rpp/mesh.py:281:            sector: Initial sector assignment
rpp/mesh.py:291:            sector=sector,
rpp/mesh.py:327:    def get_nodes_in_sector(self, sector: RoutableSector) -> List[FragmentNode]:
rpp/mesh.py:328:        """Get all nodes in a specific sector."""
rpp/mesh.py:331:            if n.address.sector == sector and n.connected
rpp/mesh.py:440:        elif destination.startswith("SECTOR:"):
rpp/mesh.py:441:            address_type = AddressType.SECTOR
rpp/mesh.py:486:        elif message.address_type == AddressType.SECTOR:
rpp/mesh.py:487:            # Parse sector from destination
rpp/mesh.py:488:            sector_name = str(message.destination).replace("SECTOR:", "")
rpp/mesh.py:490:                sector = RoutableSector[sector_name]
rpp/mesh.py:491:                for node in self.get_nodes_in_sector(sector):
rpp/mesh.py:607:            'sectors': {
rpp/mesh.py:608:                sector.name: len(self.get_nodes_in_sector(sector))
rpp/mesh.py:609:                for sector in RoutableSector
rpp/network.py:41:THETA_SECTORS              = 8    # 512 theta values / 8 sectors = 64 per sector
rpp/network.py:42:MIN_HOT_NODES_PER_SECTOR   = 3    # minimum for backbone redundancy
rpp/network.py:70:# Internal — gap detection threshold (same value as MIN_HOT_NODES_PER_SECTOR)
rpp/network.py:71:_GAP_THRESHOLD = MIN_HOT_NODES_PER_SECTOR
rpp/network.py:96:    theta:              int     # angular sector [0-511] — data type this node routes
rpp/network.py:142:    theta:           int     # node's angular sector
rpp/network.py:175:    theta_distance:  int    # angular distance from my sector to requested theta
rpp/network.py:187:    Propagation rule: forward to all neighbors where any(theta in theta_sectors).
rpp/network.py:193:    theta_sectors:    list   # which theta sectors are affected
rpp/network.py:202:    Sent by Hot nodes to Warm nodes in under-covered theta sectors.
rpp/network.py:208:    target_sector:      int    # theta sector index needing coverage (0-7)
rpp/network.py:209:    current_coverage:   int    # how many Hot nodes are in this sector
rpp/network.py:389:    Return theta sector indices with insufficient Hot node coverage.
rpp/network.py:391:    Sector i covers theta values in [i*64, (i+1)*64 - 1].
rpp/network.py:392:    A sector is considered a gap when it has fewer than MIN_HOT_NODES_PER_SECTOR
rpp/network.py:399:        List of sector indices (0-7) that are under-covered.
rpp/network.py:402:    sector_counts = [0] * THETA_SECTORS
rpp/network.py:405:        sector = node.theta // 64
rpp/network.py:406:        sector_counts[sector] += 1
rpp/network.py:408:    return [i for i, count in enumerate(sector_counts) if count < _GAP_THRESHOLD]
rpp/network.py:418:    affected_sectors: int,
rpp/network.py:433:        affected_sectors: Number of theta sectors affected (not used in current
rpp/network.py:498:    "THETA_SECTORS",
rpp/network.py:499:    "MIN_HOT_NODES_PER_SECTOR",
rpp/pma.py:591:    from rpp.address_canonical import create_from_sector, ThetaSector
rpp/pma.py:598:    addr = create_from_sector(ThetaSector.MEMORY, phi=3, omega=2, radius=0.75)
rpp/pma.py:641:        addr = create_from_sector(ThetaSector.MEMORY, phi=3, omega=i % 5, radius=0.5 + i * 0.1)
rpp/resolver.py:17:- Checks sector sensitivity and grounding zone
rpp/resolver.py:78:    - Theta (sector - determines consent requirements)
rpp/resolver.py:162:        - Sector sensitivity (gene, guardian, meta = high)
rpp/resolver.py:223:        return f"{backend}://{addr.sector_name.lower()}/{addr.grounding_level.lower()}/{addr.theta}_{addr.phi}_{addr.harmonic}"
rpp/sector_router.py:2:Sector Router Module
rpp/sector_router.py:5:Consent-gated theta sector routing for SPIRAL protocol.
rpp/sector_router.py:6:Implements the 8-sector model with VOID state and consent-based access control.
rpp/sector_router.py:8:Reference: SPIRAL-Architecture.md Section 4 (Theta Sectors)
rpp/sector_router.py:21:# Theta Sector Enum (Extended with VOID)
rpp/sector_router.py:24:class RoutableSector(IntEnum):
rpp/sector_router.py:26:    8 semantic theta sectors plus VOID for phase collapse.
rpp/sector_router.py:28:    The sectors form a chambered nautilus geometry with consent-gated access.
rpp/sector_router.py:31:    Sector Access by Consent State:
rpp/sector_router.py:32:        FULL_CONSENT: All sectors (0-8)
rpp/sector_router.py:50:# Sector Access Matrix
rpp/sector_router.py:53:# Define which sectors are accessible for each consent state
rpp/sector_router.py:54:SECTOR_ACCESS: Final[Dict[ConsentState, FrozenSet[RoutableSector]]] = {
rpp/sector_router.py:56:        RoutableSector.VOID,
rpp/sector_router.py:57:        RoutableSector.CORE,
rpp/sector_router.py:58:        RoutableSector.GENE,
rpp/sector_router.py:59:        RoutableSector.MEMORY,
rpp/sector_router.py:60:        RoutableSector.WITNESS,
rpp/sector_router.py:61:        RoutableSector.DREAM,
rpp/sector_router.py:62:        RoutableSector.BRIDGE,
rpp/sector_router.py:63:        RoutableSector.GUARDIAN,
rpp/sector_router.py:64:        RoutableSector.SHADOW,
rpp/sector_router.py:67:        RoutableSector.MEMORY,
rpp/sector_router.py:68:        RoutableSector.WITNESS,
rpp/sector_router.py:69:        RoutableSector.BRIDGE,
rpp/sector_router.py:70:        RoutableSector.GUARDIAN,
rpp/sector_router.py:73:        RoutableSector.BRIDGE,
rpp/sector_router.py:74:        RoutableSector.GUARDIAN,
rpp/sector_router.py:75:        RoutableSector.SHADOW,
rpp/sector_router.py:78:        RoutableSector.BRIDGE,
rpp/sector_router.py:79:        RoutableSector.GUARDIAN,
rpp/sector_router.py:82:        RoutableSector.GUARDIAN,  # Lockdown to GUARDIAN only
rpp/sector_router.py:86:# Sectors that are always accessible (universal access)
rpp/sector_router.py:87:UNIVERSAL_SECTORS: Final[FrozenSet[RoutableSector]] = frozenset([
rpp/sector_router.py:88:    RoutableSector.BRIDGE,
rpp/sector_router.py:89:    RoutableSector.GUARDIAN,
rpp/sector_router.py:92:# Sectors requiring full consent
rpp/sector_router.py:93:RESTRICTED_SECTORS: Final[FrozenSet[RoutableSector]] = frozenset([
rpp/sector_router.py:94:    RoutableSector.CORE,
rpp/sector_router.py:95:    RoutableSector.GENE,
rpp/sector_router.py:96:    RoutableSector.DREAM,
rpp/sector_router.py:101:# Sector Properties
rpp/sector_router.py:104:# Sector sensitivity levels (higher = more restricted)
rpp/sector_router.py:105:SECTOR_SENSITIVITY: Final[Dict[RoutableSector, int]] = {
rpp/sector_router.py:106:    RoutableSector.VOID: 0,      # Special state, no sensitivity
rpp/sector_router.py:107:    RoutableSector.BRIDGE: 1,    # Universal access
rpp/sector_router.py:108:    RoutableSector.GUARDIAN: 1,  # Universal access (fallback)
rpp/sector_router.py:109:    RoutableSector.SHADOW: 2,    # Diminished+ access
rpp/sector_router.py:110:    RoutableSector.MEMORY: 3,    # Attentive+ access
rpp/sector_router.py:111:    RoutableSector.WITNESS: 3,   # Attentive+ access
rpp/sector_router.py:112:    RoutableSector.DREAM: 4,     # Full consent required
rpp/sector_router.py:113:    RoutableSector.GENE: 5,      # Full consent required (biological)
rpp/sector_router.py:114:    RoutableSector.CORE: 5,      # Full consent required (identity)
rpp/sector_router.py:117:# Fallback sector chain (when access denied, try these in order)
rpp/sector_router.py:118:FALLBACK_CHAIN: Final[tuple[RoutableSector, ...]] = (
rpp/sector_router.py:119:    RoutableSector.GUARDIAN,
rpp/sector_router.py:120:    RoutableSector.BRIDGE,
rpp/sector_router.py:128:def can_access_sector(
rpp/sector_router.py:130:    sector: RoutableSector,
rpp/sector_router.py:134:    Check if a sector is accessible given the consent state.
rpp/sector_router.py:138:        sector: Target sector to access
rpp/sector_router.py:142:        True if sector is accessible
rpp/sector_router.py:145:        - VOID sector requires coherence = 0
rpp/sector_router.py:149:    if sector == RoutableSector.VOID:
rpp/sector_router.py:153:    if sector == RoutableSector.GUARDIAN:
rpp/sector_router.py:156:    # Check sector access matrix
rpp/sector_router.py:157:    accessible = SECTOR_ACCESS.get(consent_state, frozenset())
rpp/sector_router.py:158:    return sector in accessible
rpp/sector_router.py:161:def get_accessible_sectors(consent_state: ConsentState) -> FrozenSet[RoutableSector]:
rpp/sector_router.py:163:    Get all sectors accessible for a given consent state.
rpp/sector_router.py:169:        Frozenset of accessible sectors
rpp/sector_router.py:171:    return SECTOR_ACCESS.get(consent_state, frozenset([RoutableSector.GUARDIAN]))
rpp/sector_router.py:174:def get_fallback_sector(
rpp/sector_router.py:176:    requested_sector: RoutableSector,
rpp/sector_router.py:177:) -> RoutableSector:
rpp/sector_router.py:179:    Get fallback sector when requested sector is not accessible.
rpp/sector_router.py:183:        requested_sector: Originally requested sector
rpp/sector_router.py:186:        Fallback sector (GUARDIAN or BRIDGE)
rpp/sector_router.py:188:    if can_access_sector(consent_state, requested_sector):
rpp/sector_router.py:189:        return requested_sector
rpp/sector_router.py:192:    accessible = get_accessible_sectors(consent_state)
rpp/sector_router.py:198:    return RoutableSector.GUARDIAN
rpp/sector_router.py:201:def get_sector_sensitivity(sector: RoutableSector) -> int:
rpp/sector_router.py:203:    Get sensitivity level for a sector (0-5).
rpp/sector_router.py:205:    Higher values indicate more restricted sectors.
rpp/sector_router.py:208:        sector: Target sector
rpp/sector_router.py:213:    return SECTOR_SENSITIVITY.get(sector, 5)
rpp/sector_router.py:216:def requires_full_consent(sector: RoutableSector) -> bool:
rpp/sector_router.py:218:    Check if sector requires FULL_CONSENT for access.
rpp/sector_router.py:221:        sector: Target sector
rpp/sector_router.py:226:    return sector in RESTRICTED_SECTORS
rpp/sector_router.py:229:def is_universal_access(sector: RoutableSector) -> bool:
rpp/sector_router.py:231:    Check if sector has universal access (all consent states).
rpp/sector_router.py:234:        sector: Target sector
rpp/sector_router.py:239:    return sector in UNIVERSAL_SECTORS
rpp/sector_router.py:247:    """Result of a sector routing decision."""
rpp/sector_router.py:249:    __slots__ = ('granted', 'sector', 'original_sector', 'reason')
rpp/sector_router.py:254:        sector: RoutableSector,
rpp/sector_router.py:255:        original_sector: RoutableSector,
rpp/sector_router.py:259:        self.sector = sector
rpp/sector_router.py:260:        self.original_sector = original_sector
rpp/sector_router.py:265:        """Check if request was redirected to fallback sector."""
rpp/sector_router.py:266:        return self.sector != self.original_sector
rpp/sector_router.py:272:                f"RoutingDecision({status}: {self.original_sector.name} → "
rpp/sector_router.py:273:                f"{self.sector.name}, reason={self.reason!r})"
rpp/sector_router.py:275:        return f"RoutingDecision({status}: {self.sector.name}, reason={self.reason!r})"
rpp/sector_router.py:278:def route_to_sector(
rpp/sector_router.py:280:    requested_sector: RoutableSector,
rpp/sector_router.py:285:    Make a routing decision for sector access.
rpp/sector_router.py:289:        requested_sector: Desired sector
rpp/sector_router.py:297:    if requested_sector == RoutableSector.VOID:
rpp/sector_router.py:301:                sector=RoutableSector.VOID,
rpp/sector_router.py:302:                original_sector=RoutableSector.VOID,
rpp/sector_router.py:307:                fallback = get_fallback_sector(consent_state, requested_sector)
rpp/sector_router.py:310:                    sector=fallback,
rpp/sector_router.py:311:                    original_sector=RoutableSector.VOID,
rpp/sector_router.py:316:                sector=requested_sector,
rpp/sector_router.py:317:                original_sector=requested_sector,
rpp/sector_router.py:322:    if can_access_sector(consent_state, requested_sector, coherence):
rpp/sector_router.py:325:            sector=requested_sector,
rpp/sector_router.py:326:            original_sector=requested_sector,
rpp/sector_router.py:327:            reason=f"{consent_state.name} grants access to {requested_sector.name}",
rpp/sector_router.py:332:        fallback = get_fallback_sector(consent_state, requested_sector)
rpp/sector_router.py:335:            sector=fallback,
rpp/sector_router.py:336:            original_sector=requested_sector,
rpp/sector_router.py:338:                f"{consent_state.name} denies {requested_sector.name}, "
rpp/sector_router.py:346:        sector=requested_sector,
rpp/sector_router.py:347:        original_sector=requested_sector,
rpp/sector_router.py:348:        reason=f"{consent_state.name} denies access to {requested_sector.name}",
rpp/sector_router.py:353:# Sector Conversion Utilities
rpp/sector_router.py:356:def from_legacy_sector(legacy_value: int) -> RoutableSector:
rpp/sector_router.py:358:    Convert legacy ThetaSector value (0-7) to RoutableSector (1-8).
rpp/sector_router.py:366:        legacy_value: Legacy ThetaSector value (0-7)
rpp/sector_router.py:369:        Corresponding RoutableSector
rpp/sector_router.py:372:        raise ValueError(f"Legacy sector must be 0-7, got {legacy_value}")
rpp/sector_router.py:373:    return RoutableSector(legacy_value + 1)
rpp/sector_router.py:376:def to_legacy_sector(sector: RoutableSector) -> int:
rpp/sector_router.py:378:    Convert RoutableSector to legacy ThetaSector value.
rpp/sector_router.py:381:        sector: RoutableSector value
rpp/sector_router.py:384:        Legacy ThetaSector value (0-7), or -1 for VOID
rpp/sector_router.py:387:        ValueError: If sector is VOID (no legacy equivalent)
rpp/sector_router.py:389:    if sector == RoutableSector.VOID:
rpp/sector_router.py:391:    return sector.value - 1
rpp/transitions.py:355:    Locks system to GUARDIAN sector only.
rpp/visual.py:83:        sector = "Gene"
rpp/visual.py:85:        sector = "Memory"
rpp/visual.py:87:        sector = "Witness"
rpp/visual.py:89:        sector = "Dream"
rpp/visual.py:91:        sector = "Bridge"
rpp/visual.py:93:        sector = "Guardian"
rpp/visual.py:95:        sector = "Emergence"
rpp/visual.py:97:        sector = "Meta"
rpp/visual.py:111:    sector_val = _c(sector, "blue", fancy)
rpp/visual.py:123:        f"|      | {shell_val:^8} | {sector_val:^8} | {ground_val:^8} |                    |",
rpp/visual.py:251:    Generate ASCII representation of theta sectors as a wheel.
rpp/visual.py:254:    Shows the 8 semantic sectors with the active one highlighted.
rpp/visual.py:256:    sectors = [
rpp/visual.py:267:    # Find active sector
rpp/visual.py:269:    for i, (start, end, name) in enumerate(sectors):
rpp/visual.py:276:    for i, (start, end, name) in enumerate(sectors):
rpp/visual.py:283:    header = f"Theta Sector: {theta}/511"
rpp/visual.py:351:def address_mini(addr_hex: str, shell_name: str, sector: str,
rpp/visual.py:363:        _c(sector, "blue", fancy),
```
