#![no_main]
libfuzzer_sys::fuzz_target!(|data: &[u8]| {
    rpp_input_hardening::billboard_bytes(data);
});
