import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()
MBTA_API_KEY = os.getenv("MBTA_API_KEY")
BASE_URL = "https://api-v3.mbta.com"

def get_headers():
    """返回请求头"""
    return {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}

# ========== 测试 1: 获取所有地铁线路 ==========
def test_get_routes():
    """获取地铁线路"""
    print("\n" + "="*50)
    print("测试 1: 获取地铁线路")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/routes",
        params={"filter[type]": "0,1"},  # 只要地铁和轻轨
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"找到 {len(data['data'])} 条线路:\n")
        for route in data['data']:
            attrs = route['attributes']
            print(f"  {route['id']:12} | {attrs['long_name']}")
    else:
        print(f"错误: {response.status_code}")

# ========== 测试 2: 获取某线路的站点 ==========
def test_get_stops(route_id="Red"):
    """获取某线路的所有站点"""
    print("\n" + "="*50)
    print(f"测试 2: 获取 {route_id} 线的站点")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/stops",
        params={"filter[route]": route_id},
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"找到 {len(data['data'])} 个站点:\n")
        for stop in data['data'][:10]:  # 只显示前10个
            attrs = stop['attributes']
            print(f"  {stop['id']:20} | {attrs['name']}")
        if len(data['data']) > 10:
            print(f"  ... 还有 {len(data['data']) - 10} 个站点")
    else:
        print(f"错误: {response.status_code}")

# ========== 测试 3: 搜索站点 ==========
def test_search_stops(query="Harvard"):
    """按名称搜索站点"""
    print("\n" + "="*50)
    print(f"测试 3: 搜索站点 '{query}'")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/stops",
        params={"filter[name]": query},
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"找到 {len(data['data'])} 个匹配:\n")
        for stop in data['data'][:5]:
            attrs = stop['attributes']
            print(f"  {stop['id']:25} | {attrs['name']}")
    else:
        print(f"错误: {response.status_code}")

# ========== 测试 4: 获取到站预测（核心功能）==========
def test_get_predictions(stop_id="place-harsq", route_id=None):
    """获取实时到站预测"""
    print("\n" + "="*50)
    print(f"测试 4: 获取 {stop_id} 的到站预测")
    print("="*50)
    
    params = {
        "filter[stop]": stop_id,
        "include": "route"
    }
    if route_id:
        params["filter[route]"] = route_id
    
    response = requests.get(
        f"{BASE_URL}/predictions",
        params=params,
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        predictions = data['data']
        
        if not predictions:
            print("当前没有预测数据（可能不在运营时间）")
            return
        
        print(f"找到 {len(predictions)} 条预测:\n")
        
        for pred in predictions[:5]:
            attrs = pred['attributes']
            
            # 解析时间
            arrival = attrs.get('arrival_time')
            if arrival:
                arrival_dt = datetime.fromisoformat(arrival.replace('Z', '+00:00'))
                time_str = arrival_dt.strftime("%H:%M:%S")
                
                # 计算还有多久
                now = datetime.now(arrival_dt.tzinfo)
                diff = (arrival_dt - now).total_seconds() / 60
                mins_str = f"{diff:.0f} 分钟后" if diff > 0 else "即将到达"
            else:
                time_str = "未知"
                mins_str = ""
            
            # 获取线路名称
            route_data = pred['relationships']['route']['data']
            route_name = route_data['id'] if route_data else "未知"
            
            # 方向
            direction = "北行" if attrs.get('direction_id') == 1 else "南行"
            
            # 状态
            status = attrs.get('status', '')
            
            print(f"  🚇 {route_name:8} | {direction} | {time_str} | {mins_str} {status}")
    else:
        print(f"错误: {response.status_code}")
        print(response.text)

# ========== 测试 5: 获取服务警报 ==========
def test_get_alerts(route_id="Red"):
    """获取服务警报"""
    print("\n" + "="*50)
    print(f"测试 5: 获取 {route_id} 线的服务警报")
    print("="*50)
    
    response = requests.get(
        f"{BASE_URL}/alerts",
        params={"filter[route]": route_id},
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        alerts = data['data']
        
        if not alerts:
            print("当前没有服务警报 ✅")
            return
        
        print(f"找到 {len(alerts)} 条警报:\n")
        for alert in alerts[:3]:
            attrs = alert['attributes']
            print(f"  ⚠️  {attrs.get('header', '无标题')}")
            print(f"      {attrs.get('description', '')[:100]}...")
            print()
    else:
        print(f"错误: {response.status_code}")

# ========== 运行所有测试 ==========
if __name__ == "__main__":
    print("\n🚇 MBTA API 测试开始 🚇")
    
    test_get_routes()
    test_get_stops("Red")
    test_search_stops("Harvard")
    test_get_predictions("place-harsq")
    test_get_alerts("Red")
    
    print("\n" + "="*50)
    print("测试完成！")
    print("="*50)