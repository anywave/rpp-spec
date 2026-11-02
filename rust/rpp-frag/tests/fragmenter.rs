use rpp_frag::{Error, Fragmenter, HEADER_LEN};

#[test]
fn emitted_fragments_never_exceed_mtu_and_reconstruct_exact_bytes() {
    // Mutation emitted-fragment-over-mtu: include the header in the MTU budget.
    let data = core::array::from_fn::<_, 112, _>(|i| i as u8);
    for mtu in [6, 20, 51, 117, 512] {
        let mut fragmenter = Fragmenter::<112>::new(&data, 0x1234, mtu).unwrap();
        let mut output = [0; 512];
        let mut recovered = Vec::new();
        while let Some(length) = fragmenter.write_next(&mut output).unwrap() {
            assert!(length <= mtu);
            assert_eq!(&output[..4], &[0xe0, 112, 0x12, 0x34]);
            assert_eq!(output[4] as usize, recovered.len());
            recovered.extend_from_slice(&output[HEADER_LEN..length]);
        }
        assert_eq!(recovered, data);
    }
}

#[test]
fn invalid_limits_and_short_buffer_do_not_advance_cursor() {
    // Mutations tiny-mtu/oversize-accepted and cursor-advanced-on-short-buffer.
    assert!(matches!(
        Fragmenter::<112>::new(&[1], 0, 5),
        Err(Error::InvalidMtu)
    ));
    assert!(matches!(
        Fragmenter::<112>::new(&[0; 113], 0, 20),
        Err(Error::TooLarge)
    ));
    assert!(matches!(
        Fragmenter::<256>::new(&[1], 0, 20),
        Err(Error::TooLarge)
    ));
    assert!(matches!(
        Fragmenter::<112>::new(&[], 0, 20),
        Err(Error::InvalidHeader)
    ));
    let mut fragmenter = Fragmenter::<112>::new(&[7; 112], 0, 20).unwrap();
    assert_eq!(
        fragmenter.write_next(&mut [0; 19]),
        Err(Error::BufferTooSmall)
    );
    let mut output = [0; 20];
    assert_eq!(fragmenter.write_next(&mut output), Ok(Some(20)));
    assert_eq!(output[4], 0);
}
