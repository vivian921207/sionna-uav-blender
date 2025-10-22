import bpy

# === 1. UAV 顏色設定 ===
obj = bpy.data.objects.get("UAV")
if obj:
    obj.color = (1.0, 0.2, 0.1, 1.0)  # 紅橙色 UAV
    obj.show_name = True
    obj.show_in_front = True
else:
    print("⚠ 找不到 UAV 物件，請確認是否存在。")



# === 3. 材質顏色設定 ===
for mat in bpy.data.materials:
    name = mat.name.lower()
    if "wall" in name:
        mat.diffuse_color = (0.7, 0.7, 0.7, 1.0)  # 淺灰牆
    elif "roof" in name:
        mat.diffuse_color = (1.0, 0.5, 0.3, 1.0)  # 橙紅屋頂
    elif "uav" in name:
        mat.diffuse_color = (0.4, 1.0, 0.4, 1.0)  # 橙紅屋頂

# === 4. 修正視覺化模式（顯示物件顏色 / 材質顏色）===
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                # 若想看物件顏色改成 'OBJECT'，若想看材質顏色用 'MATERIAL'
                space.shading.color_type = 'MATERIAL'
                space.shading.type = 'SOLID'
                break

print("✅ UAV、Region、材質顏色已全部設定完成！")
