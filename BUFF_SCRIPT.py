import os
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import sys
import os

# 修复标准流（Windows系统）仅生成exe时启用
# if sys.platform.startswith('win'):
#     try:
#         if sys.stdin is None or not sys.stdin.isatty():
#             sys.stdin = open('CONIN$', 'r')
#         if sys.stdout is None or not sys.stdout.isatty():
#             sys.stdout = open('CONOUT$', 'w')
#         if sys.stderr is None or not sys.stderr.isatty():
#             sys.stderr = open('CONOUT$', 'w')
#     except Exception as e:
#         print(f"Error reopening stdio: {e}")
#         sys.exit(1)
# --------------------------
# 核心功能模块
# --------------------------

def validate_category_file(file_path="category_mapping.json", expected_sub=129):
    """验证分类文件有效性"""
    result = {"valid": False, "message": "", "total_main": 0, "total_sub": 0}

    try:
        if not Path(file_path).exists():
            result["message"] = " 分类文件不存在"
            return result

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            result["message"] = " 文件格式错误：顶层结构应为列表"
            return result

        result["total_main"] = len(data)
        result["total_sub"] = sum(len(cat.get("sub_categories", [])) for cat in data)

        if result["total_sub"] < expected_sub:
            result["message"] = f"? 子分类不足（当前：{result['total_sub']}，需要 ≥{expected_sub}）"
            return result

        result["valid"] = True
        result["message"] = f" 验证通过（主分类：{result['total_main']}，子分类：{result['total_sub']}）"
        return result

    except Exception as e:
        result["message"] = f" 文件解析失败：{str(e)}"
        return result


def execute_html_pipeline():
    """HTML采集分析全流程"""
    print("\n HTML数据采集分析")
    print("=" * 40)

    # 检查前置条件
    if not Path("duplicates.txt").exists():
        print(" 需要先执行API采集生成分类文件")
        return False

    try:
        # 执行HTML采集
        print("\n 启动HTML数据采集...")
        from GET_ITEMS_DetailsByHtml import main as html_main
        html_main()

        # 执行HTML数据分析
        print("\n 正在分析HTML数据...")
        from Buff_MetaDataByHtml import process_summary
        process_summary()

        print("\n HTML数据处理完成")
        return True
    except ImportError as e:
        print(f" 缺少依赖文件: {str(e)}")
        return False
    except Exception as e:
        print(f" 处理失败: {str(e)}")
        return False
def generate_category_file():
    """生成分类文件主流程"""
    print("\n? 分类文件生成流程")
    print("="*40)

    # 强制删除旧文件
    category_file = Path("category_mapping.json")
    if category_file.exists():
        category_file.unlink()
        print(" 已清除旧分类文件")

    # 显示操作指南
    print(" 操作步骤：")
    steps = [
        ("1. 访问页面", "https://buff.163.com/market/csgo"),
        ("2. 完全加载页面", "展开所有分类"),
        ("3. 保存网页", "快捷键Ctrl+S → 选择'仅HTML'格式"),
        ("4. 记住保存位置", "推荐保存到桌面或下载目录")
    ]
    for num, desc in steps:
        print(f"{num}: {desc}")

        # 获取HTML路径

    def get_html_path():
        common_paths = [
            Path("buff_market.html"),
            Path.home() / "Downloads/buff_market.html",
            Path.home() / "Desktop/buff_market.html"
        ]
        for p in common_paths:
            if p.exists():
                print(f" 发现HTML文件：{p}")
                if input("? 使用此文件？(Y/N): ").upper() == 'Y':
                    return p

        print("\n 手动指定HTML文件路径（可拖拽文件）：")
        while True:
            path = Path(input("? 文件路径（输入Q退出）: ").strip().strip('"'))
            if path.name.upper() == 'Q':
                print(" 操作取消")
                sys.exit(0)
            if not path.exists():
                print(f" 路径不存在：{path}")
                continue
            if path.is_dir():
                print(f" 需要文件路径，当前是目录：{path}")
                continue
            if path.suffix.lower() not in ['.html', '.htm']:
                print(f" 文件类型错误：需要HTML文件")
                continue
            return path

    # 解析处理
    try:
        html_path = get_html_path()
        print(f"\n 正在解析：{html_path.name}")

        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')

        container = soup.find('div', {'id': 'j_h1z1-selType'})
        if not container:
            raise ValueError("页面结构异常，请确认保存完整页面")

        categories = []
        for div in container.find_all('div', class_='item'):
            main_cat = div.p.text.strip()
            sub_cats = [{
                "name": li.text.strip().replace('\xa0', ' '),
                "value": li.get('value', '')
            } for li in div.find_all('li')]

            categories.append({
                "main_category": main_cat,
                "sub_categories": sub_cats
            })

        # 保存数据
        with open("category_mapping.json", 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

        print(f"\n 文件已更新：{Path('category_mapping.json').absolute()}")
        validation = validate_category_file()
        print(validation["message"])
        return True
    except Exception as e:
        print(f"? 更新失败：{str(e)}")
        sys.exit(1)


# --------------------------
# 数据采集模块
# --------------------------
def update_cookie_config():
    """更新Cookie配置"""
    print("\n 更新Cookie配置")
    print("=" * 40)

    config_file = Path("config.json")
    current_config = {}

    try:
        # 读取现有配置
        if config_file.exists():
            with open(config_file, 'r') as f:
                current_config = json.load(f)
            print("当前配置：")
            print(f"Cookie: {current_config.get('cookie', '未配置')}")
            print(f"CSRF Token: {current_config.get('csrf_token', '未配置')}")
            print("\n" + "-" * 30)
    except Exception as e:
        print(f" 配置文件格式不正确: {str(e)}")

    try:
        # 获取新输入
        new_cookie = input("请输入新的Cookie值（直接回车保留当前）: ").strip()
        new_csrf = input("请输入新的CSRF Token（直接回车保留当前）: ").strip()

        # 更新配置
        if new_cookie:
            current_config["cookie"] = new_cookie
        if new_csrf:
            current_config["csrf_token"] = new_csrf

        # 保存配置
        with open(config_file, 'w') as f:
            json.dump(current_config, f, indent=2)

        print("\n 配置已更新！")
        print(f"文件路径: {config_file.absolute()}")
        return True
    except Exception as e:
        print(f" 保存配置失败: {str(e)}")
        return False
def execute_api_pipeline():
    """API采集全流程"""
    print("\n API数据采集启动")
    print("=" * 40)

    try:
        from BUFF_GET_ALL_ITEMS_DETAILS import main as api_main
        api_main()  # 执行核心采集

        # 自动执行后续处理
        print("\n 启动数据处理流水线...")
        execute_metadata_pipeline()
        return True

    except ImportError:
        print(" 错误：缺少BUFF_GET_ALL_ITEMS_DETAILS.py")
        sys.exit(1)
    except Exception as e:
        print(f" 采集失败：{str(e)}")
        return False


def execute_metadata_pipeline():
    """元数据处理流水线"""
    try:
        from Buff_MetaData import merge_buffdata
        from ExtractSummaryDataduplicates import extract_duplicate_names

        print("\n 正在合并数据...")
        merge_buffdata("BuffData", "SummaryData")

        print("\n 正在提取重复项...")
        extract_duplicate_names()

        print("\n 数据处理完成")
        print("生成文件：")
        print("- SummaryData/summary.json")
        print("- SummaryData/duplicates.json")
        print("- duplicates.txt")
        return True

    except Exception as e:
        print(f" 处理失败：{str(e)}")
        return False


# --------------------------
# 系统功能模块
# --------------------------

def cleanup_system():
    """清除生成文件"""
    targets = [
        "category_mapping.json",
        "duplicates.txt",
        Path("BuffData"),
        Path("SummaryData"),
        Path("BuffDataByExtractHTML"),  # 新增HTML数据目录
        Path("HtmlAnalysis"),           # 新增分析结果目录
        Path("FinalExtract"),
        Path("BuffStats"),
        "diff_categories_count.txt"
    ]

    removed = []
    for target in targets:
        if isinstance(target, Path):
            if target.exists():
                for f in target.glob("*"):
                    f.unlink()
                target.rmdir()
                removed.append(str(target))
        else:
            path = Path(target)
            if path.exists():
                path.unlink()
                removed.append(target)

    if removed:
        print(f"? 已清除：{', '.join(removed)}")
    else:
        print("? 没有可清除的文件")


def execute_actual_count_pipeline():
    """实时统计流程"""
    print("\n 实时数据统计")
    print("=" * 40)

    try:
        from ActualTimeCategoryCount import main as actual_main
        actual_main()  # 执行实时统计

        # 自动执行差异比较
        print("\n 正在比较数据差异...")
        from Find_Count_Not_Equal_Category import compare_category_counts
        compare_category_counts()
        return True
    except ImportError as e:
        print(f" 缺少依赖文件: {str(e)}")
        return False
    except Exception as e:
        print(f" 统计失败: {str(e)}")
        return False

def system_status():
    """获取系统状态"""
    status = []

    # 分类文件状态
    cat_validation = validate_category_file()
    status.append(f"分类文件：{cat_validation['message']}")

    # 数据目录状态
    data_dirs = {
        "BuffData": "原始数据",
        "SummaryData": "汇总数据"
    }
    for dirname, desc in data_dirs.items():
        path = Path(dirname)
        if path.exists() and any(path.iterdir()):
            status.append(f"{desc}： 已存在")
        else:
            status.append(f"{desc}： 未生成")
    config_status = " 已配置" if Path("config.json").exists() else " 未配置"
    status.append(f"Cookie配置：{config_status}")
    # 重复文件
    dup_file = Path("duplicates.txt")
    status.append(f"重复记录：{' 已生成' if dup_file.exists() else ' 未生成'}")
    # HTML数据状态
    html_data = Path("BuffDataByExtractHTML")
    if html_data.exists() and any(html_data.glob("*.json")):
        status.append("HTML数据： 已采集")
        analysis_dir = Path("SummaryDataByHtml")
        status.append(f"HTML分析：{' 已完成' if analysis_dir.exists() else ' 未分析'}")
    else:
        status.append("HTML数据： 未采集")
    final_data = Path("FinalExtract")
    if final_data.exists() and any(final_data.glob("*.json")):
        status.append("合并数据： 已生成")
        count_file = Path("BuffStats/FinalCount.json")
        status.append(f"最终统计：{' 已完成' if count_file.exists() else ' 未生成'}")
    else:
        status.append("合并数据： 未生成")
    actual_file = Path("BuffStats/ActualCategoryCount.json")
    diff_file = Path("diff_categories_count.txt")
    status.extend([
        f"实时统计：{' 已完成' if actual_file.exists() else ' 未执行'}",
        f"差异分析：{' 已生成' if diff_file.exists() else ' 未分析'}"
    ])
    return "\n".join(status)



# 修改execute_merge_pipeline函数
def execute_merge_pipeline():
    """数据合并流程"""
    print("\n 数据合并流程")
    print("=" * 40)
    try:
        from TwoBuffDataExtract import IncrementalMerger
        merger = IncrementalMerger()
        merger.interactive_mode()
        return True
    except ImportError:
        print(" 缺少TwoBuffDataExtract.py文件")
        return False
    except Exception as e:
        print(f" 合并失败: {str(e)}")
        return False
def execute_find_duplicates():
    """执行重复ID分析流程"""
    print("\n 查找重复ID")
    print("=" * 40)
    try:
        from FindDuplicates import analyze_ids
        analyze_ids()  # 直接调用分析函数
        return True
    except ImportError:
        print(" 错误：缺少FindDuplicates.py文件")
        return False
    except Exception as e:
        print(f" 分析失败: {str(e)}")
        return False
# --------------------------
# 主界面模块
# --------------------------
def main_menu():
    """主控制界面"""
    menu = """
========================================
    CS:GO饰品数据管理系统 v5.0
========================================
1. 生成/更新分类文件
2. 执行API采集+分析
3. 执行HTML采集+分析
4. 合并数据源并统计
5. 实时统计+差异分析
6. 清除所有生成文件
7. 更新Cookie配置
8. 查找重复ID
9. 生成ID列表
10. 退出程序
========================================
"""
    print(system_status())
    print(menu)

    print("=" * 40)
    while True:
        choice = input(" 请选择操作 (1-10): ").strip()
        if choice in map(str, range(1, 11)):
            return choice
        print(" 无效输入，请重新选择")


def main():
    """主程序入口"""
    try:
        while True:
            # 直接调用检测模块
            print("\n正在检查账户状态...")
            try:
                from Account_Freeze_Judgment import main as check_accounts
                check_accounts()  # 直接执行检测函数
            except ImportError:
                print(" 账户检测模块加载失败")
                sys.exit(1)
            except Exception as e:
                print(f" 账户检测异常: {str(e)}")
                sys.exit(1)

            choice = main_menu()

            if choice == '1':
                if generate_category_file():
                    input("\n按回车返回主菜单...")

            elif choice == '2':
                if not validate_category_file()["valid"]:
                    print(" 请先生成分类文件")
                    continue
                if execute_api_pipeline():
                    input("\n 按回车返回主菜单...")
            elif choice == '3':
                if execute_html_pipeline():
                    input("\n 按回车返回主菜单...")
            # 选项处理...
            elif choice == '4':
                if execute_merge_pipeline():  # 合并成功后会自动统计
                    input("\n 按回车返回主菜单...")

            elif choice == '5':
                if execute_actual_count_pipeline():
                    input("\n 按回车返回主菜单...")
            elif choice == '6':
                cleanup_system()
                input("\n 按回车返回主菜单...")
            elif choice == '7':
                if update_cookie_config():
                    input("\n 按回车返回主菜单...")
            elif choice == '8':
                if execute_find_duplicates():
                    input("\n 按回车返回主菜单...")
            elif choice == '9':
                try:
                    from GOODS_ID import process_final_extract
                    if process_final_extract():
                        input("\n按回车返回主菜单...")
                except ImportError:
                    print(" 错误：缺少GOODS_ID.py文件")
                except Exception as e:
                    print(f" 生成ID列表失败：{str(e)}")
            elif choice == '10':
                print("\n 感谢使用！")
                sys.exit(0)

    except KeyboardInterrupt:
        print("\n 程序已终止")
        sys.exit(0)


if __name__ == "__main__":
    main()