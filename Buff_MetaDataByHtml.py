import os
import json
from datetime import datetime
from collections import defaultdict

INPUT_DIR = 'BuffDataByExtractHTML'
OUTPUT_DIR = 'SummaryDataByHtml'


def process_summary():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_items = []
    item_registry = defaultdict(list)

    # 读取并合并所有数据
    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(INPUT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                items = data['data']
                all_items.extend(items)

                # 记录商品来源信息
                for item in items:
                    item_registry[item['goods_id']].append({
                        "file": filename,
                        "item": item
                    })
            except Exception as e:
                print(f"解析文件 {filename} 失败: {str(e)}")
                continue

    # 去重逻辑：保留每个goods_id的第一个出现项
    seen_ids = {}
    summary_data = []
    for item in all_items:
        goods_id = item['goods_id']
        if goods_id not in seen_ids:
            seen_ids[goods_id] = True
            summary_data.append(item)

    # 检测重复项
    duplicates = []
    for goods_id, records in item_registry.items():
        if len(records) > 1:
            duplicates.append({
                "goods_id": goods_id,
                "count": len(records),
                "files": [r['file'] for r in records],
                "sample_item": records[0]['item']
            })

    # 生成最终文件
    for filename, data in [('summary.json', summary_data), ('duplicates.json', duplicates)]:
        output_path = os.path.join(OUTPUT_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "meta": {
                    "generated_time": datetime.now().isoformat(),
                    "total_items": len(data),
                    "duplicate_count": len(duplicates)
                },
                "data": data
            }, f, ensure_ascii=False, indent=2)

    # 打印统计信息
    print(f"生成文件：")
    print(f"- 主文件：{os.path.join(OUTPUT_DIR, 'summary.json')}")
    print(f"- 重复记录：{os.path.join(OUTPUT_DIR, 'duplicates.json')}")
    print(
        f"统计：共处理 {len(all_items)} 条原始数据，去重后保留 {len(summary_data)} 条，发现 {len(duplicates)} 个重复商品ID")


if __name__ == "__main__":
    process_summary()