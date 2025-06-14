#!/usr/bin/env python3
"""
highspeed_reader.py – robust reader for Teensy framed current-sensor stream
author: Dune Industries, Inc. – June 2025
"""

import os, serial, struct, collections, time, statistics

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SERIAL_PORT  = "/dev/ttyACM0"
BAUD_RATE    = 6_000_000

SYNC_BYTE    = 0xA5          # Must match Teensy code
USE_CHECKSUM = True          # Set False if MCU sends no XOR byte

PRINT_INTERVAL_S = 1.0       # How often to show SPS / currents
WINDOW_SIZE      = 1000      # For instantaneous SPS calculation

# Sensor scaling (done *only* for the values we show)
VREF       = 3.3            # [V]
ADC_MAX    = 4095
SENS_DRILL = 0.1            # [V/A]
SENS_POWER = 0.1
SENS_LINEAR= 0.1875
def to_current(raw, sens):
    return (raw * VREF / ADC_MAX) / sens

# ─── LOW-LEVEL CONSTANTS ─────────────────────────────────────────────────────
_PAYLOAD_LEN = 6                           # 3 × uint16
_FRAME_LEN   = 1 + _PAYLOAD_LEN + (1 if USE_CHECKSUM else 0)

_STRUCT_U16  = struct.Struct('<3H')        # little-endian

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    # Optional: max process priority (won't crash if not root)
    try:  os.nice(-20)
    except PermissionError:  pass

    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0) as ser:
        buf   = bytearray(_FRAME_LEN * 1024)    # 1 k frames at once
        view  = memoryview(buf)
        times = collections.deque(maxlen=WINDOW_SIZE)

        start_ns       = time.perf_counter_ns()
        last_print_ns  = start_ns
        sample_total   = 0
        last_raw       = (0, 0, 0)

        print("Streaming…  Ctrl-C to stop")

        try:
            while True:
                n = ser.readinto(view)         # Non-blocking; returns bytes read
                if n == 0:
                    continue

                cursor = 0
                now_ns = time.perf_counter_ns()

                # ── parse everything read in this chunk ────────────────────
                while cursor + _FRAME_LEN <= n:
                    if view[cursor] != SYNC_BYTE:
                        cursor += 1            # Resync
                        continue

                    payload = view[cursor+1 : cursor+1+_PAYLOAD_LEN]
                    if USE_CHECKSUM:
                        chk = 0
                        for b in payload:  chk ^= b
                        if chk != view[cursor+1+_PAYLOAD_LEN]:
                            cursor += 1        # Bad frame -> resync
                            continue

                    raw = _STRUCT_U16.unpack_from(payload)
                    last_raw = raw
                    sample_total += 1
                    times.append(now_ns)

                    cursor += _FRAME_LEN

                # ── stats / print ───────────────────────────────────────────
                if now_ns - last_print_ns >= PRINT_INTERVAL_S * 1e9 and len(times) > 1:
                    dt_ns = times[-1] - times[0]
                    inst_sps = (len(times)-1) * 1e9 / dt_ns
                    drill, power, linear = map(int, last_raw)

                    print(
                        f"\r{inst_sps:8.1f} SPS  |  "
                        f"Drill: {to_current(drill, SENS_DRILL):6.3f} A  "
                        f"Power: {to_current(power, SENS_POWER):6.3f} A  "
                        f"Linear: {to_current(linear, SENS_LINEAR):6.3f} A",
                        end="", flush=True
                    )
                    last_print_ns = now_ns

        except KeyboardInterrupt:
            duration_s = (time.perf_counter_ns() - start_ns) / 1e9
            avg_sps    = sample_total / duration_s
            print("\n\nInterrupted by user.")
            print(f"Total samples  : {sample_total}")
            print(f"Duration [s]   : {duration_s:.1f}")
            print(f"Average SPS    : {avg_sps:.1f}")
            d,p,l = map(int, last_raw)
            print("Last sample    :", 
                  f"Drill={to_current(d,SENS_DRILL):.3f} A,",
                  f"Power={to_current(p,SENS_POWER):.3f} A,",
                  f"Linear={to_current(l,SENS_LINEAR):.3f} A")

if __name__ == "__main__":
    main()
