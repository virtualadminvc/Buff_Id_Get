import os
import json
from datetime import datetime
from collections import defaultdict


def merge_buffdata(source_dir, output_dir):
    # 初始化数据
    total_count = 0
    collected_ids = set()
    all_items = []
    processed_files = 0
    duplicates = defaultdict(list)
    id_records = defaultdict(lambda: {'count': 0, 'files': set(), 'sample': None})

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 遍历源目录
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith('.json'):
            continue

        filepath = os.path.join(source_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                processed_files += 1

                # 统计总量
                total_count += data.get('meta', {}).get('total_count', 0)

                # 处理items
                for item in data.get('items', []):
                    if 'id' not in item:
                        continue

                    item_id = item['id']
                    if item_id in collected_ids:
                        # 记录重复信息
                        id_records[item_id]['count'] += 1
                        id_records[item_id]['files'].add(filename)
                        duplicates[item_id].append(item)
                    else:
                        # 记录新ID
                        collected_ids.add(item_id)
                        id_records[item_id] = {
                            'count': 1,
                            'files': {filename},
                            'sample': item
                        }
                        all_items.append(item)

        except Exception as e:
            print(f"跳过文件 {filename}，原因: {str(e)}")
            continue

    # 构建汇总数据
    result = {
        "meta": {
            "generated_time": datetime.now().isoformat(),
            "total_count": total_count,
            "collected": len(collected_ids),
            "success_rate": f"{(len(collected_ids) / total_count * 100):.2f}%" if total_count else "0.00%",
            "duplicate_count": len(duplicates)
        },
        "items": sorted(all_items, key=lambda x: x['id'])
    }

    # 生成重复报告
    duplicate_report = []
    for item_id, info in id_records.items():
        if info['count'] > 1:
            duplicate_report.append({
                "id": item_id,
                "count": info['count'],
                "files": list(info['files']),
                "sample_item": info['sample']
            })

    # 定义固定文件名
    summary_file = os.path.join(output_dir, "summary.json")
    report_file = os.path.join(output_dir, "duplicates.json")

    # 写入文件（覆盖原有文件）
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(duplicate_report, f, ensure_ascii=False, indent=2)

    print(f"\n合并完成！")
    print(f"处理文件数: {processed_files}")
    print(f"总物品数: {total_count}")
    print(f"成功收集: {len(collected_ids)}")
    print(f"发现重复: {len(duplicates)}")
    print(f"汇总文件: {os.path.basename(summary_file)}")
    print(f"重复报告: {os.path.basename(report_file)}")


if __name__ == "__main__":
    BUFFDATA_DIR = "BuffData"
    OUTPUT_DIR = "SummaryData"

    if os.path.exists(BUFFDATA_DIR):
        merge_buffdata(BUFFDATA_DIR, OUTPUT_DIR)
    else:
        print(f"错误：目录 {BUFFDATA_DIR} 不存在")