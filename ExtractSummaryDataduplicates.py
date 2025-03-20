import os
import json


def extract_duplicate_names():
    """增强版重复数据提取"""
    from pathlib import Path
    # 固定文件路径
    input_path = Path("SummaryData") / "duplicates.json"
    if not input_path.exists():
        print(f"错误：找不到输入文件 {input_path}")
        return

    # 读取文件
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
    except Exception as e:
        print(f"文件处理失败: {str(e)}")
        return

    # 处理数据
    unique_names = set()

    # 遍历每个重复条目
    for entry in report_data:
        # 提取该重复项涉及的所有文件名（不带扩展名）
        for filename in entry.get('files', []):
            name = os.path.splitext(filename)[0]
            unique_names.add(name)

    # 写入文件
    output_file = "duplicates.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for name in sorted(unique_names):
            f.write(name + "\n")

    print(f"成功生成 {output_file}")
    print(f"共提取 {len(unique_names)} 个重复文件名")


if __name__ == "__main__":
    extract_duplicate_names()