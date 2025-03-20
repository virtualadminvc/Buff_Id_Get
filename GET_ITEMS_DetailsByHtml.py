import os
import json
import math
import sys
import re
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

OUTPUT_DIR = 'BuffDataByExtractHTML'


class BuffHTMLCollector:
    def __init__(self):
        self.OUTPUT_DIR = OUTPUT_DIR
        self.state_file = os.path.join(self.OUTPUT_DIR, 'collector.state')
        self.categories = []
        self.current_task = {
            'mode': None,
            'targets': [],
            'progress': 0,
            'file_name': None
        }
        self.delay = 3
        self.headless = False
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        self.load_state()


    def interactive_mode(self):
        """交互式入口"""
        print("\n" + "=" * 40)
        print(" BUFF HTML数据采集工具 ".center(40, "★"))
        print("=" * 40)

        if self.current_task['mode']:
            self.handle_existing_task()
            return

        if self.check_data_files():
            mode = self.ask_question(
                "请选择采集模式:",
                [
                    "全量采集（所有分类）",
                    "指定单个分类",
                    "文件采集（选择预设文件）"
                ],
                allow_zero=True,
                exit_on_zero=True
            )
            if mode == 0:
                return False
            elif mode == 1:
                self.handle_full_mode()
            elif mode == 2:
                self.handle_single_mode()
            else:
                self.handle_file_mode()

    def exit_program(self):
        """安全退出程序"""
        print("\n正在退出程序...")
        self.save_state()
        sys.exit(0)
    def check_data_files(self):
        """检查数据文件完整性"""
        data_dir = 'BuffData'
        if not os.path.exists(data_dir):
            print(f"数据目录 {data_dir} 不存在")
            return False

        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        if not json_files:
            print(f"目录 {data_dir} 中没有JSON文件")
            return False

        print(f"找到 {len(json_files)} 个分类文件")
        return True

    def load_state(self):
        """加载未完成任务状态"""
        if not os.path.exists(self.state_file):
            return False

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)
                # 验证状态完整性
                if all(key in saved_state for key in ['mode', 'targets', 'progress']):
                    self.current_task = saved_state
                    return True
                print("状态文件不完整，已忽略")
                return False
        except Exception as e:
            print(f"状态加载失败: {str(e)}")
            return False

    def handle_full_mode(self):
        """全量采集模式"""
        self.load_valid_categories()
        if not self.categories:
            return

        self.current_task = {
            'mode': 'all',
            'targets': self.categories,
            'progress': 0
        }
        self.start_collection()

    def handle_existing_task(self):
        """处理未完成任务"""
        file_info = f"({self.current_task['file_name']})" if self.current_task['mode'] == 'file' else ""
        print(f"\n🔍 发现未完成任务: {self.current_task['mode']}模式 {file_info}")
        print(f"进度: {self.current_task['progress']}/{len(self.current_task['targets'])}")

        choice = self.ask_question(
            "请选择操作:",
            ["继续任务", "放弃任务并重新开始"],
            allow_zero=True
        )
        if choice == 0:
            self.interactive_mode()
        elif choice == 2:
            self.clear_state()
            self.current_task = {'mode': None, 'targets': [], 'progress': 0}
            self.interactive_mode()
        else:
            self.start_collection()

    def handle_single_mode(self):
        """指定单个分类模式（修正q键处理）"""
        self.load_valid_categories()
        if not self.categories:
            return

        print("\n可用分类列表:")
        for i, cat in enumerate(self.categories, 1):
            print(f"{i:>3}. {cat}")

        while True:
            try:
                prompt = f"\n请输入分类编号 (0返回主菜单，1-{len(self.categories)}，q退出): "
                choice = input(prompt).strip().lower()

                if choice == 'q':
                    self.interactive_mode()  # 新增返回主菜单
                    return
                if choice == '0':
                    self.interactive_mode()
                    return

                choice_num = int(choice)
                if 1 <= choice_num <= len(self.categories):
                    target = self.categories[choice_num - 1]
                    self.current_task = {
                        'mode': 'single',
                        'targets': [target],
                        'progress': 0
                    }
                    self.start_collection()
                    return
                print(f"请输入1~{len(self.categories)}之间的数字")
            except ValueError:
                print("必须输入数字")

    def handle_file_mode(self):
        """文件采集模式"""
        choice = self.ask_question(
            "请选择要使用的分类文件:",
            [
                "duplicates.txt (重复分类)",
                "diff_categories_count.txt (差异分类)"
            ],
            allow_zero=True
        )
        if choice == 0:
            self.interactive_mode()
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
            print(f"文件 {filename} 不存在")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            targets = [line.strip() for line in f if line.strip()]

        self.load_valid_categories()
        valid_targets = []
        for t in targets:
            if t in self.categories:
                valid_targets.append(t)
            else:
                print(f"跳过无效分类: {t}")

        if not valid_targets:
            print("没有有效分类可采集")
            return

        self.current_task = {
            'mode': 'file',
            'targets': valid_targets,
            'progress': 0,
            'file_name': filename
        }
        self.start_collection()

    def load_valid_categories(self):
        """加载有效分类列表"""
        data_dir = 'BuffData'
        raw_files = os.listdir(data_dir)
        self.categories = []

        for f in raw_files:
            if f.endswith('.json') and not f.startswith('_'):
                category = f.split('.')[0]
                json_path = os.path.join(data_dir, f)
                if self.validate_json_file(json_path):
                    self.categories.append(category)

        self.categories.sort()
        print(f"加载到 {len(self.categories)} 个有效分类")

    def validate_json_file(self, path):
        """验证JSON文件有效性"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'meta' in data and 'items' in data:
                    return True
            print(f"文件格式异常: {os.path.basename(path)}")
            return False
        except Exception as e:
            print(f"文件损坏: {os.path.basename(path)} - {str(e)}")
            return False

    def ask_question(self, prompt, options, allow_zero=False, exit_on_zero=False):
        """增强版提问方法，支持退出选项"""
        print(f"\n{prompt}")
        zero_label = "退出程序" if exit_on_zero else "返回主菜单"
        if allow_zero:
            print(f" 0. {zero_label}")
        for i, opt in enumerate(options, 1):
            print(f" {i}. {opt}")

        max_opt = len(options)
        valid_range = f"0~{max_opt}" if allow_zero else f"1~{max_opt}"

        while True:
            try:
                choice = input(f"\n请输入选项数字 ({valid_range}): ").strip()
                if not choice:
                    raise ValueError

                choice_num = int(choice)
                if allow_zero and choice_num == 0:
                    return 0
                if 1 <= choice_num <= max_opt:
                    return choice_num
                print(f"❌ 请输入{valid_range}之间的数字")
            except ValueError:
                print("❌ 必须输入有效数字")

    def clear_state(self):
        """清除任务状态"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            print("已清除任务状态")
    def start_collection(self):
        """增强的采集流程"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    channel="msedge",
                    headless=self.headless,
                    slow_mo=int(self.delay * 1000)
                )
                context = browser.new_context(
                    storage_state="auth.json" if os.path.exists("auth.json") else None
                )
                page = context.new_page()

                if not self.login_check(page):
                    print("登录失败，终止采集")
                    return

                targets = self.current_task['targets']
                total = len(targets)

                # 断点续采逻辑
                for idx in range(self.current_task['progress'], total):
                    category = targets[idx]
                    print(f"\n处理进度 ({idx + 1}/{total}): {category}")

                    if self.process_category(page, category):
                        self.current_task['progress'] = idx + 1
                        self.save_state()  # 每个分类完成后保存
                    else:
                        print(f"跳过分类 {category}")

                print("\n所有任务完成！")
                self.clear_state()

        except KeyboardInterrupt:
            print("\n用户中断操作...")
            self.save_state()
            print(f"进度已保存至: {self.state_file}")
            sys.exit(0)
        except Exception as e:
            print(f"发生错误: {str(e)}")
            self.save_state()

    def save_state(self):
        """保存当前进度到状态文件"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_task, f, indent=2)
        except Exception as e:
            print(f"\n状态保存失败: {str(e)}")

    def login_check(self, page):
        """登录检查（集成冻结检测）"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            # 访问市场页面检测登录状态
            page.goto("https://buff.163.com/market/csgo", timeout=60000)

            # 检测登录按钮是否存在
            login_selector = "a[onclick='loginModule.showLogin()']"
            if page.locator(login_selector).count() == 0:
                # 已登录状态，进行账号状态检测
                if self.check_account_status(page):
                    print("登录状态有效且账号正常")
                    return True
                else:
                    # 账号异常处理
                    print("检测到账号异常，执行登出流程...")
                    self.force_logout(page)
                    retry_count += 1
                    continue

            # 需要登录流程
            print("需要登录...")
            page.goto("https://buff.163.com/account/login", timeout=30000)
            input("请手动完成登录后按 Enter 继续...")

            # 保存登录状态
            page.context.storage_state(path="auth.json")

            # 二次登录验证
            page.goto("https://buff.163.com/market/csgo")
            if page.locator(login_selector).count() > 0:
                print("登录验证失败")
                retry_count += 1
                continue

            # 检测新登录的账号状态
            if self.check_account_status(page):
                return True
            else:
                self.force_logout(page)
                retry_count += 1

        print("超过最大重试次数，登录失败")
        return False

    def check_account_status(self, page):
        """使用Playwright的API请求检测账号状态"""
        timestamp = int(time.time() * 1000)
        api_url = f"https://buff.163.com/api/market/goods?game=csgo&use_suggestion=0&_={timestamp}"

        try:
            # 使用当前页面上下文发送API请求
            response = page.context.request.get(api_url)
            if not response.ok:
                print(f"状态检测请求失败，状态码：{response.status}")
                return False

            data = response.json()
            print("账号状态检测结果：", data)

            # 解析异常状态
            error_code = data.get("code")
            error_msg = data.get("error", "")
            if error_code in ["User Frozen", "Action Forbidden"] or "被冻结" in error_msg:
                print(f"账号异常状态：{error_code} - {error_msg}")
                return False

            # 验证数据有效性
            if data.get("code") == "OK" and "data" in data:
                print("账号状态正常且接口有效")
                return True

            print("未知响应格式，建议人工检查")
            return False
        except Exception as e:
            print(f"状态检测异常：{str(e)}")
            return False

    def force_logout(self, page):
        """强制登出并清理凭证"""
        print("执行强制登出...")
        page.goto("https://buff.163.com/account/logout")

        # 清理登录凭证
        if os.path.exists("auth.json"):
            os.remove("auth.json")
            print("已清除本地登录凭证")

        # 清除浏览器上下文
        page.context.clear_cookies()
        print("已清除浏览器Cookies")
    def process_category(self, page, category):
        """处理单个分类（增加状态保存）"""
        json_path = os.path.join('BuffData', f'{category}.json')
        if not os.path.exists(json_path):
            print(f"数据文件不存在: {json_path}")
            return False

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total = data['meta']['total_count']
                pages = math.ceil(total / 20)
        except Exception as e:
            print(f"文件读取失败: {str(e)}")
            return False

        print(f"总页数: {pages}")
        category_items = []

        for page_num in range(1, pages + 1):
            print(f"正在处理第 {page_num}/{pages} 页", end='\r')
            try:
                url = f"https://buff.163.com/market/csgo#game=csgo&page_num={page_num}&category={category}"
                page.goto(url, timeout=30000)
                self.wait_for_loading(page)
                html = page.content()
                items = self.parse_html(html)
                category_items.extend(items)
                time.sleep(self.delay)
            except Exception as e:
                print(f"\n页面 {page_num} 处理失败: {str(e)}")
                continue

        return self.save_category_data(category, category_items, pages)

    def wait_for_loading(self, page):
        """等待页面加载完成"""
        try:
            page.wait_for_selector('ul.card_csgo li', state='attached', timeout=20000)
            for _ in range(2):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
        except Exception as e:
            print(f"⚠加载异常: {str(e)}")

    def save_category_data(self, category, items, total_pages):
        """保存分类数据"""
        output_path = os.path.join(OUTPUT_DIR, f'{category}.json')
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "meta": {
                        "category": category,
                        "total_pages": total_pages,
                        "total_items": len(items)
                    },
                    "data": items
                }, f, ensure_ascii=False, indent=2)
            print(f"\n成功保存 {len(items)} 条数据到 {output_path}")
            return True
        except Exception as e:
            print(f"\n保存失败: {str(e)}")
            return False

    @staticmethod
    def parse_html(html):
        """解析商品数据"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []

        for li in soup.select('ul.card_csgo li'):
            try:
                a_tag = li.find('a', href=re.compile(r'/goods/\d+'))
                if not a_tag:
                    continue

                goods_id = re.search(r'/goods/(\d+)', a_tag['href']).group(1)
                title = a_tag.get('title', '').strip()

                items.append({
                    "goods_id": goods_id,
                    "shortname": title,
                })
            except Exception as e:
                print(f"解析异常: {str(e)}")
        return items


def main():
    try:
        if sys.platform.startswith('win'):
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCP(65001)
            kernel32.SetConsoleOutputCP(65001)

        collector = BuffHTMLCollector()
        collector.interactive_mode()
    except Exception as e:
        print(f"发生严重错误: {str(e)}")
    finally:
        if __name__ == "__main__":
            # 根据任务状态显示完成提示
            if collector and collector.current_task['mode']:
                print("\nHTML解析完成")
            elif collector and collector.current_task['mode'] is None:
                print("\n已取消所有操作")
            if sys.stdin.isatty():
                input("\n按 Enter 键退出...")

if __name__ == "__main__":
    main()