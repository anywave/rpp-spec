fn main() {
    print!(
        "{}",
        rpp_steer::sim::trace_log().expect("valid scripted measurements")
    );
}
