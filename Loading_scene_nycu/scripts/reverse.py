# === JSON 監聽並自動載入對應 .blend + 地圖移動模式 (Blender 3.x/4.x) ===
import bpy, os, sys, importlib

# === 自動加入 scripts 資料夾到搜尋路徑 ===
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(bpy.data.filepath)), "scripts")
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# === 清除內嵌 Text Block（避免誤載內嵌版本） ===
for name in ("region_loader", "json_watcher"):
    if name in bpy.data.texts:
        print(f"[safe import] 發現內嵌 {name}.py，正在刪除...")
        bpy.data.texts.remove(bpy.data.texts[name])

# === 匯入模組 ===
import region_loader, json_watcher
importlib.reload(region_loader)
importlib.reload(json_watcher)
from region_loader import RegionLoader
from json_watcher import JSONWatcher


# === 設定 ===
JSON_PATH = "//../jason/uav_from_sionna.json"  # 相對於 .blend
INTERVAL = 0.05  # 檢查頻率（秒）

# 每個 region 的初始位置（世界座標）
REGION_MAP = {
    "A": {"blend": "//nycu0.blend", "coll": "RegionRoot1", "pos": (0.0, 0.0, 0.0)},
    "B": {"blend": "//nycu1.blend", "coll": "RegionRoot2", "pos": (1170.0, 0.0, 0.0)},
    "C": {"blend": "//nycu2.blend", "coll": "RegionRoot3", "pos": (-1170.0, 0.0, 0.0)},
}

# === 狀態 ===
loader = RegionLoader(verbose=True)
uav_fixed_pos = (0.0, 0.0, 200.0)  # UAV 固定位置


# === 回調 1：控制區域載入/顯示/隱藏 ===
def on_region_update(data):
    """依據 data['regions'] 控制各區域的載入與可見性"""
    if not isinstance(data, dict) or "regions" not in data:
        return

    regions = data["regions"]
    remove_unlisted = data.get("remove_unlisted", False)

    for region, action in regions.items():
        region = region.strip().upper()
        if region not in REGION_MAP:
            print(f"[region-watch] 未知區域 '{region}'，跳過。")
            continue

        info = REGION_MAP[region]
        blend_path = bpy.path.abspath(info["blend"])
        coll_name = info["coll"]
        pos = info.get("pos", (0.0, 0.0, 0.0))

        inst_name = f"REGION_{region}_INST"
        inst = bpy.data.objects.get(inst_name)
        col = bpy.data.collections.get(coll_name)
        action = str(action).lower().strip()

        if action in ("show", "hide"):
            if not col:
                print(f"[region-watch] 載入 {region}（初始狀態: {action}）")
                try:
                    col = loader.load_collection(blend_path, coll_name)
                    inst = loader.create_instance(coll_name, inst_name, visible=(action == "show"))
                    inst.location = pos
                except Exception as e:
                    print(f"[region-watch] 無法載入 {region}: {e}")
                    continue
            else:
                loader.set_visible(inst, (action == "show"))
                print(f"[region-watch] {'顯示' if action == 'show' else '隱藏'} 區域 {region}")

    # 移除未列出的區域
    if remove_unlisted:
        listed = set(k.strip().upper() for k in regions.keys())
        for key, info in REGION_MAP.items():
            if key not in listed:
                coll_name = info["coll"]
                if coll_name in bpy.data.collections:
                    print(f"[region-watch] 移除未列出區域 {key}")
                    try:
                        loader.unload(coll_name)
                    except Exception as e:
                        print(f"[region-watch] 無法移除 {key}: {e}")


# === 回調 2：地圖反向移動（UAV 固定） ===
def on_uav_update(data):
    """依據 data['uav'] 控制地圖偏移，而非 UAV 物體"""
    if not isinstance(data, dict) or "uav" not in data:
        return

    uav = data["uav"]
    if not isinstance(uav, dict):
        return

    # UAV 實際位置 (用來決定地圖偏移)
    x = float(uav.get("x", 0.0))
    y = float(uav.get("y", 0.0))
    z = float(uav.get("z", uav_fixed_pos[2]))

    # UAV 固定在原點
    uav_obj = bpy.data.objects.get("UAV")
    if uav_obj:
        uav_obj.location = (0.0, 0.0, z)

    # 地圖以 UAV 位置的反方向偏移
    for region, info in REGION_MAP.items():
        inst_name = f"REGION_{region}_INST"
        inst = bpy.data.objects.get(inst_name)
        if inst:
            base_pos = info.get("pos", (0.0, 0.0, 0.0))
            inst.location.x = base_pos[0] - x  # ✨ 關鍵反向偏移
            inst.location.y = base_pos[1] - y
    print(f"[map-move] 偏移地圖 ← UAV({x:.2f}, {y:.2f}, {z:.2f})")


# === 啟動監聽 ===
def start_watch():
    watcher = JSONWatcher(json_path=JSON_PATH, interval=INTERVAL, verbose=True)
    watcher.add_callback(on_region_update)
    watcher.add_callback(on_uav_update)
    watcher.start()
    print(f"[main] 已啟動監聽：{bpy.path.abspath(JSON_PATH)}")
    return watcher


# === 自動啟動 ===
watcher = start_watch()
