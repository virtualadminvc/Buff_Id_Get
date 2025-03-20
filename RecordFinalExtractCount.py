import os
import json
from datetime import datetime


def count_goods_ids():
    # 初始化统计字典
    result = {}
    total = 0

    # 设置输出文件夹
    output_folder = "BuffStats"
    os.makedirs(output_folder, exist_ok=True)  # 确保文件夹存在

    # 遍历目标文件夹
    folder_path = "FinalExtract"
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)

            try:
                # 读取JSON文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 获取商品ID数量
                count = len(data.get("data", []))

                # 使用文件名作为分类名（去掉扩展名）
                category = os.path.splitext(filename)[0]
                result[category] = count
                total += count

            except Exception as e:
                print(f"处理文件 {filename} 时出错: {str(e)}")
                continue

    # 添加汇总数据和更新日期
    result["Sum"] = total
    result["更新日期"] = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    # 写入结果文件到BuffStats文件夹
    output_path = os.path.join(output_folder, "FinalCount.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    count_goods_ids()
    print("统计完成，结果已保存到 BuffStats/FinalCount.json")