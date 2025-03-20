import json
from pathlib import Path
from datetime import datetime

# 颜色配置
COLORS = {
    "id": "\033[92m",  # 绿色
    "name": "\033[93m",  # 黄色
    "category": "\033[94m",  # 蓝色
    "reset": "\033[0m"
}


def process_final_extract():
    """精确处理数据并生成指定格式"""
    print("\n\033[1m开始处理FinalExtract数据...\033[0m")
    print("=" * 40)

    # 初始化数据结构
    result = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "total_items": 0,
            "total_categories": 0,
            "categories": {}
        },
        "data": []
    }

    try:
        extract_path = Path("FinalExtract")
        if not extract_path.exists():
            raise FileNotFoundError("FinalExtract目录不存在")

        # 遍历所有JSON文件
        for json_file in extract_path.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 提取关键数据
            category = data['meta']['category']
            items = data['data']

            # 更新统计
            result['meta']['categories'][category] = len(items)
            result['meta']['total_items'] += len(items)
            result['meta']['total_categories'] = len(result['meta']['categories'])

            # 构建data条目并输出到控制台
            for item in items:
                entry = {
                    "goods_id": item['goods_id'],
                    "shortname": item['shortname']
                }
                result['data'].append(entry)

                # 带颜色控制台输出
                print(
                    f"{COLORS['id']}{item['goods_id']}{COLORS['reset']} | "
                    f"{COLORS['name']}{item['shortname']}{COLORS['reset']} | "
                    f"{COLORS['category']}{category}{COLORS['reset']}"
                )
                print("-" * 80)

        # 保存文件
        with open("id.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print("\n\033[1m处理完成！生成文件：id.json\033[0m")
        print(f"总分类数：{result['meta']['total_categories']}")
        print(f"总物品数：{result['meta']['total_items']}")
        return True

    except Exception as e:
        print(f"\n\033[91m处理失败：{str(e)}\033[0m")
        return False


if __name__ == "__main__":
    process_final_extract()