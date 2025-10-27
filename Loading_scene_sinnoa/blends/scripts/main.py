# === JSON 監聽並自動載入對應 .blend + UAV移動 (Blender 3.x/4.x) ===
import bpy, os, sys, importlib
import json

class RegionLoader:
    """
    用於從外部 .blend 載入指定 Collection 並建立 Collection Instance。
    使用 link=True：資料仍位於外部檔。
    """

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.cache = {}  # {collection_name: (collection, instance)}

    def load_collection(self, blend_path, coll_name):
        """從指定的 .blend 檔案載入 Collection"""
        blend = bpy.path.abspath(blend_path)
        blend = os.path.abspath(blend)
        if not os.path.exists(blend):
            raise FileNotFoundError(f"找不到 .blend 檔案：{blend}")

        if self.verbose:
            print(f"[RegionLoader] 正在載入 {blend} 中的集合 {coll_name}")

        with bpy.data.libraries.load(blend, link=True) as (data_from, data_to):
            if coll_name not in data_from.collections:
                raise ValueError(f"[RegionLoader] 檔案中無此集合: {coll_name}\n可用集合: {list(data_from.collections)}")
            data_to.collections = [coll_name]

        col = bpy.data.collections.get(coll_name)
        if not col:
            raise RuntimeError(f"[RegionLoader] 無法在 bpy.data.collections 中取得 {coll_name}")

        self.cache[coll_name] = (col, None)
        return col

    def create_instance(self, coll_name, instance_name=None, visible=True):
        """
        為已載入的集合建立 Collection Instance。
        若同名實例已存在，則重用它而不重新建立。
        """
        if coll_name not in self.cache:
            raise KeyError(f"[RegionLoader] 尚未載入集合 {coll_name}")

        col, _ = self.cache[coll_name]
        if instance_name is None:
            instance_name = f"INST__{coll_name}"

        # ✅ 若同名實例已存在，直接重用
        exist = bpy.data.objects.get(instance_name)
        if exist and exist.instance_collection == col:
            if self.verbose:
                print(f"[RegionLoader] 重用現有實例：{instance_name}")
            self.set_visible(exist, visible)
            self.cache[coll_name] = (col, exist)
            return exist

        # 若無現有實例才建立新的
        inst = bpy.data.objects.new(instance_name, None)
        inst.instance_type = 'COLLECTION'
        inst.instance_collection = col
        bpy.context.scene.collection.objects.link(inst)
        self.set_visible(inst, visible)

        self.cache[coll_name] = (col, inst)
        if self.verbose:
            print(f"[RegionLoader] 建立新實例：{instance_name}")
        return inst


    def set_visible(self, inst, visible=True):
        """設定實例是否顯示（viewport + render）。"""
        if not inst:
            return
        inst.hide_viewport = not visible
        inst.hide_render = not visible

    def unload(self, coll_name):
        """移除指定集合與其實例（若存在）。"""
        if coll_name not in self.cache:
            return
        col, inst = self.cache[coll_name]
        if inst and inst.name in bpy.data.objects:
            bpy.data.objects.remove(inst, do_unlink=True)
        if col and col.users == 0:
            bpy.data.collections.remove(col, do_unlink=True)
        if self.verbose:
            print(f"[RegionLoader] 已釋放 {coll_name}")
        self.cache.pop(coll_name, None)
class JSONWatcher:
    """
    通用 JSON 檔監聽器。
    每次檔案更新時自動呼叫 callback(json_data)。
    """
    def __init__(self, json_path, interval=1.0, verbose=True):
        self.json_path = bpy.path.abspath(json_path)
        self.interval = interval
        self.verbose = verbose
        self.running = False
        self.last_mtime = 0.0
        self._callbacks = []

    def add_callback(self, func):
        self._callbacks.append(func)

    def _read_json(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            if self.verbose:
                print(f"[watch] 讀取 JSON 失敗：{e}")
            return None

    def _timer(self):
        if not self.running:
            return None

        if not os.path.exists(self.json_path):
            if self.verbose:
                print(f"[watch] 找不到 JSON：{self.json_path}")
            return self.interval

        mtime = os.path.getmtime(self.json_path)
        if mtime <= self.last_mtime:
            return self.interval

        self.last_mtime = mtime
        data = self._read_json()
        if data is None:
            return self.interval

        if self.verbose:
            print(f"[watch] JSON 更新，觸發 {len(self._callbacks)} 個 callback")

        for cb in self._callbacks:
            try:
                cb(data)
            except Exception as e:
                print(f"[watch] callback 執行錯誤：{e}")

        return self.interval

    def start(self):
        if self.running:
            print("[watch] 已在監聽中。")
            return
        self.running = True
        self.last_mtime = 0.0
        bpy.app.timers.register(self._timer, first_interval=0.2)
        print(f"[watch] 開始監聽 {self.json_path}")

    def stop(self):
        self.running = False
        print("[watch] 停止監聽。")



# === 設定 ===
JSON_PATH = "//../jason/uav_from_sionna.json"  # 相對於 .blend
INTERVAL = 0.1  # 檢查頻率（秒）

REGION_MAP = {
    "A": {"blend": "//nycu.blend", "coll": "RegionRoot1", "pos": (0.0, 0.0, 0.0)},
    "B": {"blend": "//nycu_right.blend", "coll": "RegionRoot2", "pos": (1300.0, 0.0, 0.0)},
    "C": {"blend": "//nycu_left.blend", "coll": "RegionRoot3", "pos": (-1300.0, 0.0, 0.0)},
}

# === 狀態 ===
loader = RegionLoader(verbose=True)


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


# === 回調 2：控制 UAV 移動 ===
def on_uav_update(data):
    """依據 data['uav'] 控制 UAV 物體的位置"""
    if not isinstance(data, dict) or "uav" not in data:
        return

    uav = data["uav"]
    if not isinstance(uav, dict):
        return

    x = float(uav.get("x", 0.0))
    y = float(uav.get("y", 0.0))
    z = float(uav.get("z", 0.0))

    obj = bpy.data.objects.get("UAV")  # 物件名稱可自行更改
    if obj is None:
        print("[uav-watch] 找不到物件 'UAV'")
        return

    obj.location = (x, y, z)
    print(f"[uav-watch] UAV → ({x:.2f}, {y:.2f}, {z:.2f})")


# === 啟動單一 JSON 監聽，但綁兩個 callback ===
def start_watch():
    watcher = JSONWatcher(json_path=JSON_PATH, interval=INTERVAL, verbose=True)
    watcher.add_callback(on_region_update)
    watcher.add_callback(on_uav_update)
    watcher.start()
    print(f"[main] 已啟動監聽：{bpy.path.abspath(JSON_PATH)}")
    return watcher


# === 自動啟動 ===
watcher = start_watch()
