fn main() -> Result<(), Box<dyn std::error::Error>> {
    let report = rpp_link_udp::demo::loopback_demo()?;
    println!("Loopback policy capabilities are fixtures; no tunnel is proved.");
    println!(
        "Initial measured readings (latency_ms is RTT): {:?}",
        report.initial
    );
    println!("After peer closure: {:?}", report.after_close);
    println!(
        "Fleet endpoint {} -> {}",
        report.selected_before, report.selected_after
    );
    Ok(())
}
