# === 簡易 JSON 監聽移動 (Blender 3.x/4.x) ===
import bpy, json, os, time
from mathutils import Vector

# ==== 設定 ====
JSON_PATH = "//uav_from_sionna.json"  # 可用 '//' 表示相對於 .blend 的路徑
OBJECT_NAME = "root"              # 留空=用目前 Active 物件；或填物件名，如 "UAV"
INTERVAL    = 0.01                # 每幾秒檢查一次
USE_WORLD   = True               # True: 設定世界座標；False: 設定物件座標(location)

_state = {"running": False, "last_mtime": 0.0}

def _get_obj():
    return bpy.data.objects.get(OBJECT_NAME) if OBJECT_NAME else bpy.context.view_layer.objects.active

def _read_xyz(path):
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ---- 取得 geodetic (lat, lon, h) ----
    # 優先從 data["transmitter"]["geodetic"]；若沒有，退回 data["geodetic"]
    g = None
    if isinstance(data, dict):
        tx = data.get("transmitter")
        if isinstance(tx, dict):
            g = tx.get("geodetic")
        if g is None:
            g = data.get("geodetic")

    if not isinstance(g, dict) or not all(k in g for k in ("lat", "lon")):
        raise ValueError("JSON 需提供 geodetic.lat / geodetic.lon（可含 h，高度預設 0）")

    lat = float(g["lat"])
    lon = float(g["lon"])
    h   = float(g.get("h", 0.0))

    # ---- 取得參考原點 (lat0, lon0, h0) ----
    if "origin" in data and isinstance(data["origin"], dict):
        o = data["origin"]
        lat0 = float(o["lat"]); lon0 = float(o["lon"]); h0 = float(o.get("h", 0.0))
    else:
        b = data.get("bbox")
        if not isinstance(b, dict) or not all(k in b for k in ("min_lat", "max_lat", "min_lon", "max_lon")):
            raise ValueError("缺少 origin，且 bbox 也未提供（至少其一需存在）")
        lat0 = (float(b["min_lat"]) + float(b["max_lat"])) / 2.0
        lon0 = (float(b["min_lon"]) + float(b["max_lon"])) / 2.0
        h0   = 0.0

    # ---- geodetic -> ENU (m) -> Blender XYZ（BU）----
    try:
        import pymap3d as pm
    except Exception as e:
        raise RuntimeError("需要 pymap3d 才能從經緯度換算 XYZ，請先安裝：pip install pymap3d") from e

    e, n, u = pm.geodetic2enu(lat, lon, h, lat0, lon0, h0)  # meters: East, North, Up

    # 1BU = ? m（預設 1.0）。若你的腳本有定義 SCALE_M_PER_BU，就會自動使用
    scale = globals().get("SCALE_M_PER_BU", 1.0)
    x = e / float(scale)
    y = n / float(scale)
    z = u / float(scale)

    return float(x), float(y), float(z)


def focus_on_object(obj_name):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        print(f"[focus] 找不到物件 {obj_name}")
        return

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                override = {
                                    'window': window,
                                    'screen': window.screen,
                                    'area': area,
                                    'region': region,
                                    'space_data': space,
                                    'scene': bpy.context.scene,
                                    'active_object': obj,
                                }
                                bpy.context.view_layer.objects.active = obj
                                bpy.ops.view3d.view_selected(override)
                                return


def _set_location(obj, vec3):
    v = Vector(vec3)
    if USE_WORLD:
        obj.matrix_world.translation = v
    else:
        obj.location = v

def _timer():
    if not _state["running"]:
        return None
    path = bpy.path.abspath(JSON_PATH)
    if os.path.exists(path):
        m = os.path.getmtime(path)
        if m > _state["last_mtime"]:
            _state["last_mtime"] = m
            try:
                x, y, z = _read_xyz(path)
                obj = _get_obj()
                if obj is not None:
                    _set_location(obj, (x, y, z))
                    print(f"[json-move] {obj.name} → ({x:.3f}, {y:.3f}, {z:.3f}) @ {time.strftime('%H:%M:%S')}")
                else:
                    print("[json-move] 找不到目標物件（請選取物件或設定 OBJECT_NAME）")
            except Exception as e:
                print("[json-move] 讀檔或移動失敗：", e)
    return INTERVAL

def start_watch():
    focus_on_object(OBJECT_NAME)
    if _state["running"]:
        print("[json-move] 已在監聽中。若要重啟請先呼叫 stop_watch()")
        return
    _state["running"] = True
    _state["last_mtime"] = 0.0
    bpy.app.timers.register(_timer, first_interval=0.2)
    print(f"[json-move] 監聽 {bpy.path.abspath(JSON_PATH)}，每 {INTERVAL}s 檢查一次。目標物件：{OBJECT_NAME or '(Active)'}")
    print("[json-move] JSON 範例：{'x':1.2,'y':0,'z':0.8} 或 {'location':[1.2,0,0.8]}")

def stop_watch():
    _state["running"] = False
    print("[json-move] 停止監聽。")

# 自動啟動
start_watch()
