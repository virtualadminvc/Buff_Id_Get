import json
import requests
import time
current_timestamp = int(time.time() * 1000)
def load_accounts():
    accounts = []

    # 加载config.json账号
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            accounts.append({
                'name': 'config账号',
                'cookie': config['cookie'],
                'csrf_token': config['csrf_token']
            })
    except Exception as e:
        print(f"加载config.json失败: {str(e)}")

    # 加载auth.json账号
    try:
        with open('auth.json', 'r', encoding='utf-8') as f:
            auth = json.load(f)
            cookies = []
            for entry in auth['cookies']:
                if entry['domain'] == 'buff.163.com' and entry['name'] in ['session', 'csrf_token']:
                    cookies.append(f"{entry['name']}={entry['value']}")
            cookie_str = '; '.join(cookies)

            csrf_token = next((e['value'] for e in auth['cookies'] if e['name'] == 'csrf_token'), None)

            accounts.append({
                'name': 'auth账号',
                'cookie': cookie_str,
                'csrf_token': csrf_token
            })
    except Exception as e:
        print(f"加载auth.json失败: {str(e)}")

    return accounts


def check_frozen_status(account):
    url = "https://buff.163.com/api/market/goods"
    params = {
        "game": "csgo",
        "use_suggestion": 0,
        "_": current_timestamp
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Cookie": account['cookie'],
        "X-CSRFToken": account['csrf_token']
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        result = response.json()
        print(f"\n{account['name']}检测结果:")
        print("原始响应:", result)

        if result.get('code') == "User Frozen":
            print(" 状态: 账号冻结（User Frozen）")
            print("详细信息:", result.get('error', '无附加信息'))
        elif result.get('code') == "Action Forbidden":
            print(" 状态: 功能限制（Action Forbidden）")
            print("详细信息:", result.get('error', '无附加信息'))
        else:
            print(" 状态: 账号正常")
            if 'data' in result:
                print("检测到有效商品数据，接口访问正常")

    except requests.exceptions.RequestException as e:
        print(f"?请求异常: {str(e)}")
    except json.JSONDecodeError:
        print("响应不是有效的JSON格式")


def main():
    print("开始账号冻结检测...")
    accounts = load_accounts()

    if not accounts:
        print("没有可用的账号配置")
        return

    for account in accounts:
        print("\n" + "=" * 40)
        print(f" 正在检测账号: {account['name']} ")
        print("=" * 40)
        check_frozen_status(account)


if __name__ == "__main__":
    main()