# === JSON 監聽並自動載入對應 .blend (Blender 3.x/4.x) ===
import bpy, json, os, sys, time, importlib

scripts_dir = os.path.join(os.path.dirname(os.path.dirname(bpy.data.filepath)), "scripts")
region_loader_path = os.path.join(scripts_dir, "region_loader.py")

# 如果內嵌 Text Block 存在，先刪除
if "region_loader" in bpy.data.texts:
    print("[safe import] 發現內嵌 region_loader Text，正在刪除...")
    bpy.data.texts.remove(bpy.data.texts["region_loader"])

# 加入外部搜尋路徑
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# 強制 reload 外部版本
import region_loader
importlib.reload(region_loader)
from region_loader import RegionLoader



# === 設定 ===
JSON_PATH = "//../jason/uav_from_sionna.json"  # 相對於 .blend
INTERVAL = 1.0  # 每秒檢查一次

# === 對應表：JSON 的 "region" / "regions" -> 對應 .blend 與集合名 ===
REGION_MAP = {
    "A": {
        "blend": "//1.blend",
        "coll": "RegionRoot1",
        "pos": (0.0, 0.0, 0.0)
    },
    "B": {
        "blend": "//2.blend",
        "coll": "RegionRoot2",
        "pos": (30.0, 0.0, 0.0)
    }
}

# === 狀態 ===
loader = RegionLoader(verbose=True)
_state = {
    "running": False,
    "last_mtime": 0.0,
    "cur_region": None,
    "cur_inst": None
}


# === 讀取 JSON 並解析區域 ===
def _read_region(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[watch] 讀取 JSON 失敗：{e}")
        return None

    if not isinstance(data, dict):
        return None

    # 舊格式 {"region": "A"}
    if "region" in data:
        return str(data["region"]).strip().upper()

    # 新格式 {"regions": {"A": "show"}}
    if "regions" in data and isinstance(data["regions"], dict):
        for key, value in data["regions"].items():
            if str(value).lower() == "show":
                return key.strip().upper()

    return None


# === 主監聽邏輯 ===
def _json_timer():
    if not _state["running"]:
        return None

    path = bpy.path.abspath(JSON_PATH)
    if not os.path.exists(path):
        print(f"[watch] 找不到 JSON：{path}")
        return INTERVAL

    # 檢查是否有修改
    mtime = os.path.getmtime(path)
    if mtime <= _state["last_mtime"]:
        return INTERVAL

    _state["last_mtime"] = mtime

    region = _read_region(path)
    if not region:
        print(f"[watch] 無效區域 '{region}'，請確認 JSON。")
        return INTERVAL

    if region not in REGION_MAP:
        print(f"[watch] 未知區域 '{region}'，請確認 REGION_MAP。")
        return INTERVAL

    # 若區域未變則略過
    if region == _state["cur_region"]:
        print(f"[watch] 區域未變 ({region})")
        return INTERVAL

    info = REGION_MAP[region]
    blend_path = bpy.path.abspath(info["blend"])
    coll_name = info["coll"]
    pos = info.get("pos", (0.0, 0.0, 0.0))

    print(f"[watch] 切換至區域 {region}")
    print(f"[watch] 載入：{blend_path}")

    try:
        col = loader.load_collection(blend_path, coll_name)
        inst = loader.create_instance(coll_name, f"REGION_{region}_INST", visible=True)
        inst.location = pos

        # 隱藏舊模型
        if _state["cur_inst"]:
            loader.set_visible(_state["cur_inst"], False)

        _state["cur_region"] = region
        _state["cur_inst"] = inst
        print(f"[watch] 區域 {region} 載入完成，位置 {pos}")

    except Exception as e:
        print(f"[watch] 載入區域時發生錯誤：{e}")

    return INTERVAL


# === 控制函式 ===
def start_watch():
    if _state["running"]:
        print("[watch] 已在監聽中。")
        return
    _state["running"] = True
    _state["last_mtime"] = 0.0
    bpy.app.timers.register(_json_timer, first_interval=0.2)
    print(f"[watch] 開始監聽 {bpy.path.abspath(JSON_PATH)}")

def stop_watch():
    _state["running"] = False
    print("[watch] 停止監聽。")


# === 自動啟動 ===
start_watch()
