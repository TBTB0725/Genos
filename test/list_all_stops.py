"""
打印波士顿所有地铁/轻轨站点
类型 0 = 轻轨 (Green Line)
类型 1 = 地铁 (Red, Orange, Blue)
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
    print("=" * 60)
    print("🚇 波士顿地铁/轻轨站点列表")
    print("=" * 60)
    
    stops = get_all_stops()
    
    print(f"\n共找到 {len(stops)} 个站点\n")
    print(f"{'序号':<5} {'站点ID':<25} {'站点名称':<30}")
    print("-" * 60)
    
    for i, stop in enumerate(stops, 1):
        stop_id = stop["id"]
        name = stop["attributes"]["name"]
        print(f"{i:<5} {stop_id:<25} {name:<30}")
    
    print("-" * 60)
    print(f"总计: {len(stops)} 个站点")


if __name__ == "__main__":
    main()