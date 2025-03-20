#生成category_mapping.json，最开始的文件
from bs4 import BeautifulSoup
import json

def extract_categories(html_content):
    """从HTML中提取所有分类名称和值"""
    soup = BeautifulSoup(html_content, 'lxml')
    categories = []

    # 定位主分类容器
    main_container = soup.find('div', {'id': 'j_h1z1-selType'})

    # 遍历每个主分类
    for category_div in main_container.find_all('div', class_='item'):
        # 获取主分类名称
        main_category = category_div.p.text.strip()

        # 遍历子分类
        sub_items = []
        sub_ul = category_div.find('ul', class_='cols') or category_div.find('ul')
        if sub_ul:
            for li in sub_ul.find_all('li'):
                sub_items.append({
                    "name": li.text.strip(),
                    "value": li['value']
                })

        categories.append({
            "main_category": main_category,
            "sub_categories": sub_items
        })

    return categories


if __name__ == "__main__":
    # 加载本地保存的HTML文件
    with open('buff_market.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 执行提取
    result = extract_categories(html)

    # 保存结果
    with open('category_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 打印统计信息
    total_main = len(result)
    total_sub = sum(len(cat['sub_categories']) for cat in result)
    print(f"提取完成！共找到 {total_main} 个主分类，{total_sub} 个子分类")
    print("示例数据：")
    print(json.dumps(result[0]['sub_categories'][:2], indent=2, ensure_ascii=False))