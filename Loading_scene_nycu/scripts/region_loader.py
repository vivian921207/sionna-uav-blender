# region_loader.py
import bpy, json, os

class RegionLoader:
    """
    用於從外部 .blend 載入指定 Collection 並建立 Collection Instance。
    使用 link=True：資料仍位於外部檔。
    """

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.cache = {}  # {collection_name: (collection, instance)}

    def load_collection(self, blend_path, coll_name):
        """
        從指定的 .blend 載入 Collection。
        回傳: bpy.types.Collection
        """
        blend = os.path.abspath(blend_path)
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
        回傳: bpy.types.Object (instance)
        """
        if coll_name not in self.cache:
            raise KeyError(f"[RegionLoader] 尚未載入集合 {coll_name}")

        col, inst = self.cache[coll_name]
        if instance_name is None:
            instance_name = f"INST__{coll_name}"

        # 若已存在可用的 instance，直接重用
        exist = bpy.data.objects.get(instance_name)
        if exist and exist.instance_collection == col:
            self.set_visible(exist, visible)
            self.cache[coll_name] = (col, exist)
            return exist

        inst = bpy.data.objects.new(instance_name, None)
        inst.instance_type = 'COLLECTION'
        inst.instance_collection = col
        bpy.context.scene.collection.objects.link(inst)
        self.set_visible(inst, visible)

        self.cache[coll_name] = (col, inst)
        return inst

    def set_visible(self, inst, visible=True):
        """設定實例是否顯示（viewport + render）。"""
        if not inst:
            return
        inst.hide_viewport = not visible
        inst.hide_render = not visible

    def switch(self, inst_from, inst_to):
        """在兩個實例之間瞬間切換。"""
        self.set_visible(inst_from, False)
        self.set_visible(inst_to, True)

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
# === 通用 JSON 監聽器 (Blender 3.x/4.x) ===
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
        self._callbacks = []  # 儲存多個反應函數

    # 註冊回調函數
    def add_callback(self, func):
        """註冊當 JSON 變動時要執行的函數，函數需接受一個參數 data。"""
        self._callbacks.append(func)

    # 嘗試讀取 JSON
    def _read_json(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            if self.verbose:
                print(f"[watch] 讀取 JSON 失敗：{e}")
            return None

    # Blender timer callback
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
