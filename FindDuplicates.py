import os
import json
from collections import defaultdict

def analyze_ids():
    # 获取用户输入路径
    folder_path = input("请输入JSON文件夹路径：").strip()

    # 验证路径有效性
    if not os.path.isdir(folder_path):
        print("错误：路径不存在或不是文件夹")
        return

    # 询问是否启用缺失hashname检测
    enable_check = input("是否检测缺失hashname的条目？(Y/N): ").strip().upper() == 'Y'

    # 初始化统计数据
    total_counter = defaultdict(int)
    file_stats_list = []
    global_ids = []
    missing_hashname = []  # 存储缺失hashname的记录

    # 处理每个JSON文件
    for filename in os.listdir(folder_path):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(folder_path, filename)
        file_ids = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # 提取所有可能的ID字段（兼容混合结构）
                items = []
                if 'data' in data:  # 提取第一种结构
                    items = data['data']
                elif 'items' in data:  # 提取第二种结构
                    items = data['items']
                else:
                    raise ValueError("未找到data/items字段")

                # 遍历所有条目
                for item in items:
                    # 检测缺失hashname的情况
                    if enable_check and 'hashname' not in item:
                        # 获取ID（优先goods_id，其次id）
                        item_id = str(item.get('goods_id') or item.get('id', '未知ID')).strip()
                        # 获取shortname
                        shortname = item.get('shortname', '未知名称').strip()
                        # 记录缺失条目
                        missing_hashname.append(f"{item_id} | {shortname}")

                    # 处理ID统计逻辑
                    for id_key in ['id', 'goods_id']:
                        if id_key in item:
                            # 统一转换为字符串并去除空格
                            raw_value = item[id_key]
                            item_id = str(raw_value).strip()

                            # 记录ID
                            file_ids.append(item_id)
                            global_ids.append(item_id)
                            total_counter[item_id] += 1

                # 统计当前文件
                unique_ids = set(file_ids)
                duplicates = len(file_ids) - len(unique_ids)

                file_stats = {
                    'filename': filename,
                    'total': len(file_ids),
                    'unique': len(unique_ids),
                    'duplicates': duplicates,
                    'duplicate_details': defaultdict(int)
                }

                # 记录文件内重复情况
                counter = defaultdict(int)
                for item_id in file_ids:
                    counter[item_id] += 1
                for k, v in counter.items():
                    if v > 1:
                        file_stats['duplicate_details'][k] = v

                file_stats_list.append(file_stats)

                # 打印当前文件结果
                print(f"\n文件：{filename}")
                print(f"总ID数量：{file_stats['total']}")
                print(f"唯一ID数量：{file_stats['unique']}")
                print(f"重复数量：{file_stats['duplicates']}")

                if file_stats['duplicates'] > 0:
                    print("重复明细：")
                    for id, count in file_stats['duplicate_details'].items():
                        print(f"  ID {id} 重复 {count} 次")

        except Exception as e:
            print(f"\n处理文件 {filename} 时出错：{str(e)}")
            continue

    # 保存缺失hashname的记录（如果启用）
    if enable_check:
        if missing_hashname:
            output_file = "ShouldFindHashname.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(missing_hashname))
            print(f"\n发现 {len(missing_hashname)} 条缺失hashname的记录，已保存到 {output_file}")
        else:
            print("\n所有条目均包含hashname字段")

    # 打印全局统计
    print("\n" + "=" * 50)
    print("全局统计：")
    print(f"处理文件总数：{len(file_stats_list)}")
    print(f"总ID数量：{len(global_ids)}")
    print(f"全局唯一ID数量：{len(set(global_ids))}")
    print(f"总重复次数（包含跨文件）：{len(global_ids) - len(set(global_ids))}")
    print(f"存在重复的ID数量（跨文件）：{sum(1 for count in total_counter.values() if count > 1)}")

if __name__ == "__main__":
    analyze_ids()