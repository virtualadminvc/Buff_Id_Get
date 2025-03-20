import json
import os
import sys
import time
import requests
from datetime import datetime
######################

class BuffCollector:
    def __init__(self):
        self.base_url = "https://buff.163.com"
        self.session = requests.Session()
        self.headers = self.setup_headers()
        self.page_size = 20
        self.request_interval = 10
        self.output_dir = "BuffData"
        self.state_file = os.path.join(self.output_dir, "collector.state")

        os.makedirs(self.output_dir, exist_ok=True)
        self.categories = self.load_categories()
        self.current_task = {
            'mode': None,  # all/file/single
            'targets': [],
            'progress': 0,
            'file_name': None
        }

    def setup_headers(self):
        """从配置文件加载headers信息"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                cookie = config.get('cookie')
                csrf_token = config.get('csrf_token')
                if not cookie or not csrf_token:
                    raise ValueError("Cookie或CSRF Token未在配置文件中设置")
        except FileNotFoundError:
            print("配置文件config.json不存在，请参考模板创建")
            sys.exit(1)
        except Exception as e:
            print(f"配置加载失败: {e}")
            sys.exit(1)

        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}/market/csgo",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": cookie,
            "X-CSRFToken": csrf_token
        }

    def safe_input(self, prompt):
        """跨平台安全输入方法"""
        try:
            return input(prompt)
        except UnicodeDecodeError:
            print("输入编码错误，请使用英文输入")
            return ""
        except Exception as e:
            print(f"输入错误: {str(e)}")
            return ""

    def load_categories(self):
        try:
            with open('category_mapping.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [sub['value'] for cat in data for sub in cat['sub_categories']]
        except Exception as e:
            print(f"分类加载失败: {e}")
            return []

    def interactive_mode(self):
        """交互式界面"""
        try:
            while True:
                print("\n" + "=" * 40)
                print(" BUFF数据采集工具 ".center(40, "★"))
                print("=" * 40)

                if self.load_state():
                    self.handle_existing_task()
                    continue

                mode = self.ask_question(
                    "请选择采集模式:",
                    ["全量采集", "指定分类", "文件采集"],
                    allow_exit=True
                )
                if mode == 0:
                    return False
                elif mode == 1:
                    self.handle_full_mode()
                elif mode == 2:
                    self.handle_single_mode()
                elif mode == 3:
                    self.handle_file_mode()
        except KeyboardInterrupt:
            return False
        return True


    def handle_existing_task(self):
        """处理存在的未完成任务"""
        file_info = ""
        if self.current_task['mode'] == 'file':
            file_info = f" ({self.current_task.get('file_name', '未知文件')})"

        print(f"\n发现未完成的任务: {self.current_task['mode']}模式{file_info}")
        print(f"进度: {self.current_task['progress'] + 1}/{len(self.current_task['targets'])}")

        choice = self.ask_question(
            "请选择操作:",
            ["继续任务", "清除任务并开始新任务"],
            allow_exit=True
        )

        if choice == 0:
            self.clean_exit()
        elif choice == 1:
            self.start_collection()
        else:
            self.clear_state()

    def clean_exit(self):
        """清理退出"""
        self.clear_state()
        print("\n 用户主动退出")
        sys.exit(0)
    def handle_full_mode(self):
        """全量采集模式"""
        self.current_task = {
            'mode': 'all',
            'targets': self.categories,
            'progress': 0
        }
        self.start_collection()
    def handle_single_mode(self):
        """指定分类模式"""
        while True:
            print("\n可用分类列表:")
            for i, cat in enumerate(self.categories, 1):
                print(f"{i}. {cat}")
            print("0. 返回主菜单")

            try:
                choice = int(self.safe_input("\n请输入分类编号: "))
                if choice == 0:
                    return
                if 1 <= choice <= len(self.categories):
                    target = self.categories[choice - 1]
                    self.current_task = {
                        'mode': 'single',
                        'targets': [target],
                        'progress': 0
                    }
                    self.start_collection()
                    return
                print("编号超出范围")
            except ValueError:
                print("请输入数字")

    def handle_file_mode(self):
        """文件采集模式"""
        choice = self.ask_question(
            "请选择要使用的分类文件:",
            ["duplicates.txt (重复分类)", "diff_categories_count.txt (差异分类)"],
            allow_exit=True
        )

        if choice == 0:
            return

        file_map = {
            1: "duplicates.txt",
            2: "diff_categories_count.txt"
        }

        filename = file_map.get(choice)
        if not filename:
            print("无效选择")
            return

        if not os.path.exists(filename):
            print(f"文件 {filename} 不存在，请确保文件在当前目录")
            return

        content = self.read_file_with_fallback(filename)
        if not content:
            return

        targets = [line.strip() for line in content if line.strip()]
        invalid = set(targets) - set(self.categories)

        if invalid:
            print(f"发现无效分类: {', '.join(invalid)}")
            return

        self.current_task = {
            'mode': 'file',
            'targets': targets,
            'progress': 0,
            'file_name': filename
        }
        self.start_collection()

    def read_file_with_fallback(self, path):
        """安全读取文件"""
        try:
            with open(path, 'rb') as f:
                raw = f.read()
                for enc in ['utf-8', 'gbk', 'utf-16']:
                    try:
                        return raw.decode(enc).splitlines()
                    except UnicodeDecodeError:
                        continue
                print("文件编码无法识别，请保存为UTF-8格式")
                return None
        except Exception as e:
            print(f"文件读取失败: {str(e)}")
            return None

    def ask_question(self, prompt, options, allow_exit=False):
        """增强版提问方法"""
        print(f"\n{prompt}")
        for i, opt in enumerate(options, 1):
            print(f" {i}. {opt}")
        if allow_exit:
            print(" 0. 退出程序")

        while True:
            try:
                choice = int(self.safe_input("\n请输入选项数字: "))
                if allow_exit and choice == 0:
                    return 0
                if 1 <= choice <= len(options):
                    return choice
                print(f"请输入有效数字 (1-{len(options)}{', 0退出' if allow_exit else ''})")
            except ValueError:
                print("请输入数字")

    def start_collection(self):
        """启动采集流程"""
        try:
            total = len(self.current_task['targets'])
            start_idx = self.current_task['progress']

            for idx in range(start_idx, total):
                self.current_task['progress'] = idx
                self.save_state()

                category = self.current_task['targets'][idx]
                print(f"\n正在采集 ({idx + 1}/{total}): {category}")
                self.process_category(category)

            print("\n所有任务已完成！")
            self.clear_state()
        except KeyboardInterrupt:
            self.handle_interrupt()

    def handle_interrupt(self):
        """处理中断事件 - 修改后自动保存"""
        print("\n 采集已中断，自动保存进度...")
        try:
            self.save_state()
            print(f"进度已保存至: {self.state_file}")
        except Exception as e:
            print(f"保存失败: {str(e)}")
        finally:
            sys.exit(0)

    # def ask_yesno(self, prompt):
    #     """安全的是/否提问"""
    #     for _ in range(3):
    #         answer = self.safe_input(f"{prompt} (Y/N): ").lower()
    #         if answer in ['y', 'yes']:
    #             return True
    #         if answer in ['n', 'no']:
    #             return False
    #         print("请输入 Y 或 N")
    #     return False

    def process_category(self, category):
        """处理单个分类"""
        try:
            collected_items = []
            # 获取第一页数据
            first_page = self.fetch_page(category, 1)
            if not first_page or not first_page.get('items'):
                print(f"无有效数据: {category}")
                return

            # 提取总数量
            total_count = first_page.get('total_count', 0)
            collected_items.extend(self._format_items(first_page.get('items', [])))

            # 处理后续页面
            total_page = first_page.get('total_page', 1)
            for page in range(2, total_page + 1):
                page_data = self.fetch_page(category, page)
                if page_data and page_data.get('items'):
                    collected_items.extend(self._format_items(page_data.get('items', [])))
                    print(f"已获取第 {page}/{total_page} 页")

            # 保存格式化数据
            self.save_data(category, collected_items, total_count)
        except Exception as e:
            print(f"采集失败: {str(e)}")

    def _format_items(self, items):
        """标准化数据格式"""
        formatted = []
        for item in items:
            if all(key in item for key in ['id', 'market_hash_name']):
                formatted.append({
                    "id": item['id'],
                    "hashname": item['market_hash_name'],
                    "shortname": item.get('short_name', "")
                })
            else:
                print(f"跳过无效数据条目: {item.get('id', '未知ID')}")
        return formatted

    def fetch_page(self, category, page):
        """API请求"""
        try:
            params = {
                'game': 'csgo',
                'page_num': page,
                'page_size': self.page_size,
                'category': category,
                '_': int(time.time() * 1000)
            }

            resp = self.session.get(
                f"{self.base_url}/api/market/goods",
                params=params,
                headers=self.headers,
                timeout=20
            )

            if resp.status_code == 403:
                print("认证失效，请更新cookies")
                return None

            resp.raise_for_status()
            return resp.json().get('data')
        except Exception as e:
            print(f"请求失败: {str(e)}")
            return None
        finally:
            time.sleep(self.request_interval)

    def save_data(self, category, items, total_count):
        """保存标准化JSON数据"""
        try:
            path = os.path.join(self.output_dir, f"{category}.json")
            result = {
                "meta": {
                    "collection_time": datetime.now().isoformat(),
                    "total_count": total_count,
                    "collected": len(items),
                    "success_rate": f"{(len(items) / total_count) * 100:.2f}%" if total_count else "0.00%"
                },
                "items": items
            }

            # 数据有效性校验
            if total_count > 0 and len(items) > total_count:
                print(f"数据异常: 采集数量({len(items)})超过总数({total_count})")
                result['items'] = items[:total_count]
                result['meta']['collected'] = total_count
                result['meta']['success_rate'] = "100.00%"

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"数据已保存: {category}")

        except Exception as e:
            print(f"保存失败: {str(e)}")

    def save_state(self):
        """保存状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_task, f)
        except Exception as e:
            print(f"状态保存失败: {str(e)}")

    def load_state(self):
        """加载状态"""
        if not os.path.exists(self.state_file):
            return False

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.current_task = json.load(f)
                return True
        except Exception as e:
            print(f"状态加载失败: {str(e)}")
            return False

    def clear_state(self):
        """清除状态"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

def main():
    try:
        # Windows系统编码设置

        if sys.platform.startswith('win'):
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCP(65001)
            kernel32.SetConsoleOutputCP(65001)

        BuffCollector().interactive_mode()
    except Exception as e:
        print(f"系统错误: {str(e)}")
    finally:
        if __name__ == "__main__" and sys.stdin.isatty():
            input("\n按 Enter 键退出...")

if __name__ == "__main__":
    main()