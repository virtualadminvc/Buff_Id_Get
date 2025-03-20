import json


def load_json_data(file_path):
    """加载JSON文件并返回字典数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载文件 {file_path} 失败: {str(e)}")
        return {}


def compare_category_counts():
    # 文件路径配置
    actual_path = "./BuffStats/ActualCategoryCount.json"
    final_path = "./BuffStats/FinalCount.json"
    output_path = "./diff_categories_count.txt"

    # 加载数据
    actual_data = load_json_data(actual_path)
    final_data = load_json_data(final_path)

    # 排除不需要比较的字段
    exclude_fields = {"Sum", "更新日期"}

    # 获取所有需要比较的键（并集）
    all_keys = set(actual_data.keys()).union(final_data.keys())
    compare_keys = [key for key in all_keys if key not in exclude_fields]

    # 找出差异项
    diff_categories = []
    for key in compare_keys:
        actual_val = actual_data.get(key)
        final_val = final_data.get(key)

        # 当存在以下情况时视为差异：
        # 1. 键只存在于一个文件中
        # 2. 值不同
        if actual_val != final_val:
            diff_categories.append(key)

    # 写入输出文件
    if diff_categories:
        with open(output_path, 'w', encoding='utf-8') as f:
            for category in diff_categories:
                f.write(f"{category}\n")
        print(f"发现 {len(diff_categories)} 个差异分类，已写入 {output_path}")
    else:
        print("没有发现差异分类")

    return diff_categories


if __name__ == "__main__":
    compare_category_counts()