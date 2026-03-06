"""
LoRa (Low-Power Wide-Area) Transport Adapter for RPP

Simulates LoRa packet framing for use with serial-connected LoRa modules
(e.g., Semtech SX1276, RFM95W). In the absence of real hardware, uses a
mock serial interface that records sent packets.

On real hardware: configure with pyserial and AT command set of the module.
"""

import struct
from typing import List, Optional


# ---------------------------------------------------------------------------
# LoRa frame constants
# ---------------------------------------------------------------------------

# Two-byte preamble indicating start of an RPP-over-LoRa frame
LORA_PREAMBLE_HI: int = 0xAA
LORA_PREAMBLE_LO: int = 0x55

# Spreading factor → shell mapping
_SHELL_TO_SF: dict = {
    0: 7,   # Shell 0 (Hot)    — SF7:  fastest, shortest range
    1: 8,   # Shell 1 (Warm)   — SF8
    2: 10,  # Shell 2 (Cold)   — SF10
    3: 12,  # Shell 3 (Frozen) — SF12: slowest, longest range
}

# Maximum LoRa payload depends on SF and regional regulation; use a safe cap.
# At SF7/BW125 the limit is ~222 bytes; we use 200 as a conservative default.
MAX_PAYLOAD_BYTES: int = 200


class LoRaTransport:
    """
    LoRa transport adapter for RPP.

    In mock mode (port=None, the default):
    - No hardware or pyserial is required.
    - Sent frames are appended to the _sent_packets list for inspection.
    - is_available() always returns True.

    In real mode (port set, e.g. "COM3" or "/dev/ttyUSB0"):
    - Requires pyserial: pip install pyserial
    - Frames are written to the serial port as raw bytes.
    - is_available() checks whether the port can be opened.

    Frame format (wire bytes):
        [0x AA]          preamble high
        [0x 55]          preamble low
        [SF byte]        spreading factor (7, 8, 10, or 12)
        [addr byte 0]    most-significant byte of 32-bit address
        [addr bytes 1-3] remaining three bytes of 32-bit address
        [payload ...]    zero or more payload bytes

    The 32-bit address is packed big-endian across bytes 3-6 of the frame:
        frame[3:7] = struct.pack(">I", address_int)

    Example:
        lora = LoRaTransport()                 # mock mode
        lora.send(0x01234567, shell=2)
        print(lora._sent_packets)              # [b'\\xAA\\x55\\x0A\\x01#Eg']
    """

    name: str = "LoRa"

    def __init__(
        self,
        port: Optional[str] = None,
        baud: int = 115200,
        spreading_factor: int = 9,
    ) -> None:
        """
        Initialize LoRa transport.

        Args:
            port:             Serial port path (e.g. "COM3", "/dev/ttyUSB0").
                              None (default) activates mock mode.
            baud:             Baud rate for the serial connection.
                              Ignored in mock mode.
            spreading_factor: Default SF used when shell-based mapping is
                              not applied. Valid values: 7, 8, 9, 10, 11, 12.
        """
        self._port = port
        self._baud = baud
        self._spreading_factor = spreading_factor

        # Mock-mode packet log — inspectable by tests
        self._sent_packets: List[bytes] = []

        # Real-mode serial handle (populated lazily when port is set)
        self._serial = None

    # ------------------------------------------------------------------
    # Shell-to-spreading-factor mapping
    # ------------------------------------------------------------------

    @staticmethod
    def spreading_factor_for_shell(shell: int) -> int:
        """
        Map an RPP shell number to a LoRa spreading factor.

        Shell proximity tiers translate to LoRa range/speed trade-offs:
            Shell 0 (Hot)    → SF7  — fastest, shortest range
            Shell 1 (Warm)   → SF8
            Shell 2 (Cold)   → SF10
            Shell 3 (Frozen) → SF12 — slowest, longest range

        Args:
            shell: RPP shell value (0-3).

        Returns:
            LoRa spreading factor integer.

        Raises:
            ValueError: If shell is not in the range 0-3.
        """
        if shell not in _SHELL_TO_SF:
            raise ValueError(f"Shell must be 0-3, got {shell}")
        return _SHELL_TO_SF[shell]

    # ------------------------------------------------------------------
    # Frame construction
    # ------------------------------------------------------------------

    def frame(self, address_int: int, payload: bytes = b"") -> bytes:
        """
        Construct a LoRa wire frame for an RPP address.

        Frame layout:
            byte 0:   0xAA (preamble high)
            byte 1:   0x55 (preamble low)
            byte 2:   SF byte (current spreading factor)
            bytes 3-6: address packed as 4-byte big-endian unsigned int
            bytes 7+:  payload (may be empty)

        Args:
            address_int: 28-bit RPP address as unsigned integer.
            payload:     Optional payload bytes.

        Returns:
            Raw bytes ready for transmission.
        """
        addr_bytes = struct.pack(">I", address_int)
        return (
            bytes([LORA_PREAMBLE_HI, LORA_PREAMBLE_LO, self._spreading_factor])
            + addr_bytes
            + payload
        )

    # ------------------------------------------------------------------
    # Core transport interface
    # ------------------------------------------------------------------

    def send(
        self,
        address_int: int,
        shell: int = 1,
        payload: bytes = b"",
    ) -> bool:
        """
        Frame and transmit an RPP address + payload via LoRa.

        The spreading factor is derived from the shell argument via
        spreading_factor_for_shell(), overriding the instance default.

        In mock mode:
            Appends the framed bytes to self._sent_packets and returns True.

        In real mode (port set):
            Writes the frame bytes to the serial port.
            Requires pyserial to be installed: pip install pyserial.

        Args:
            address_int: 28-bit RPP address as unsigned integer.
            shell:       RPP shell (0-3); controls spreading factor selection.
            payload:     Optional payload bytes.

        Returns:
            True on success, False on error.
        """
        # Temporarily adopt the shell-derived SF for this packet
        original_sf = self._spreading_factor
        self._spreading_factor = self.spreading_factor_for_shell(shell)

        packet = self.frame(address_int, payload)

        # Restore instance default SF
        self._spreading_factor = original_sf

        if self._port is None:
            # Mock mode — record and return
            self._sent_packets.append(packet)
            return True

        # Real mode — write to serial port
        # Requires: pip install pyserial
        return self._write_serial(packet)

    def _write_serial(self, packet: bytes) -> bool:
        """
        Write packet bytes to the configured serial port.

        Lazily opens the serial connection on first call.

        Args:
            packet: Raw frame bytes to transmit.

        Returns:
            True on success, False if pyserial is unavailable or port errors.
        """
        try:
            import serial  # pyserial — not a stdlib module
        except ImportError:
            # pyserial not installed; cannot use real hardware
            return False

        try:
            if self._serial is None or not self._serial.is_open:
                self._serial = serial.Serial(self._port, self._baud, timeout=1)
            self._serial.write(packet)
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        """
        Check whether the LoRa transport is available.

        In mock mode: always True.
        In real mode: attempts to open the configured serial port.

        Returns:
            True if transport is usable, False otherwise.
        """
        if self._port is None:
            return True

        # Real mode — verify the port is openable
        try:
            import serial  # pyserial
            probe = serial.Serial(self._port, self._baud, timeout=0.1)
            probe.close()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """
        Close the serial port if one is open. No-op in mock mode.
        """
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "LoRaTransport":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        mode = f"port={self._port!r}" if self._port else "mock"
        return f"LoRaTransport({mode}, sf={self._spreading_factor})"
