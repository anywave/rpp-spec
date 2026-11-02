#![no_main]
libfuzzer_sys::fuzz_target!(|input: &[u8]| {
    let Some((mode, data)) = input.split_first() else {
        return;
    };
    if mode & 1 == 1 {
        let mtu = if mode & 2 == 2 { 51 } else { 20 };
        rpp_input_hardening::schedule(data, 8, 3, mtu);
    } else {
        rpp_input_hardening::arbitrary_fragments(data);
    }
});
