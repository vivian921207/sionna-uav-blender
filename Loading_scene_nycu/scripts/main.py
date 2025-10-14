# === JSON 監聽並自動載入對應 .blend (Blender 3.x/4.x) ===
import bpy, os, sys, importlib

# === 自動加入 scripts 資料夾到搜尋路徑 ===
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(bpy.data.filepath)), "scripts")
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# === 清除內嵌 region_loader ===
if "region_loader" in bpy.data.texts:
    print("[safe import] 發現內嵌 region_loader Text，正在刪除...")
    bpy.data.texts.remove(bpy.data.texts["region_loader"])
if "json_watcher" in bpy.data.texts:
    print("[safe import] 發現內嵌 region_loader Text，正在刪除...")
    bpy.data.texts.remove(bpy.data.texts["json_watcher"])
# === 匯入必要模組 ===
import region_loader
import json_watcher
importlib.reload(region_loader)
importlib.reload(json_watcher)
from region_loader import RegionLoader
from json_watcher import JSONWatcher


# === 設定 ===
JSON_PATH = "//../jason/uav_from_sionna.json"  # 相對於 .blend
INTERVAL = 1.0

REGION_MAP = {
    "A": {"blend": "//nycu0.blend", "coll": "RegionRoot1", "pos": (0.0, 0.0, 0.0)},
    "B": {"blend": "//nycu1.blend", "coll": "RegionRoot2", "pos": (1100.0, 0.0, 0.0)},
    "C": {"blend": "//nycu2.blend", "coll": "RegionRoot3", "pos": (-900.0, 0.0, 0.0)},
}

# === 狀態 ===
loader = RegionLoader(verbose=True)
current_state = {}


# === JSON 回調函式 ===
def on_json_update(data):
    """當 JSON 更新時執行的邏輯"""
    if not isinstance(data, dict) or "regions" not in data:
        print("[watch] JSON 結構錯誤，缺少 'regions'")
        return

    regions = data["regions"]
    remove_unlisted = data.get("remove_unlisted", False)

    for region, action in regions.items():
        region = region.strip().upper()
        if region not in REGION_MAP:
            print(f"[watch] 未知區域 '{region}'，跳過。")
            continue

        info = REGION_MAP[region]
        blend_path = bpy.path.abspath(info["blend"])
        coll_name = info["coll"]
        pos = info.get("pos", (0.0, 0.0, 0.0))

        inst_name = f"REGION_{region}_INST"
        inst = bpy.data.objects.get(inst_name)
        col = bpy.data.collections.get(coll_name)
        action = str(action).lower().strip()

        if action == "show" or action == "hide":
    # 若尚未載入，先載入
            if not col:
                print(f"[watch] 載入 {region}（初始狀態: {action}）")
                try:
                    col = loader.load_collection(blend_path, coll_name)
                    inst = loader.create_instance(coll_name, inst_name, visible=(action == "show"))
                    inst.location = pos
                except Exception as e:
                    print(f"[watch] 無法載入 {region}: {e}")
                    continue
            else:
                # 已存在 → 僅切換可見性
                loader.set_visible(inst, (action == "show"))
                print(f"[watch] { '顯示' if action == 'show' else '隱藏' } 區域 {region}")


    # 移除未列出的區域
    if remove_unlisted:
        listed = set(k.strip().upper() for k in regions.keys())
        for key, info in REGION_MAP.items():
            if key not in listed:
                coll_name = info["coll"]
                if coll_name in bpy.data.collections:
                    print(f"[watch] 移除未列出區域 {key}")
                    try:
                        loader.unload(coll_name)
                    except Exception as e:
                        print(f"[watch] 無法移除 {key}: {e}")


# === 啟動監聽 ===
watcher = JSONWatcher(json_path=JSON_PATH, interval=INTERVAL, verbose=True)
watcher.add_callback(on_json_update)
watcher.start()
