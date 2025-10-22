import bpy, os

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
