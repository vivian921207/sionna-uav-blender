import sys
sys.path.append(r"E:\NYCU\topic2\test_to_blend\scripts")

from region_loader import RegionLoader

loader = RegionLoader(verbose=True)

# 1) 載入集合
colA = loader.load_collection(r"E:\NYCU\topic2\test_to_blend\blends\1.blend", "RegionRoot")

# 2) 建立 instance
instA = loader.create_instance("RegionRoot", "REGION_A_INST", visible=True)

# 3) 若要再載入另一個分區
colB = loader.load_collection(r"E:\NYCU\topic2\test_to_blend\blends\2.blend", "RegionRoot2")
instB = loader.create_instance("RegionRoot2", "REGION_B_INST", visible=True)

# 4) 瞬間切換
#loader.switch(instA, instB)

# 5) 卸載（若不再需要）
# loader.unload("RegionRoot")
