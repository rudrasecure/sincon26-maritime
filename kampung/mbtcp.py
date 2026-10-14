"""
mbtcp — a tiny, dependency-free Modbus/TCP client for the SINCON 2026 Maritime
Hacking Kampung.

Standard library only. No pymodbus, no pip install, nothing to break on a strange
laptop at a conference. It speaks just enough Modbus/TCP to:

  * read holding registers           (function code 0x03)
  * read device identification        (function code 0x2B / MEI type 14)

That is all the starter scripts need, and reading the wire format by hand is half
the lesson: a Modbus request is a tiny, unauthenticated packet, and the device
answers anyone who frames it correctly.

Wire format recap (Modbus/TCP):

    MBAP header (7 bytes): transaction-id(2) protocol-id(2)=0 length(2) unit-id(1)
    PDU: function-code(1) + function data

If you want to go further and write registers in your own exploit, you can keep
using this (add FC06/FC16) or switch to pymodbus — see requirements.txt. This
client deliberately does NOT implement any write function: the starter scripts
only look, they never touch.
"""

from __future__ import annotations

import socket
import struct


class ModbusError(Exception):
    """A Modbus exception response, or a malformed/short reply."""


class ModbusTCP:
    """Minimal synchronous Modbus/TCP client (read-only)."""

    def __init__(self, host: str, port: int = 502, unit: int = 1, timeout: float = 4.0):
        self.host = host
        self.port = port
        self.unit = unit
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._tid = 0

    # -- connection -------------------------------------------------------
    def __enter__(self) -> "ModbusTCP":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(self.timeout)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    # -- transport --------------------------------------------------------
    def _txn(self, pdu: bytes) -> bytes:
        """Send one PDU, return the response PDU (function code + data)."""
        if self._sock is None:
            raise ModbusError("not connected")
        self._tid = (self._tid + 1) & 0xFFFF
        mbap = struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, self.unit)
        self._sock.sendall(mbap + pdu)

        header = self._recvn(7)
        tid, proto, length, unit = struct.unpack(">HHHB", header)
        remaining = length - 1
        if remaining < 1:
            raise ModbusError("truncated response")
        body = self._recvn(remaining)
        func = body[0]
        if func & 0x80:  # exception response
            code = body[1] if len(body) > 1 else 0
            raise ModbusError(f"exception 0x{code:02X} to function 0x{func & 0x7F:02X}")
        return body

    def _recvn(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ModbusError("connection closed by peer")
            buf += chunk
        return buf

    # -- function 0x03: read holding registers ----------------------------
    def read_holding(self, address: int, count: int) -> list[int]:
        """Read `count` holding registers starting at `address` (FC03)."""
        if not 1 <= count <= 125:
            raise ValueError("count must be 1..125 per request")
        pdu = struct.pack(">BHH", 0x03, address, count)
        body = self._txn(pdu)
        byte_count = body[1]
        data = body[2:2 + byte_count]
        return [struct.unpack(">H", data[i:i + 2])[0] for i in range(0, len(data), 2)]

    def read_holding_safe(self, address: int, count: int) -> list[int] | None:
        """read_holding that returns None instead of raising (for probing a map)."""
        try:
            return self.read_holding(address, count)
        except (ModbusError, OSError):
            return None

    # -- function 0x2B / MEI 14: read device identification ----------------
    def read_device_identification(self) -> dict[int, bytes]:
        """Read every device-identification object (FC43/14), following More-Follows.

        Returns {object_id: value_bytes}. Standard object ids:
            0x00 VendorName        0x01 ProductCode     0x02 MajorMinorRevision
            0x03 VendorUrl         0x04 ProductName     0x05 ModelName
            0x06 UserApplicationName
        Vendors may add user objects at 0x80+ (serial number, asset tag, ...).
        """
        objects: dict[int, bytes] = {}
        # read-device-id code 0x03 = "extended" (stream ALL objects, incl. user-defined)
        read_code = 0x03
        next_obj = 0x00
        for _ in range(32):  # bounded: avoid an infinite loop on a broken peer
            pdu = struct.pack(">BBBB", 0x2B, 0x0E, read_code, next_obj)
            body = self._txn(pdu)
            # body: 2B 0E | readcode | conformity | more | next | count | objects...
            more = body[4]
            next_obj = body[5]
            count = body[6]
            off = 7
            for _ in range(count):
                oid = body[off]
                olen = body[off + 1]
                val = body[off + 2:off + 2 + olen]
                objects[oid] = val
                off += 2 + olen
            if more != 0xFF:
                break
        return objects


# Object-id -> human name, for pretty printing a device-identification dump.
DEVICE_ID_NAMES = {
    0x00: "VendorName",
    0x01: "ProductCode",
    0x02: "MajorMinorRevision",
    0x03: "VendorUrl",
    0x04: "ProductName",
    0x05: "ModelName",
    0x06: "UserApplicationName",
    0x80: "SerialNumber",
    0x81: "AssetTag",
}


def parse_target(target: str, default_port: int) -> tuple[str, int]:
    """Parse HOST or HOST:PORT. IPv6 in brackets is not supported (not needed here)."""
    if target.count(":") == 1:
        host, _, port = target.partition(":")
        return host, int(port)
    return target, default_port


def s16(v: int) -> int:
    """Interpret a 16-bit register as a signed value."""
    return v - 0x10000 if v >= 0x8000 else v


def u32(hi: int, lo: int) -> int:
    """Combine two registers into a 32-bit unsigned value (hi word first)."""
    return (hi << 16) | lo
