import bpy, json, os

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

        