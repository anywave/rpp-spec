@echo off
REM SPIRAL Protocol HDL Simulation Script (Windows)
REM Requires: Icarus Verilog (iverilog) - http://bleyer.org/icarus/

echo ======================================================================
echo   SPIRAL Protocol HDL Simulation (Ra-Derived Coherence)
echo ======================================================================
echo.

REM Check for iverilog
where iverilog >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: iverilog not found.
    echo.
    echo Installation options:
    echo   1. Download from: http://bleyer.org/icarus/
    echo   2. Or via scoop: scoop install iverilog
    echo   3. Or via chocolatey: choco install iverilog
    echo.
    echo Add to PATH after installation.
    echo.
    echo Running Python behavioral simulation instead...
    echo.
    python hdl_simulation_canonical.py
    exit /b 0
)

cd /d "%~dp0"

REM Build and run Ra-Derived Coherence Testbench
echo --- Building Ra-Derived Coherence Testbench ---
iverilog -g2012 -o spiral_ra.vvp ^
    coherence_evaluator_ra.v ^
    spiral_testbench.v
if %ERRORLEVEL% neq 0 (
    echo Build failed!
    exit /b 1
)
echo Running Ra-derived testbench...
vvp spiral_ra.vvp
echo.

if exist spiral_testbench.vcd (
    echo Waveform generated: spiral_testbench.vcd
    echo View with: gtkwave spiral_testbench.vcd spiral_testbench.gtkw
)

echo.
echo ======================================================================
echo   Simulation Complete
echo ======================================================================
echo.
echo Files generated:
echo   - spiral_testbench.vcd (waveform)
echo   - spiral_testbench.gtkw (GTKWave config)
echo   - VERIFICATION_REPORT.md (test results)
echo.
