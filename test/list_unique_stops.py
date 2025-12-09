"""
打印波士顿所有地铁/轻轨站点（去重）
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

MBTA_API_KEY = os.getenv("MBTA_API_KEY")
BASE_URL = "https://api-v3.mbta.com"

def get_headers():
    return {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}


def get_all_stops():
    """获取所有地铁/轻轨站点"""
    response = requests.get(
        f"{BASE_URL}/stops",
        params={"filter[route_type]": "0,1"},
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"错误: {response.status_code}")
        return []
    
    return response.json().get("data", [])


def main():
    print("=" * 40)
    print("🚇 波士顿地铁/轻轨站点（去重）")
    print("=" * 40)
    
    stops = get_all_stops()
    
    # 用 set 去重，只保留站点名称
    unique_names = sorted(set(stop["attributes"]["name"] for stop in stops))
    
    print(f"\n共 {len(unique_names)} 个不重复站点\n")
    
    for i, name in enumerate(unique_names, 1):
        print(f"{i:3}. {name}")
    
    print(f"\n总计: {len(unique_names)} 个站点")


if __name__ == "__main__":
    main()