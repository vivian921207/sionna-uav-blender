# === JSON 監聽並自動載入對應 .blend (Blender 3.x/4.x) ===
import bpy, json, os, time
from region_loader import RegionLoader   # 需確認 region_loader.py 可用

# ==== 設定 ====
JSON_PATH = r"E:\NYCU\topic2\uav_from_sionna.json"
INTERVAL = 1.0  # 每幾秒檢查一次

# 對應表：JSON 的 "region" -> 對應 .blend 與集合名
REGION_MAP = {
    "A": {
        "blend": r"E:\NYCU\topic2\test_to_blend\1.blend",
        "coll": "RegionRoot"
    },
    "B": {
        "blend": r"E:\NYCU\topic2\test_to_blend\2.blend",
        "coll": "RegionRoot2"
    }
}

# ==== 狀態 ====
_state = {
    "running": False,
    "last_mtime": 0.0,
    "cur_region": None,
    "inst_cur": None,
}

_loader = RegionLoader(verbose=True)

# ==== 讀取 JSON 的 region ====
def _read_region(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "region" not in data:
        return None
    return str(data["region"]).strip().upper()

# ==== 主定時器 ====
def _timer():
    if not _state["running"]:
        return None

    path = bpy.path.abspath(JSON_PATH)
    if not os.path.exists(path):
        return INTERVAL

    m = os.path.getmtime(path)
    if m <= _state["last_mtime"]:
        return INTERVAL
    _state["last_mtime"] = m

    try:
        region = _read_region(path)
        if region not in REGION_MAP:
            print(f"[watch] 無效區域 '{region}'，請確認 JSON。")
            return INTERVAL

        # 若區域變更
        if region != _state["cur_region"]:
            info = REGION_MAP[region]
            print(f"[watch] 切換至區域 {region}")

            # 載入新模型
            col = _loader.load_collection(info["blend"], info["coll"])
            inst = _loader.create_instance(info["coll"], f"REGION_{region}_INST", visible=True)

            # 隱藏舊模型
            if _state["inst_cur"]:
                _loader.set_visible(_state["inst_cur"], False)

            # 更新狀態
            _state["cur_region"] = region
            _state["inst_cur"] = inst
        else:
            print(f"[watch] 區域未變 ({region})")

    except Exception as e:
        print("[watch] 錯誤：", e)

    return INTERVAL

# ==== 控制函數 ====
def start_watch():
    if _state["running"]:
        print("[watch] 已在監聽中。")
        return
    _state["running"] = True
    _state["last_mtime"] = 0.0
    bpy.app.timers.register(_timer, first_interval=0.2)
    print(f"[watch] 開始監聽 {bpy.path.abspath(JSON_PATH)}")

def stop_watch():
    _state["running"] = False
    print("[watch] 停止監聽。")

# 自動啟動
start_watch()
