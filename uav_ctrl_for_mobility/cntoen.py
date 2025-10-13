import os
import shutil
import xml.etree.ElementTree as ET

# 路徑
xml_path = r"NYCU_scene/NYCU.xml"      # 你的 XML
mesh_dir = r"NYCU_scene/meshes"        # .ply 的目錄

# 中文 → 英文 對照表（可自行補齊/調整）
name_map = {
    "小木屋鬆餅": "WaffleHouse",
    "工程三館": "EngineeringBuilding3",
    "工程四館": "EngineeringBuilding4",
    "工程五館": "EngineeringBuilding5",
    "工程六館": "EngineeringBuilding6",
    "科學一館": "ScienceBuilding1",
    "科學三館": "ScienceBuilding3",
    "中正堂": "ZhongzhengHall",
    "浩然圖書資訊中心": "Library",
    "交映樓": "JiaoyingBuilding",
    "田家炳光電大樓": "OptoBuilding",
    "資訊技術服務中心": "ITServiceCenter",
    "管理二館": "ManagementBuilding2",
    "24k": "24k",   # 已是英文
}

def transliterate(s: str) -> str:
    """把 value 內的中文片段換成英文，並把反斜線換成正斜線"""
    out = s.replace("\\", "/")
    for zh, en in name_map.items():
        if zh in out:
            out = out.replace(zh, en)
    return out

# 備份
bak = xml_path + ".bak"
if not os.path.exists(bak):
    shutil.copy2(xml_path, bak)
    print(f"[備份] 已建立 {bak}")

# 讀 XML 並修改
tree = ET.parse(xml_path)
root = tree.getroot()

total = 0
changed = 0
unchanged_examples = []

for elem in root.findall(".//string[@name='filename']"):
    total += 1
    old = elem.get("value")
    new = transliterate(old)
    if new != old:
        print(f"XML: {old}  →  {new}")
        elem.set("value", new)
        changed += 1
    else:
        if any(ord(c) > 127 for c in old):  # 仍含非 ASCII
            unchanged_examples.append(old)

# 寫回（覆寫原檔）
tree.write(xml_path, encoding="utf-8", xml_declaration=True)
print(f"\n[結果] 找到 {total} 個 filename，實際修改 {changed} 個。")

if unchanged_examples:
    print("\n[提醒] 仍含中文但未被改到的路徑（可能對照表少了對應）：")
    for v in sorted(set(unchanged_examples)):
        print("  -", v)

# 重新命名實體 .ply 檔
renamed = 0
for fname in os.listdir(mesh_dir):
    new_name = transliterate(fname)
    if new_name != fname:
        src = os.path.join(mesh_dir, fname)
        dst = os.path.join(mesh_dir, new_name)
        print(f"Rename: {fname}  →  {new_name}")
        os.rename(src, dst)
        renamed += 1

print(f"\n[檔案重新命名] 共重新命名 {renamed} 個 .ply 檔。")
