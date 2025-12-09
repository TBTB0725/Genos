"""
核心功能测试：下一班地铁什么时候到？
测试站点：Babcock Street (绿线 B)
"""
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
MBTA_API_KEY = os.getenv("MBTA_API_KEY")
BASE_URL = "https://api-v3.mbta.com"

def get_headers():
    return {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}


def search_stop(query):
    """
    搜索站点（修复版）
    正确的 API 参数是 filter[id] 或直接搜索所有站点再过滤
    """
    print(f"\n🔍 搜索站点: '{query}'")
    print("-" * 40)
    
    # 方法：获取所有站点，本地过滤
    response = requests.get(
        f"{BASE_URL}/stops",
        params={
            "filter[route_type]": "0,1",  # 只要轻轨和地铁站点
        },
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        # 本地搜索匹配
        query_lower = query.lower()
        matches = [
            stop for stop in data['data']
            if query_lower in stop['attributes']['name'].lower()
        ]
        
        if matches:
            print(f"找到 {len(matches)} 个匹配:\n")
            for stop in matches[:10]:
                print(f"  ID: {stop['id']:25} | 名称: {stop['attributes']['name']}")
            return matches
        else:
            print("没有找到匹配的站点")
            return []
    else:
        print(f"错误: {response.status_code}")
        return []


def get_next_train(stop_id, route_id=None):
    """
    获取下一班地铁的到站时间
    
    参数:
        stop_id: 站点 ID，如 "place-babck"
        route_id: 线路 ID，如 "Green-B"（可选，不填则返回所有线路）
    """
    print(f"\n🚇 查询下一班车")
    print(f"   站点: {stop_id}")
    if route_id:
        print(f"   线路: {route_id}")
    print("-" * 40)
    
    params = {
        "filter[stop]": stop_id,
        "sort": "arrival_time",  # 按到站时间排序
        "include": "route,trip",  # 包含线路和车次信息
    }
    
    # 如果指定了线路，只查该线路
    if route_id:
        params["filter[route]"] = route_id
    
    response = requests.get(
        f"{BASE_URL}/predictions",
        params=params,
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"错误: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    predictions = data['data']
    
    # 构建 route 信息字典（从 included 中提取）
    routes_info = {}
    for item in data.get('included', []):
        if item['type'] == 'route':
            routes_info[item['id']] = item['attributes']
    
    if not predictions:
        print("❌ 当前没有预测数据")
        print("   可能原因：不在运营时间 或 线路暂停服务")
        return None
    
    print(f"✅ 找到 {len(predictions)} 条预测\n")
    
    # 当前时间
    now = datetime.now(timezone.utc)
    
    # 过滤并显示即将到来的列车
    upcoming = []
    
    for pred in predictions:
        attrs = pred['attributes']
        
        # 获取到站时间
        arrival_str = attrs.get('arrival_time') or attrs.get('departure_time')
        if not arrival_str:
            continue
        
        # 解析时间
        arrival_time = datetime.fromisoformat(arrival_str.replace('Z', '+00:00'))
        
        # 只要未来的车
        if arrival_time < now:
            continue
        
        # 计算等待时间（分钟）
        wait_minutes = (arrival_time - now).total_seconds() / 60
        
        # 获取线路信息
        route_data = pred['relationships']['route']['data']
        route_id_val = route_data['id'] if route_data else "未知"
        
        # 获取方向
        direction_id = attrs.get('direction_id', 0)
        
        # 尝试从 routes_info 获取方向名称
        direction_name = ""
        if route_id_val in routes_info:
            destinations = routes_info[route_id_val].get('direction_destinations', [])
            if destinations and direction_id < len(destinations):
                dest = destinations[direction_id]
                direction_name = dest[0] if isinstance(dest, list) else dest
        
        # 状态
        status = attrs.get('status', '')
        
        upcoming.append({
            'route': route_id_val,
            'direction': direction_name or f"方向{direction_id}",
            'arrival_time': arrival_time,
            'wait_minutes': wait_minutes,
            'status': status
        })
    
    # 按等待时间排序
    upcoming.sort(key=lambda x: x['wait_minutes'])
    
    # 显示结果
    if upcoming:
        print("即将到站的列车:\n")
        for i, train in enumerate(upcoming[:8], 1):
            wait = train['wait_minutes']
            if wait < 1:
                wait_str = "即将到达 🚨"
            elif wait < 60:
                wait_str = f"{wait:.0f} 分钟"
            else:
                hours = int(wait // 60)
                mins = int(wait % 60)
                wait_str = f"{hours}小时{mins}分"
            
            time_str = train['arrival_time'].strftime("%H:%M:%S")
            status = f" ({train['status']})" if train['status'] else ""
            
            print(f"  {i}. 🚇 {train['route']:10} → {train['direction']:15} | {wait_str:12} | {time_str}{status}")
        
        # 返回最近一班
        return upcoming[0]
    else:
        print("❌ 没有找到即将到来的列车")
        return None


def main():
    print("=" * 50)
    print("🚇 MBTA 下一班车查询测试")
    print("=" * 50)
    
    # 测试 1: 搜索 Babcock Street 站
    print("\n" + "=" * 50)
    print("测试 1: 搜索 Babcock Street")
    print("=" * 50)
    stops = search_stop("Babcock")
    
    # 测试 2: 查询 Babcock Street 绿线 B 的下一班车
    # Babcock Street 的站点 ID 是 place-babck
    print("\n" + "=" * 50)
    print("测试 2: Babcock Street 绿线 B 下一班车")
    print("=" * 50)
    next_train = get_next_train("place-babck", "Green-B")
    
    if next_train:
        print(f"\n📢 下一班 {next_train['route']} 将在 {next_train['wait_minutes']:.0f} 分钟后到达")
        print(f"   方向: {next_train['direction']}")
    
    # 测试 3: 查询 Harvard 红线的下一班车
    print("\n" + "=" * 50)
    print("测试 3: Harvard 红线下一班车")
    print("=" * 50)
    next_train = get_next_train("place-harsq", "Red")
    
    if next_train:
        print(f"\n📢 下一班 {next_train['route']} 将在 {next_train['wait_minutes']:.0f} 分钟后到达")
        print(f"   方向: {next_train['direction']}")
    
    # 测试 4: Park Street 所有线路（红线+绿线换乘站）
    print("\n" + "=" * 50)
    print("测试 4: Park Street 所有地铁线路")
    print("=" * 50)
    get_next_train("place-pktrm")  # 不指定线路，显示所有


if __name__ == "__main__":
    main()