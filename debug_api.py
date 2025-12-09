"""
调试脚本：检查 API 实际返回什么
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

MBTA_API_KEY = os.getenv("MBTA_API_KEY")
BASE_URL = "https://api-v3.mbta.com"

def get_headers():
    return {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}


def debug_predictions(stop_id: str, route_id: str = None):
    """详细打印 API 返回内容"""
    print(f"\n{'='*50}")
    print(f"调试: stop_id={stop_id}, route_id={route_id}")
    print("=" * 50)
    
    params = {
        "filter[stop]": stop_id,
        "sort": "arrival_time",
    }
    
    if route_id:
        params["filter[route]"] = route_id
    
    print(f"\n请求 URL: {BASE_URL}/predictions")
    print(f"请求参数: {params}")
    
    response = requests.get(
        f"{BASE_URL}/predictions",
        params=params,
        headers=get_headers()
    )
    
    print(f"\n响应状态码: {response.status_code}")
    
    data = response.json()
    
    predictions = data.get("data", [])
    print(f"预测数量: {len(predictions)}")
    
    if not predictions:
        print("\n⚠️  API 返回空数据！")
        print("可能原因:")
        print("  1. 线路停运/维修")
        print("  2. 不在运营时间")
        print("  3. 站点 ID 错误")
    else:
        print("\n前 5 条预测:")
        for i, pred in enumerate(predictions[:5], 1):
            attrs = pred["attributes"]
            arrival = attrs.get("arrival_time") or attrs.get("departure_time") or "无时间"
            route = pred["relationships"]["route"]["data"]["id"]
            direction = attrs.get("direction_id", "?")
            status = attrs.get("status", "")
            print(f"  {i}. 线路={route}, 方向={direction}, 到达={arrival}, 状态={status}")
    
    # 检查是否有 alerts（服务警报）
    print(f"\n{'='*50}")
    print("检查服务警报...")
    print("=" * 50)
    
    alerts_params = {}
    if route_id:
        alerts_params["filter[route]"] = route_id
    
    alerts_response = requests.get(
        f"{BASE_URL}/alerts",
        params=alerts_params,
        headers=get_headers()
    )
    
    alerts_data = alerts_response.json()
    alerts = alerts_data.get("data", [])
    
    if alerts:
        print(f"\n⚠️  发现 {len(alerts)} 条警报:")
        for alert in alerts[:5]:
            attrs = alert["attributes"]
            header = attrs.get("header", "无标题")
            effect = attrs.get("effect", "")
            print(f"\n  📢 {effect}: {header}")
    else:
        print("\n✅ 没有服务警报")


if __name__ == "__main__":
    # 测试 Babcock Street Green-B
    debug_predictions("place-babck", "Green-B")
    
    # 测试 Harvard Avenue Green-B
    debug_predictions("70130", "Green-B")
    
    # 也测试红线（应该正常）
    debug_predictions("place-harsq", "Red")