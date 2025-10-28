import json, time, os, math

# === 基本設定 ===
JSON_PATH = r"E:\NYCU\topic2\Loading_scene_sinnoa\jason\uav_from_sionna.json"

# 三個區域在 X 軸上的中心座標
REGION_CENTERS = {
    "C": -1400.0,
    "A": 0.0,
    "B": 1400.0,
}

# UAV 初始狀態
uav = {"x": 0.0, "y": 0.0, "z": 150.0}
vx = 50.0        # UAV 速度 (Blender 單位/秒)
dt = 0.05         # 更新間隔 (秒)
direction = +1    # +1 表示往右，-1 表示往左

# === 距離閾值設定 ===
SHOW_DIST = 1400.0   # 進入可視範圍 → show
HIDE_DIST = 2400.0   # 太遠 → hide
# 超過 HIDE_DIST 的區域不寫入 JSON（代表要卸載）

# === 計算工具 ===
def distance_to_region(region_name):
    cx = REGION_CENTERS[region_name]
    return abs(uav["x"] - cx)

def current_region():
    """依 UAV 位置決定目前所在區域名稱"""
    nearest = min(REGION_CENTERS.items(), key=lambda kv: abs(uav["x"] - kv[1]))
    return nearest[0]

def build_json():
    """根據距離決定 regions 欄位內容"""
    regions = {}

    for name in REGION_CENTERS:
        d = distance_to_region(name)
        if d <= SHOW_DIST:
            regions[name] = "show"
        elif d <= HIDE_DIST:
            regions[name] = "hide"
        # 超過範圍不列入，代表 Blender 端應 unload

    return {
        "version": 1,
        "regions": regions,
        "remove_unlisted": True,
        "uav": {
            "region": current_region(),          # ✅ 新增 UAV 所屬區域名稱
            "x": round(uav["x"], 2),
            "y": round(uav["y"], 2),
            "z": round(uav["z"], 2),
        },
    }

# === 主模擬迴圈 ===
print("🚁 UAV 距離式載入模擬開始 (Ctrl+C 停止)\n")

try:
    while True:
        # 移動 UAV
        uav["x"] += vx * direction * dt

        # 超出邊界則反向
        if uav["x"] > 1400:
            uav["x"] = 1400
            direction = -1
        elif uav["x"] < -1400:
            uav["x"] = -1400
            direction = +1

        # 建立 JSON 並寫入
        data = build_json()
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 印出狀態
        summary = ", ".join(f"{k}:{v}" for k, v in data["regions"].items())
        reg = data["uav"]["region"]
        print(f"[update] X={uav['x']:7.1f} | {summary:25s} | region={reg}")

        time.sleep(dt)

except KeyboardInterrupt:
    print("\n🛑 模擬已手動停止。")
