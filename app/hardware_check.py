#!/usr/bin/env python

# Copyright (c) 2026 SoftBank Corp.
#
# <<licensetext>>

import os
import re
import subprocess


# ===== 設定 =====
DEVICES = [
    "ttyWitMotion",   # IMU
    "ttyCANable",     # CAN
    "ttyLD06-19",     # LiDAR
]

LIDAR_DEV = "/dev/ttyLD06-19"
LIDAR_TIMEOUT = 0.1

IMU_DEV = "/dev/ttyWitMotion"
IMU_TIMEOUT = 0.1


def _run_cmd(cmd, timeout=None):
    """コマンド実行（失敗しても落とさない）"""
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 999, "", str(e)


def _read_device_bytes(dev_path: str, timeout_sec: float, max_bytes: int = 256) -> int:
    """
    /dev/tty*** を timeout 付きで読んでバイト数を返す
    bashの `timeout 0.1 cat /dev/... | head -c 256 | wc -c` 相当
    """
    if not os.path.exists(dev_path):
        return -1

    # timeoutコマンドがある前提（Ubuntu）
    cmd = ["bash", "-lc", f"timeout {timeout_sec} cat {dev_path} 2>/dev/null | head -c {max_bytes} | wc -c"]
    code, out, err = _run_cmd(cmd)

    try:
        return int(out)
    except Exception:
        return 0


def run_hardware_check():
    """
    戻り値:
      logs: list[str]     -> コンソール用
      speak: str          -> 吹き出し用（NGだけ / 全部OKならオールクリア）
      results: dict       -> 判定まとめ
    """
    logs = []
    ng_messages = []
    results = {}

    def ok(msg):
        logs.append(f"[OK] {msg}")

    def ng(msg):
        logs.append(f"[NG] {msg}")
        ng_messages.append(msg)

    logs.append("=== /dev device check ===")
    for dev in DEVICES:
        path = f"/dev/{dev}"
        if os.path.exists(path):
            ok(f"{path} is found")
            results[path] = "OK"
        else:
            ng(f"{path} is not found")
            results[path] = "NG"

    # --- CAN check ---
    logs.append("")
    logs.append("=== CAN (can0) check ===")
    code, out, err = _run_cmd(["bash", "-lc", "ifconfig can0"])
    if code == 0:
        # RX packets を抜く（ifconfigの出力差異があるので雑に探す）
        m = re.search(r"RX packets\s+(\d+)", out)
        if m:
            rx = int(m.group(1))
            if rx > 0:
                ok(f"can0 found, RX packets = {rx}")
                results["can0_rx_packets"] = rx
            else:
                ng("can0 found, but RX packets is 0")
                results["can0_rx_packets"] = 0
        else:
            ng("can0 found, but RX packets not detected")
            results["can0_rx_packets"] = "unknown"
    else:
        ng("No can0")
        results["can0"] = "NG"

    # --- Wi-Fi check ---
    logs.append("")
    logs.append("=== Wi-Fi interface ===")
    code, out, err = _run_cmd(["bash", "-lc", "ip -4 addr show"])
    wifi_if = None
    wifi_ip = None
    if code == 0:
        # wl* の iface と inet を探す
        current_iface = None
        for line in out.splitlines():
            m1 = re.match(r"^\d+:\s+([^:]+):", line)
            if m1:
                current_iface = m1.group(1)

            if current_iface and current_iface.startswith("wl"):
                m2 = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/", line)
                if m2:
                    wifi_if = current_iface
                    wifi_ip = m2.group(1)
                    break

    if wifi_if and wifi_ip:
        ok(f"Wi-Fi IF = {wifi_if}, IP = {wifi_ip}")
        results["wifi"] = "OK"
    else:
        ng("No Wi-Fi IF")
        results["wifi"] = "NG"

    # --- Audio check (Sound_Blaster) ---
    logs.append("")
    logs.append("=== Audio Device Check (Sound_Blaster required) ===")

    # mic
    code, out, err = _run_cmd(["bash", "-lc", "pactl list short sources"])
    mic_found = False
    mic_name = ""
    if code == 0:
        for line in out.splitlines():
            if "monitor" in line:
                continue
            if re.search(r"Sound_Blaster", line, re.IGNORECASE):
                # pactl: index name driver ...
                parts = line.split()
                if len(parts) >= 2:
                    mic_name = parts[1]
                    mic_found = True
                    break

    if mic_found:
        ok(f"Sound_Blaster microphone found: {mic_name}")
        results["mic"] = "OK"
    else:
        ng("Sound_Blaster microphone not found")
        results["mic"] = "NG"

    # speaker
    code, out, err = _run_cmd(["bash", "-lc", "pactl list short sinks"])
    sp_found = False
    sp_name = ""
    if code == 0:
        for line in out.splitlines():
            if re.search(r"Sound_Blaster", line, re.IGNORECASE):
                parts = line.split()
                if len(parts) >= 2:
                    sp_name = parts[1]
                    sp_found = True
                    break

    if sp_found:
        ok(f"Sound_Blaster speaker found: {sp_name}")
        results["speaker"] = "OK"
    else:
        ng("Sound_Blaster speaker not found")
        results["speaker"] = "NG"

    # --- LiDAR data check ---
    logs.append("")
    logs.append("=== LiDAR Data Check ===")
    if os.path.exists(LIDAR_DEV):
        byte_count = _read_device_bytes(LIDAR_DEV, LIDAR_TIMEOUT)
        if byte_count > 0:
            ok(f"LiDAR is sending data ({byte_count} bytes received)")
            results["lidar_data"] = "OK"
        else:
            ng("LiDAR device found but no data received")
            results["lidar_data"] = "NG"
    else:
        ng(f"LiDAR device not found: {LIDAR_DEV}")
        results["lidar_data"] = "NG"

    # --- IMU data check ---
    logs.append("")
    logs.append("=== IMU Data Check ===")
    if os.path.exists(IMU_DEV):
        byte_count = _read_device_bytes(IMU_DEV, IMU_TIMEOUT)
        if byte_count > 0:
            ok(f"IMU is sending data ({byte_count} bytes received)")
            results["imu_data"] = "OK"
        else:
            ng("IMU device found but no data received")
            results["imu_data"] = "NG"
    else:
        ng(f"IMU device not found: {IMU_DEV}")
        results["imu_data"] = "NG"

    # --- RealSense check ---
    logs.append("")
    logs.append("=== RealSense Check ===")
    code, out, err = _run_cmd(["bash", "-lc", "lsusb"])
    if code == 0 and re.search(r"Intel.*RealSense", out, re.IGNORECASE):
        line = ""
        for l in out.splitlines():
            if re.search(r"Intel.*RealSense", l, re.IGNORECASE):
                line = l
                break
        ok(f"RealSense device detected: {line}")
        results["realsense"] = "OK"
    else:
        ng("No Intel RealSense device detected")
        results["realsense"] = "NG"

    # --- Bluetooth controller check ---
    logs.append("")
    logs.append("=== Bluetooth Controller Check ===")

    # bluetoothctl があるか
    code, out, err = _run_cmd(["bash", "-lc", "command -v bluetoothctl"])
    if code != 0:
        ng("bluetoothctl not found")
        results["bluetoothctl"] = "NG"
    else:
        # 接続中デバイス確認（簡易）
        code, out, err = _run_cmd(["bash", "-lc", "bluetoothctl info"])
        if code != 0 or "Connected: yes" not in out:
            ng("No Bluetooth devices connected")
            results["bluetooth_controller"] = "NG"
        else:
            # controllerっぽい単語があるか
            if re.search(r"(controller|gamepad|joystick|joy|xbox|dualshock|dualsense|wireless controller)", out, re.IGNORECASE):
                ok("Bluetooth controller connected")
                results["bluetooth_controller"] = "OK"
            else:
                ng("Bluetooth device connected, but no controller detected")
                results["bluetooth_controller"] = "NG"

    # ===== 吹き出し用メッセージ（NGだけ） =====
    if len(ng_messages) == 0:
        speak = "ハードウェアチェック、オールクリアだよ！"
    else:
        speak = "チェックでエラーがあったよ：\n" + "\n".join([f"・{m}" for m in ng_messages])

    return logs, speak, results
