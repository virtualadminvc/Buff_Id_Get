import json
import time
import os
import requests
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)


class BuffCategoryCounter:
    def __init__(self, request_interval=4):
        self.base_url = "https://buff.163.com"
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/market/csgo",
            "X-Requested-With": "XMLHttpRequest"
        }

        # 从配置文件加载凭证
        config = self._load_config()
        self._setup_cookies(
            session=config["session"],
            csrf_token=config["csrf_token"]
        )

        self.category_mapping = self.load_category_mapping()
        self.output_dir = "BuffStats"
        os.makedirs(self.output_dir, exist_ok=True)
        self.request_interval = max(request_interval, 4)
        self.max_retries = 3
        self.final_retry = 2
        self.retry_interval = 5

    def _load_config(self):
        """从config.json加载凭证配置"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 解析session值
            cookie_parts = config["cookie"].split(";")
            session = None
            for part in cookie_parts:
                if "session=" in part:
                    session = part.split("session=")[1].strip()
                    break

            if not session:
                raise ValueError("config.json中缺少session值")

            return {
                "session": session,
                "csrf_token": config["csrf_token"]
            }

        except FileNotFoundError:
            raise Exception("config.json文件不存在")
        except KeyError as e:
            raise Exception(f"config.json缺少必要字段: {str(e)}")
        except Exception as e:
            raise Exception(f"配置文件加载失败: {str(e)}")

    def _setup_cookies(self, session: str, csrf_token: str):
        self.session.cookies.update({
            'session': session,
            'csrf_token': csrf_token
        })
        self.headers.update({
            'X-CSRFToken': csrf_token,
            'Cookie': f'session={session}; csrf_token={csrf_token}'
        })

    def get_category_index(self):
        """生成带分类名称的编号列表"""
        index = []
        category_id = 1
        for main_cat in self.category_mapping:
            main_name = main_cat['main_category']
            for sub_cat in main_cat['sub_categories']:
                index.append({
                    'id': category_id,
                    'main': main_name,
                    'sub': sub_cat['name'],
                    'value': sub_cat['value']
                })
                category_id += 1
        return index

    def show_category_list(self):
        """显示带分类名称的编号列表"""
        index_list = self.get_category_index()

        print(f"\n{Fore.CYAN}=== 详细分类列表 ===")
        for i, cat in enumerate(index_list):
            if i % 5 == 0 and i != 0:
                print()

            main_name = cat['main'][:3]
            sub_name = cat['sub'][:6]
            output = f"{cat['id']}-{main_name}·{sub_name}".ljust(20)
            print(f"{Fore.YELLOW}{output}", end='')

        print(f"\n\n{Fore.CYAN}总分类数量: {len(index_list)}")

    def load_category_mapping(self):
        try:
            with open('category_mapping.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Fore.RED}🚨 分类文件加载失败: {str(e)}")
            return []

    def _get_all_categories(self):
        return [
            sub['value']
            for main in self.category_mapping
            for sub in main['sub_categories']
        ]

    def get_category_total(self, category_value: str) -> int:
        retries = self.max_retries
        last_count = -1

        while retries > 0:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/market/goods",
                    params={
                        'game': 'csgo',
                        'page_num': 1,
                        'page_size': 1,
                        'category': category_value
                    },
                    headers=self.headers,
                    timeout=15
                )

                if response.status_code == 403:
                    return -1

                data = response.json().get('data', {})
                current_count = data.get('total_count', 0)
                last_count = current_count
                break

            except Exception as e:
                retries -= 1
                time.sleep(2)
            finally:
                time.sleep(self.request_interval)

        return last_count if retries > 0 else -2

    def process_categories(self, categories: list, full_update=False):
        output_path = os.path.join(self.output_dir, "ActualCategoryCount.json")
        report = self._load_existing_report() if not full_update else {}

        stats = {
            'success': 0,
            'empty': 0,
            'failed': 0
        }
        retry_candidates = []

        for idx, cat in enumerate(categories, 1):
            print(f"[{idx}/{len(categories)}] {cat.ljust(30)}", end='')

            count = self.get_category_total(cat)

            if count > 0:
                report[cat] = count
                stats['success'] += 1
                print(f"{Fore.GREEN} ✓ 数量: {count}")
                self._save_progress(report)
            elif count == 0:
                retry_candidates.append(cat)
                stats['empty'] += 1
                print(f"{Fore.YELLOW} ⚠ 空分类")
            else:
                stats['failed'] += 1
                print(f"{Fore.RED} ✗ 失败")

            time.sleep(self.request_interval)

        if retry_candidates:
            print(f"\n{Fore.YELLOW} 开始重试 {len(retry_candidates)} 个空分类")
            for attempt in range(1, self.final_retry + 1):
                print(f"{Fore.CYAN}▶ 第 {attempt} 次重试")
                temp_retry = []

                for cat in retry_candidates:
                    print(f"   重试: {cat.ljust(30)}", end='')
                    count = self.get_category_total(cat)

                    if count > 0:
                        report[cat] = count
                        stats['success'] += 1
                        stats['empty'] -= 1
                        print(f"{Fore.GREEN} ✓ 数量: {count}")
                        self._save_progress(report)
                    elif count == 0:
                        temp_retry.append(cat)
                        print(f"{Fore.YELLOW} ⚠ 仍为空")
                    else:
                        stats['failed'] += 1
                        print(f"{Fore.RED} ✗ 失败")

                    time.sleep(self.retry_interval)

                retry_candidates = temp_retry
                if not retry_candidates:
                    break

        self._save_final_report(report)

    def _load_existing_report(self):
        output_path = os.path.join(self.output_dir, "ActualCategoryCount.json")
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_progress(self, new_data):
        output_path = os.path.join(self.output_dir, "ActualCategoryCount.json")

        full_report = self._load_existing_report()
        full_report.update(new_data)

        current_sum = sum(v for k, v in full_report.items() if k not in ("Sum", "更新日期"))
        full_report["Sum"] = current_sum
        full_report["更新日期"] = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False)

    def _save_final_report(self, report):
        output_path = os.path.join(self.output_dir, "ActualCategoryCount.json")

        final_report = self._load_existing_report()
        final_report.update(report)

        final_report["Sum"] = sum(v for k, v in final_report.items() if k not in ("Sum", "更新日期"))
        final_report["更新日期"] = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)

        print(f"\n{Fore.GREEN} 统计完成！")
        print(f" 处理分类数: {len(report)}")
        print(f" 商品总数: {final_report['Sum']}")
        print(f" 文件路径: {Fore.BLUE}{output_path}")


def show_menu():
    print(f"\n{Fore.CYAN}=== BUFF 商品统计工具 ===")
    print(f"{Fore.YELLOW}1. 全部分类统计")
    print(f"{Fore.YELLOW}2. 指定单个/多个分类")
    print(f"{Fore.YELLOW}3. 从文件读取分类列表")
    print(f"{Fore.RED}0. 退出程序")
    return input(f"{Fore.GREEN}请输入选项数字：")


def show_file_menu():
    print(f"\n{Fore.CYAN}=== 请选择要读取的文件 ===")
    print(f"{Fore.YELLOW}1. diff_categories_count.txt")
    print(f"{Fore.YELLOW}2. duplicates.txt")
    print(f"{Fore.RED}0. 返回上级菜单")
    return input(f"{Fore.GREEN}请输入选项数字：")


def read_selected_file(choice):
    files = {
        '1': 'diff_categories_count.txt',
        '2': 'duplicates.txt'
    }
    filename = files.get(choice)
    if not filename:
        return None
    if not os.path.exists(filename):
        print(f"{Fore.RED}文件 {filename} 不存在！")
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"{Fore.RED}读取文件失败: {str(e)}")
        return None


def get_interval():
    while True:
        try:
            interval = int(input(f"{Fore.BLUE}请输入请求间隔秒数（最小4秒）："))
            return max(4, interval)
        except ValueError:
            print(f"{Fore.RED}请输入有效数字！")


def validate_categories(input_cats, valid_cats):
    invalid = [cat for cat in input_cats if cat not in valid_cats]
    if invalid:
        print(f"{Fore.RED}无效分类: {', '.join(invalid)}")
        return False
    return True


def main():
    counter = None
    all_valid_categories = []

    try:
        while True:
            choice = show_menu()

            if choice == '0':
                print(f"{Fore.MAGENTA}再见！")
                break

            elif choice == '1':
                interval = get_interval()
                counter = BuffCategoryCounter(interval)
                all_valid_categories = counter._get_all_categories()
                counter.process_categories(all_valid_categories, full_update=True)

            elif choice == '2':
                interval = get_interval()
                counter = BuffCategoryCounter(interval)
                counter.show_category_list()
                all_categories = counter._get_all_categories()
                index_list = counter.get_category_index()
                all_valid_categories = [cat['value'] for cat in index_list]

                print(f"\n{Fore.CYAN}可用分类ID范围: 1-{len(index_list)}")
                input_nums = input(f"{Fore.BLUE}请输入分类编号（多个用逗号分隔，示例：1,3,5）: ").split(',')
                selected_cats = []

                for num in input_nums:
                    num = num.strip()
                    if not num.isdigit():
                        print(f"{Fore.RED}无效输入: '{num}' 不是数字")
                        continue

                    index = int(num) - 1
                    if 0 <= index < len(all_categories):
                        selected_cats.append(all_categories[index])
                    else:
                        print(f"{Fore.RED}无效编号: {num} (有效范围1-{len(all_categories)})")

                if not selected_cats:
                    print(f"{Fore.RED}未选择有效分类！")
                    continue

                if validate_categories(selected_cats, all_valid_categories):
                    counter.process_categories(selected_cats)

            elif choice == '3':
                while True:
                    file_choice = show_file_menu()
                    if file_choice == '0':
                        break
                    if file_choice not in ('1', '2'):
                        print(f"{Fore.RED}无效选项，请重新输入！")
                        continue

                    interval = get_interval()
                    counter = BuffCategoryCounter(interval)
                    all_valid_categories = counter._get_all_categories()

                    file_cats = read_selected_file(file_choice)
                    if not file_cats:
                        continue

                    if validate_categories(file_cats, all_valid_categories):
                        counter.process_categories(file_cats)
                    break

            else:
                print(f"{Fore.RED}无效选项，请重新输入！")

    except Exception as e:
        print(f"{Fore.RED}发生致命错误: {str(e)}")
        print(f"{Fore.YELLOW}请检查config.json配置是否正确")


if __name__ == "__main__":
    main()