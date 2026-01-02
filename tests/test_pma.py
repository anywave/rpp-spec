"""
PMA Module Tests

Tests for Phase Memory Anchor v1.1 (18-byte compact format)
"""

import pytest
from rpp.pma import (
    PMARecord,
    PMABuffer,
    PMAStore,
    ConsentState,
    PayloadType,
    encode_coherence,
    decode_coherence,
    encode_timestamp,
    decode_timestamp,
    PMA_RECORD_SIZE,
)
from rpp.address_canonical import (
    create_from_sector,
    ThetaSector,
)


class TestPMAConstants:
    """Test PMA constants match spec."""
    
    def test_record_size(self):
        """Record should be exactly 18 bytes."""
        assert PMA_RECORD_SIZE == 18
    
    def test_record_bits(self):
        """Record should be 144 bits."""
        from rpp.pma import PMA_RECORD_BITS
        assert PMA_RECORD_BITS == 144


class TestCoherenceEncoding:
    """Test coherence score encoding."""
    
    def test_encode_zero(self):
        """Zero coherence should encode to 0."""
        assert encode_coherence(0.0) == 0
    
    def test_encode_one(self):
        """Full coherence should encode to 63."""
        assert encode_coherence(1.0) == 63
    
    def test_encode_half(self):
        """Half coherence should encode to ~32."""
        encoded = encode_coherence(0.5)
        assert 31 <= encoded <= 32
    
    def test_decode_roundtrip(self):
        """Encode/decode should be close."""
        for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
            encoded = encode_coherence(val)
            decoded = decode_coherence(encoded)
            assert abs(decoded - val) < 0.02


class TestTimestampEncoding:
    """Test nanosecond timestamp encoding."""
    
    def test_encode_simple(self):
        """Simple timestamp should encode correctly."""
        ts = encode_timestamp(1000, 500000000)  # 1000s + 0.5s
        secs, nanos = decode_timestamp(ts)
        assert secs == 1000
        assert nanos == 500000000
    
    def test_encode_zero(self):
        """Zero timestamp should work."""
        ts = encode_timestamp(0, 0)
        secs, nanos = decode_timestamp(ts)
        assert secs == 0
        assert nanos == 0
    
    def test_encode_max_nanos(self):
        """Max nanoseconds (999999999) should work."""
        ts = encode_timestamp(100, 999999999)
        secs, nanos = decode_timestamp(ts)
        assert secs == 100
        assert nanos == 999999999


class TestPMARecordCreation:
    """Test PMA record creation."""
    
    def test_create_basic(self):
        """Basic creation should work."""
        addr = create_from_sector(ThetaSector.MEMORY)
        rec = PMARecord.create(
            window_id=0x1A2,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.85,
        )
        assert rec.window_id == 0x1A2
        assert rec.consent_state == ConsentState.FULL_CONSENT
        assert rec.is_valid
    
    def test_create_with_all_fields(self):
        """Creation with all fields should work."""
        addr = create_from_sector(ThetaSector.GUARDIAN, phi=4, omega=3)
        rec = PMARecord.create(
            window_id=0x100,
            address=addr,
            consent_state=ConsentState.DIMINISHED_CONSENT,
            coherence=0.5,
            complecount=7,
            payload_type=PayloadType.AI,
            fallback_used=True,
        )
        assert rec.complecount_score == 7
        assert rec.payload_type == PayloadType.AI
        assert rec.fallback_triggered is True
    
    def test_window_id_validation(self):
        """Invalid window_id should raise."""
        addr = create_from_sector(ThetaSector.MEMORY)
        with pytest.raises(ValueError):
            PMARecord(
                window_id=0x1000,  # > 12 bits
                timestamp=1000,
                phase_vector=addr.to_int(),
                consent_state=ConsentState.FULL_CONSENT,
                complecount_score=0,
                coherence_score=32,
                payload_type=PayloadType.HUMAN,
                fallback_triggered=False,
            )
    
    def test_complecount_validation(self):
        """Complecount > 31 should raise."""
        addr = create_from_sector(ThetaSector.MEMORY)
        with pytest.raises(ValueError):
            PMARecord(
                window_id=0x100,
                timestamp=1000,
                phase_vector=addr.to_int(),
                consent_state=ConsentState.FULL_CONSENT,
                complecount_score=32,  # > 5 bits
                coherence_score=32,
                payload_type=PayloadType.HUMAN,
                fallback_triggered=False,
            )


class TestPMARecordEncoding:
    """Test PMA record encoding/decoding."""
    
    def test_encode_length(self):
        """Encoded record should be 18 bytes."""
        addr = create_from_sector(ThetaSector.MEMORY)
        rec = PMARecord.create(
            window_id=0x1A2,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.85,
        )
        encoded = rec.to_bytes()
        assert len(encoded) == 18
    
    def test_roundtrip_basic(self):
        """Encode/decode should preserve fields."""
        addr = create_from_sector(ThetaSector.WITNESS, phi=3, omega=2, radius=0.75)
        original = PMARecord.create(
            window_id=0x42,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.7,
            complecount=5,
            payload_type=PayloadType.HUMAN,
            fallback_used=False,
        )
        
        encoded = original.to_bytes()
        decoded = PMARecord.from_bytes(encoded)
        
        assert decoded.window_id == original.window_id
        assert decoded.phase_vector == original.phase_vector
        assert decoded.consent_state == original.consent_state
        assert decoded.complecount_score == original.complecount_score
        assert decoded.coherence_score == original.coherence_score
        assert decoded.payload_type == original.payload_type
        assert decoded.fallback_triggered == original.fallback_triggered
    
    def test_roundtrip_all_consent_states(self):
        """All consent states should roundtrip."""
        addr = create_from_sector(ThetaSector.MEMORY)
        
        for state in ConsentState:
            rec = PMARecord.create(
                window_id=0x100,
                address=addr,
                consent_state=state,
                coherence=0.5,
            )
            decoded = PMARecord.from_bytes(rec.to_bytes())
            assert decoded.consent_state == state
    
    def test_roundtrip_all_payload_types(self):
        """All payload types should roundtrip."""
        addr = create_from_sector(ThetaSector.MEMORY)
        
        for pt in [PayloadType.EMPTY, PayloadType.HUMAN, PayloadType.AI, 
                   PayloadType.SCALAR, PayloadType.HYBRID, PayloadType.FREEZE]:
            rec = PMARecord.create(
                window_id=0x100,
                address=addr,
                consent_state=ConsentState.FULL_CONSENT,
                coherence=0.5,
                payload_type=pt,
            )
            decoded = PMARecord.from_bytes(rec.to_bytes())
            assert decoded.payload_type == pt
    
    def test_crc_validation(self):
        """Corrupted CRC should raise."""
        addr = create_from_sector(ThetaSector.MEMORY)
        rec = PMARecord.create(
            window_id=0x100,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.5,
        )
        
        encoded = bytearray(rec.to_bytes())
        encoded[17] ^= 0xFF  # Corrupt CRC byte
        
        with pytest.raises(ValueError, match="CRC"):
            PMARecord.from_bytes(bytes(encoded))
    
    def test_wrong_length_raises(self):
        """Wrong length data should raise."""
        with pytest.raises(ValueError):
            PMARecord.from_bytes(b'\x00' * 10)


class TestPMABuffer:
    """Test circular buffer storage."""
    
    def test_buffer_capacity(self):
        """Buffer should have correct capacity."""
        buffer = PMABuffer(capacity=64)
        assert buffer.capacity == 64
        assert buffer.count == 0
    
    def test_buffer_capacity_validation(self):
        """Buffer capacity should be 8-4096."""
        with pytest.raises(ValueError):
            PMABuffer(capacity=4)
        with pytest.raises(ValueError):
            PMABuffer(capacity=5000)
    
    def test_write_and_get(self):
        """Write should be retrievable by window_id."""
        buffer = PMABuffer(capacity=16)
        addr = create_from_sector(ThetaSector.MEMORY)
        rec = PMARecord.create(
            window_id=0x42,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.8,
        )
        
        buffer.write(rec)
        
        retrieved = buffer.get(0x42)
        assert retrieved is not None
        assert retrieved.window_id == 0x42
    
    def test_circular_overwrite(self):
        """Buffer should overwrite oldest records."""
        buffer = PMABuffer(capacity=8)
        addr = create_from_sector(ThetaSector.MEMORY)
        
        # Write 10 records to 8-slot buffer
        for i in range(10):
            rec = PMARecord.create(
                window_id=0x100 + i,
                address=addr,
                consent_state=ConsentState.FULL_CONSENT,
                coherence=0.5,
            )
            buffer.write(rec)
        
        # First 2 should be overwritten
        assert buffer.get(0x100) is None
        assert buffer.get(0x101) is None
        
        # Last 8 should exist
        for i in range(2, 10):
            assert buffer.get(0x100 + i) is not None
    
    def test_get_latest(self):
        """get_latest should return newest first."""
        buffer = PMABuffer(capacity=16)
        addr = create_from_sector(ThetaSector.MEMORY)
        
        for i in range(5):
            rec = PMARecord.create(
                window_id=0x100 + i,
                address=addr,
                consent_state=ConsentState.FULL_CONSENT,
                coherence=0.5,
            )
            buffer.write(rec)
        
        latest = buffer.get_latest(3)
        assert len(latest) == 3
        assert latest[0].window_id == 0x104  # Newest
        assert latest[1].window_id == 0x103
        assert latest[2].window_id == 0x102


class TestPMAStore:
    """Test window-based PMA store."""
    
    def test_allocate(self):
        """allocate should return sequential IDs."""
        store = PMAStore()
        wid1 = store.allocate()
        wid2 = store.allocate()
        assert wid1 == 1
        assert wid2 == 2
    
    def test_record_and_get(self):
        """record should store retrievable records."""
        store = PMAStore()
        wid = store.allocate()
        addr = create_from_sector(ThetaSector.BRIDGE)
        
        rec = store.record(
            window_id=wid,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.9,
        )
        assert rec is not None  # Verify record was created

        retrieved = store.get(wid)
        assert retrieved is not None
        assert retrieved.window_id == wid


class TestPMAAccessors:
    """Test PMA record accessors."""
    
    def test_get_address(self):
        """get_address should return RPPAddress."""
        addr = create_from_sector(ThetaSector.DREAM, phi=4, omega=2, radius=0.8)
        rec = PMARecord.create(
            window_id=0x100,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.7,
        )
        
        retrieved_addr = rec.get_address()
        assert retrieved_addr.theta == addr.theta
        assert retrieved_addr.phi == addr.phi
        assert retrieved_addr.omega == addr.omega
    
    def test_coherence_normalized(self):
        """coherence_normalized should be 0-1."""
        addr = create_from_sector(ThetaSector.MEMORY)
        rec = PMARecord.create(
            window_id=0x100,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.85,
        )
        
        assert 0.8 <= rec.coherence_normalized <= 0.9
    
    def test_to_dict(self):
        """to_dict should return proper structure."""
        addr = create_from_sector(ThetaSector.MEMORY)
        rec = PMARecord.create(
            window_id=0x100,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.7,
            payload_type=PayloadType.HUMAN,
            fallback_used=False,
        )
        
        d = rec.to_dict()
        assert 'window_id' in d
        assert 'consent_state' in d
        assert 'coherence_score' in d
        assert d['consent_state'] == 'FULL_CONSENT'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
