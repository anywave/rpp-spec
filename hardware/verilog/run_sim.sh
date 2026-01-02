#!/bin/bash
# SPIRAL Protocol HDL Simulation Script
# Requires: Icarus Verilog (iverilog) and GTKWave

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  SPIRAL Protocol HDL Simulation"
echo "=============================================="
echo ""

# Check for iverilog
if ! command -v iverilog &> /dev/null; then
    echo "ERROR: iverilog not found. Install Icarus Verilog:"
    echo "  Ubuntu/Debian: sudo apt install iverilog"
    echo "  macOS: brew install icarus-verilog"
    echo "  Windows: Download from http://bleyer.org/icarus/"
    exit 1
fi

# Build and run legacy testbench
echo "--- Building Legacy Testbench ---"
iverilog -g2012 -o spiral_tb_legacy \
    spiral_consolidated.v \
    spiral_testbench_legacy.v
echo "Running legacy testbench..."
vvp spiral_tb_legacy
echo ""

# Build and run spec-compliant testbench
echo "--- Building Spec-Compliant Testbench ---"
iverilog -g2012 -o spiral_tb_v2 \
    spiral_consolidated.v \
    spiral_testbench_v2.v
echo "Running spec-compliant testbench..."
vvp spiral_tb_v2
echo ""

# Generate waveforms
if [ -f "spiral_tb.vcd" ]; then
    echo "Waveform generated: spiral_tb.vcd"
    echo "View with: gtkwave spiral_tb.vcd"
fi

echo ""
echo "=============================================="
echo "  Simulation Complete"
echo "=============================================="
