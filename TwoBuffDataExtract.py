import os
import json
import sys
from datetime import datetime
from time import perf_counter
from colorama import init, Fore, Back, Style
from RecordFinalExtractCount import count_goods_ids  # 导入统计函数

init(autoreset=True)  # 初始化颜色输出

class IncrementalMerger:
    def __init__(self):
        self.source_dirs = {
            'buff': 'BuffData',
            'extract': 'BuffDataByExtractHTML'
        }
        self.final_dir = 'FinalExtract'
        os.makedirs(self.final_dir, exist_ok=True)
        self.colors = {
            'header': Fore.CYAN + Style.BRIGHT,
            'success': Fore.GREEN,
            'warning': Fore.YELLOW,
            'error': Fore.RED,
            'progress': Fore.BLUE,
            'stats': Fore.MAGENTA
        }

    def interactive_mode(self):
        """交互式主界面"""
        print(f"\n{self.colors['header']}{'='*40}")
        print(f"{self.colors['header']}{' 数据合并工具 '.center(40, '★')}")
        print(f"{self.colors['header']}{'='*40}")

        while True:
            choice = self.show_main_menu()
            if choice == 1:
                self.process_all_categories()
            elif choice == 2:
                self.process_file_categories()
            elif choice == 3:
                self.process_single_category()
            else:
                break

    def show_main_menu(self):
        """显示主菜单"""
        return self.show_numbered_menu([
            "合并所有分类",
            "通过文件合并",
            "选择单个分类",
            "退出程序"
        ])

    def show_numbered_menu(self, options):
        """通用数字菜单"""
        print("\n请选择操作：")
        for idx, opt in enumerate(options, 1):
            print(f" {idx}. {opt}")

        while True:
            try:
                choice = int(input("\n请输入数字选择："))
                if 1 <= choice <= len(options):
                    return choice
                print("输入无效，请重新输入")
            except ValueError:
                print("请输入数字")

    def process_all_categories(self):
        """处理全部分类"""
        categories = self._get_all_categories()
        print(f"\n即将合并 {len(categories)} 个分类...")
        self.process_categories(categories)

    def process_file_categories(self):
        """处理文件分类"""
        file_choice = self.show_numbered_menu([
            "duplicates.txt",
            "diff_categories_count.txt"
        ])

        files = {
            1: "duplicates.txt",
            2: "diff_categories_count.txt"
        }
        filename = files.get(file_choice)

        if not filename or not os.path.exists(filename):
            print(f"文件 {filename} 不存在")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            categories = [line.strip() for line in f if line.strip()]

        print(f"\n从 {filename} 读取到 {len(categories)} 个分类")
        self.process_categories(categories)

    def process_single_category(self):
        """处理单个分类选择（直接显示全部分类）"""
        all_cats = self._get_all_categories()
        total_cats = len(all_cats)

        print(f"\n{self.colors['header']}可用分类列表（共 {total_cats} 个）：")
        for idx, cat in enumerate(all_cats, 1):
            print(f"{idx:3d}. {cat}")

        # 获取用户选择
        while True:
            try:
                choice = int(input(f"\n请输入分类编号（1-{total_cats}）："))
                if 1 <= choice <= total_cats:
                    category = all_cats[choice - 1]
                    print(f"\n{self.colors['progress']}开始处理分类：{category}")
                    self.process_categories([category])
                    return
                print(f"编号无效，请输入 1-{total_cats} 之间的数字")
            except ValueError:
                print("请输入数字")

    def process_categories(self, categories):
        """处理分类列表（无进度条版本）"""
        total = len(categories)
        start_time = perf_counter()
        stats = {
            'added': 0,
            'skipped': 0,
            'errors': 0,
            'total_items': 0
        }

        print(f"\n{self.colors['progress']}开始处理 {total} 个分类...")

        for idx, category in enumerate(categories, 1):
            try:
                result = self.merge_category(category)
                stats['total_items'] += result['total']

                if result['added'] > 0:
                    stats['added'] += result['added']
                    print(
                        f"{self.colors['success']}✔ [{idx}/{total}] {category.ljust(40)} 新增 {result['added']} 个（当前分类条目：{result['total']}）")
                else:
                    stats['skipped'] += 1
                    print(
                        f"{self.colors['warning']}➖ [{idx}/{total}] {category.ljust(40)} 新增 0 个（当前分类条目：{result['total']}）")
            except Exception as e:
                stats['errors'] += 1
                print(f"{self.colors['error']}✖ [{idx}/{total}] {category.ljust(40)} 错误：{str(e)}")

        # 显示统计信息
        elapsed = perf_counter() - start_time
        print(f"\n{self.colors['stats']}合并完成！")
        print(f"{self.colors['stats']}├─ 总耗时: {elapsed:.2f}s")
        print(f"{self.colors['stats']}├─ 新增条目: {stats['added']}")
        print(f"{self.colors['stats']}├─ 跳过分类: {stats['skipped']}")
        print(f"{self.colors['stats']}├─ 错误分类: {stats['errors']}")
        print(f"{self.colors['stats']}└─ 总条目数: {stats['total_items']}")

        # 执行最终统计
        self.execute_final_count()

    def merge_category(self, category):
        """合并单个分类（返回统计结果）"""
        final_data = self._load_final_data(category)
        original_count = len(final_data)

        # 合并数据源
        final_data = self._merge_buff_data(category, final_data)
        final_data = self._merge_extract_data(category, final_data)

        # 保存结果
        new_additions = len(final_data) - original_count
        self._save_final_data(category, final_data)

        return {
            'added': new_additions,
            'total': len(final_data),
            'category': category
        }

    def execute_final_count(self):
        """执行最终的统计函数"""
        print(f"\n{self.colors['progress']}正在更新统计数据...")
        try:
            count_goods_ids()
            print(f"{self.colors['success']}统计数据已更新到 BuffStats/FinalCount.json")
        except Exception as e:
            print(f"{self.colors['error']}统计时发生错误：{str(e)}")

    # 以下是工具方法 ------------------------------------

    def _get_all_categories(self):
        """获取所有有效分类（共129个）"""
        cats = set()
        for d in self.source_dirs.values():
            if os.path.exists(d):
                cats.update(f.split('.')[0] for f in os.listdir(d) if f.endswith('.json'))
        return sorted(cats)

    def _load_final_data(self, category):
        """加载最终数据"""
        final_path = os.path.join(self.final_dir, f"{category}.json")
        if os.path.exists(final_path):
            with open(final_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {item['goods_id']: item for item in data['data']}
        return {}

    def _merge_buff_data(self, category, final_data):
        """合并Buff数据"""
        buff_path = os.path.join(self.source_dirs['buff'], f"{category}.json")
        if not os.path.exists(buff_path):
            return final_data

        with open(buff_path, 'r', encoding='utf-8') as f:
            for item in json.load(f).get('items', []):
                goods_id = str(item['id'])
                if goods_id not in final_data:
                    final_data[goods_id] = {
                        'goods_id': goods_id,
                        'hashname': item.get('hashname'),
                        'shortname': item.get('shortname'),
                        'source': 'BuffData',
                        'created_at': datetime.now().isoformat()
                    }
        return final_data

    def _merge_extract_data(self, category, final_data):
        """合并Extract数据"""
        extract_path = os.path.join(self.source_dirs['extract'], f"{category}.json")
        if not os.path.exists(extract_path):
            return final_data

        with open(extract_path, 'r', encoding='utf-8') as f:
            for item in json.load(f).get('data', []):
                goods_id = str(item.get('goods_id'))
                if goods_id not in final_data:
                    final_data[goods_id] = {
                        'goods_id': goods_id,
                        'shortname': item.get('shortname'),
                        'source': 'ExtractHTML',
                        'created_at': datetime.now().isoformat()
                    }
        return final_data

    def _save_final_data(self, category, data):
        """保存最终数据"""
        output_path = os.path.join(self.final_dir, f"{category}.json")
        output = {
            "meta": {
                "category": category,
                "stats": {
                    "total_items": len(data),
                    "buff_items": sum(1 for v in data.values() if v['source'] == 'BuffData'),
                    "extract_items": sum(1 for v in data.values() if v['source'] == 'ExtractHTML')
                },
                "last_updated": datetime.now().isoformat()
            },
            "data": list(data.values())
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    try:
        # Windows系统编码设置
        if sys.platform.startswith('win'):
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCP(65001)
            kernel32.SetConsoleOutputCP(65001)

        merger = IncrementalMerger()
        merger.interactive_mode()
    except Exception as e:
        print(f"程序异常: {str(e)}")
    finally:
        input("\n按 Enter 键退出...")