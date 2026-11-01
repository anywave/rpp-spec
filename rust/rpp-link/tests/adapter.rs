use rpp_control::{
    decode, ControlFrame, ControlKind, NodeId, Signature, VerifiedControlFrame, Verifier,
    HEADER_LEN,
};
use rpp_link::{
    dispatch, DataOutcome, DispatchError, DispatchOutcome, LinkAdapter, LinkKind, LinkReading,
    Outbound, TrafficPath,
};

struct AcceptFixture;
impl Verifier for AcceptFixture {
    fn verify(&self, _sender: &NodeId, _header: &[u8; HEADER_LEN], _signature: &Signature) -> bool {
        true
    }
}
fn frame() -> VerifiedControlFrame {
    // This verifier is a prior-verdict fixture, not signature verification.
    let raw = ControlFrame::new(ControlKind::Stop, 7, [1; 16], [2; 16], [3; 64]).encode();
    decode(&raw, &[2; 16], &AcceptFixture).unwrap()
}
#[derive(Default)]
struct Recorder {
    data: usize,
    control: usize,
}
impl LinkAdapter for Recorder {
    type Error = ();
    fn kind(&self) -> LinkKind {
        LinkKind::Lan
    }
    fn read(&mut self, tick: u64) -> Result<LinkReading, Self::Error> {
        Ok(LinkReading {
            latency_ms: 10,
            loss_ppm: 0,
            jitter_ms: 1,
            available: true,
            observed: tick,
        })
    }
    fn send_verified_control_frame(
        &mut self,
        _frame: &VerifiedControlFrame,
    ) -> Result<(), Self::Error> {
        self.control += 1;
        Ok(())
    }
    fn send_data(&mut self, _payload: &[u8]) -> Result<DataOutcome, Self::Error> {
        self.data += 1;
        Ok(DataOutcome::Sent)
    }
}

#[test]
fn control_on_data_path_is_rejected_before_adapter_callback() {
    // Mutation control-on-data-denial: deleting the dispatch guard must expose a forbidden adapter call.
    let mut adapter = Recorder::default();
    let frame = frame();
    assert_eq!(
        dispatch(&mut adapter, TrafficPath::Data, Outbound::Control(&frame)),
        Err(DispatchError::WrongTrafficClass)
    );
    assert_eq!((adapter.data, adapter.control), (0, 0));
}
#[test]
fn valid_data_dispatch_succeeds() {
    // Mutation drop-valid-data: ordinary data must reach the data hook; clean traffic-class control.
    let mut adapter = Recorder::default();
    assert_eq!(
        dispatch(
            &mut adapter,
            TrafficPath::Data,
            Outbound::Data(b"opaque-app-data")
        ),
        Ok(DispatchOutcome::Data(DataOutcome::Sent))
    );
    assert_eq!((adapter.data, adapter.control), (1, 0));
}
#[test]
fn control_path_accepts_only_verified_control_type() {
    // Mutation cross-class-control: data cannot use a control path, while the checked fixed frame can.
    let mut adapter = Recorder::default();
    let frame = frame();
    assert_eq!(
        dispatch(
            &mut adapter,
            TrafficPath::Control,
            Outbound::Data(b"payload")
        ),
        Err(DispatchError::WrongTrafficClass)
    );
    assert_eq!(
        dispatch(
            &mut adapter,
            TrafficPath::Control,
            Outbound::Control(&frame)
        ),
        Ok(DispatchOutcome::Control)
    );
    assert_eq!((adapter.data, adapter.control), (0, 1));
}
#[test]
fn fixed_reading_fields_are_heap_free_and_loss_is_bounded() {
    // Mutation omit-reading-bounds: loss above one million ppm must be invalid; no heap-owning field is present.
    let mut adapter = Recorder::default();
    let mut reading = adapter.read(9).unwrap();
    assert_eq!(reading.observed, 9);
    assert!(reading.valid());
    reading.loss_ppm = 1_000_000;
    assert!(reading.valid());
    reading.loss_ppm += 1;
    assert!(!reading.valid());
    assert!(!core::mem::needs_drop::<LinkReading>());
    for kind in [
        LinkKind::Lan,
        LinkKind::Wifi,
        LinkKind::Ble,
        LinkKind::Lora,
        LinkKind::Internet,
    ] {
        let _ = kind;
    }
}
