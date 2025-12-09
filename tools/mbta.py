"""
MBTA 工具模块
提供波士顿地铁 API 的所有功能

设计原则：
- 工具只做数据查询，不做智能判断
- 歧义处理交给 Agent (GPT-4o)
- 函数参数尽量使用精确的 ID
"""
import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 配置
# ============================================================
MBTA_API_KEY = os.getenv("MBTA_API_KEY")
BASE_URL = "https://api-v3.mbta.com"

# 线路方向信息（这个保留，因为是 API 返回的 direction_id 的映射）
ROUTE_DIRECTIONS = {
    "Red": {0: "Ashmont/Braintree", 1: "Alewife"},
    "Orange": {0: "Forest Hills", 1: "Oak Grove"},
    "Blue": {0: "Bowdoin", 1: "Wonderland"},
    "Green-B": {0: "Park Street", 1: "Boston College"},
    "Green-C": {0: "Park Street", 1: "Cleveland Circle"},
    "Green-D": {0: "Union Square", 1: "Riverside"},
    "Green-E": {0: "Medford/Tufts", 1: "Heath Street"},
}


def _get_headers():
    """返回 API 请求头"""
    return {"x-api-key": MBTA_API_KEY} if MBTA_API_KEY else {}


# ============================================================
# 核心功能函数
# ============================================================

def get_alerts(route_id: str = None) -> dict:
    """
    获取服务警报（停运、延误、维修等）
    
    参数:
        route_id: 线路 ID（可选），如 "Red", "Green-B"
                  不填则返回所有地铁线路的警报
    
    返回:
        {"route": "Green-B", "alerts": [{"header": "...", "effect": "..."}, ...]}
    """
    params = {}
    
    if route_id:
        params["filter[route]"] = route_id
    else:
        # 只获取地铁/轻轨的警报
        params["filter[route_type]"] = "0,1"
    
    response = requests.get(
        f"{BASE_URL}/alerts",
        params=params,
        headers=_get_headers()
    )
    
    if response.status_code != 200:
        return {"error": f"API 错误: {response.status_code}"}
    
    data = response.json()
    alerts_data = data.get("data", [])
    
    alerts = []
    for alert in alerts_data:
        attrs = alert["attributes"]
        
        # 获取影响的线路
        affected_routes = []
        for entity in attrs.get("informed_entity", []):
            if "route" in entity:
                affected_routes.append(entity["route"])
        
        alerts.append({
            "header": attrs.get("header", ""),
            "description": attrs.get("description", ""),
            "effect": attrs.get("effect", ""),  # SUSPENSION, DELAY, etc.
            "severity": attrs.get("severity", 0),
            "affected_routes": list(set(affected_routes)),
            "updated_at": attrs.get("updated_at", "")
        })
    
    # 按严重程度排序（高的在前）
    alerts.sort(key=lambda x: x["severity"], reverse=True)
    
    if not alerts:
        return {
            "route_filter": route_id,
            "has_alerts": False,
            "alerts": [],
            "message": f"✅ {'该线路' if route_id else '地铁系统'}目前没有服务警报，运营正常。"
        }
    
    # 生成消息
    lines = [f"⚠️ 发现 {len(alerts)} 条服务警报:"]
    for i, alert in enumerate(alerts[:5], 1):
        effect = alert["effect"]
        header = alert["header"]
        lines.append(f"  {i}. [{effect}] {header}")
    
    return {
        "route_filter": route_id,
        "has_alerts": True,
        "alert_count": len(alerts),
        "alerts": alerts[:10],  # 最多返回 10 条
        "message": "\n".join(lines)
    }


def get_routes(route_type: str = "0,1") -> dict:
    """
    获取所有线路
    
    参数:
        route_type: 线路类型
            - "0,1" = 地铁和轻轨（默认）
            - "2" = 通勤铁路
            - "3" = 公交车
    
    返回:
        {"routes": [{"id": "Red", "name": "Red Line", ...}, ...]}
    """
    response = requests.get(
        f"{BASE_URL}/routes",
        params={"filter[type]": route_type},
        headers=_get_headers()
    )
    
    if response.status_code != 200:
        return {"error": f"API 错误: {response.status_code}"}
    
    data = response.json()
    routes = []
    
    for route in data.get("data", []):
        attrs = route["attributes"]
        routes.append({
            "id": route["id"],
            "name": attrs["long_name"],
            "color": attrs.get("color", ""),
            "directions": ROUTE_DIRECTIONS.get(route["id"], {})
        })
    
    return {"routes": routes}


def get_stops(route_id: str) -> dict:
    """
    获取某条线路的所有站点
    
    参数:
        route_id: 线路 ID，如 "Red", "Green-B"
    
    返回:
        {"route": "Red", "stops": [{"id": "place-harsq", "name": "Harvard"}, ...]}
    """
    response = requests.get(
        f"{BASE_URL}/stops",
        params={"filter[route]": route_id},
        headers=_get_headers()
    )
    
    if response.status_code != 200:
        return {"error": f"API 错误: {response.status_code}"}
    
    data = response.json()
    
    # 去重（同一站可能有多个站台）
    seen = set()
    stops = []
    
    for stop in data.get("data", []):
        name = stop["attributes"]["name"]
        if name not in seen:
            seen.add(name)
            stops.append({
                "id": stop["id"],
                "name": name
            })
    
    return {
        "route": route_id,
        "directions": ROUTE_DIRECTIONS.get(route_id, {}),
        "stops": stops
    }


def search_stops(query: str) -> dict:
    """
    按名称搜索站点（模糊匹配）
    
    参数:
        query: 搜索关键词，如 "Harvard", "Park"
    
    返回:
        {"query": "Harvard", "results": [{"id": "place-harsq", "name": "Harvard"}, ...]}
    """
    response = requests.get(
        f"{BASE_URL}/stops",
        params={"filter[route_type]": "0,1"},
        headers=_get_headers()
    )
    
    if response.status_code != 200:
        return {"error": f"API 错误: {response.status_code}"}
    
    data = response.json()
    query_lower = query.lower().strip()
    
    # 去重 + 模糊匹配
    seen = set()
    matches = []
    
    for stop in data.get("data", []):
        name = stop["attributes"]["name"]
        if name not in seen and query_lower in name.lower():
            seen.add(name)
            matches.append({
                "id": stop["id"],
                "name": name
            })
    
    return {
        "query": query,
        "count": len(matches),
        "results": matches
    }


def get_predictions(stop_id: str, route_id: str = None, direction: str = None) -> dict:
    """
    获取某站点的到站预测
    
    参数:
        stop_id: 站点 ID，如 "place-harsq"（必须是精确ID）
        route_id: 线路 ID（可选），如 "Red"
        direction: 方向（可选），如 "Alewife"
    
    返回:
        {"stop_id": "place-harsq", "predictions": [...]}
    """
    params = {
        "filter[stop]": stop_id,
        "sort": "arrival_time",
        "include": "route"
    }
    
    if route_id:
        params["filter[route]"] = route_id
    
    response = requests.get(
        f"{BASE_URL}/predictions",
        params=params,
        headers=_get_headers()
    )
    
    if response.status_code != 200:
        return {"error": f"API 错误: {response.status_code}", "stop_id": stop_id}
    
    data = response.json()
    predictions_data = data.get("data", [])
    
    if not predictions_data:
        return {
            "stop_id": stop_id,
            "predictions": [],
            "message": "当前没有预测数据，可能不在运营时间"
        }
    
    # 当前时间
    now = datetime.now(timezone.utc)
    predictions = []
    
    for pred in predictions_data:
        attrs = pred["attributes"]
        
        # 获取时间
        arrival_str = attrs.get("arrival_time") or attrs.get("departure_time")
        if not arrival_str:
            continue
        
        arrival_time = datetime.fromisoformat(arrival_str.replace("Z", "+00:00"))
        
        # 只要未来的车
        if arrival_time < now:
            continue
        
        # 计算等待分钟数
        wait_minutes = (arrival_time - now).total_seconds() / 60
        
        # 获取线路
        route_data = pred["relationships"]["route"]["data"]
        route_name = route_data["id"] if route_data else "未知"
        
        # 获取方向
        direction_id = attrs.get("direction_id", 0)
        direction_name = ROUTE_DIRECTIONS.get(route_name, {}).get(direction_id, f"方向{direction_id}")
        
        predictions.append({
            "route": route_name,
            "direction": direction_name,
            "minutes": round(wait_minutes),
            "time": arrival_time.strftime("%H:%M:%S"),
            "status": attrs.get("status", "")
        })
    
    # 按时间排序
    predictions.sort(key=lambda x: x["minutes"])
    
    # 如果指定了方向，过滤结果
    if direction:
        direction_lower = direction.lower()
        predictions = [
            p for p in predictions
            if direction_lower in p["direction"].lower()
        ]
    
    return {
        "stop_id": stop_id,
        "route_filter": route_id,
        "direction_filter": direction,
        "predictions": predictions[:10]
    }


def get_next_train(stop_id: str, route_id: str = None, direction: str = None) -> dict:
    """
    获取下一班列车
    
    参数:
        stop_id: 站点 ID，如 "place-harsq"（必须是精确ID）
        route_id: 线路 ID（可选），如 "Red"
        direction: 方向（可选），如 "Alewife"
    
    返回:
        {"stop_id": "place-harsq", "route": "Red", "direction": "Alewife", "minutes": 3, ...}
    """
    result = get_predictions(stop_id, route_id, direction)
    
    if "error" in result:
        return result
    
    if not result["predictions"]:
        # 没有预测数据 - 明确告诉 Agent 不要编造
        return {
            "stop_id": stop_id,
            "route_filter": route_id,
            "direction_filter": direction,
            "has_data": False,  # 明确标记没有数据
            "predictions": [],
            "message": f"⚠️ 当前没有列车预测数据。可能原因：1) 线路停运或维修中 2) 不在运营时间 3) 服务中断。请查看 MBTA 官方警报获取详情。"
        }
    
    # 取第一条（最近的）
    next_train = result["predictions"][0]
    
    # 生成自然语言消息
    minutes = next_train["minutes"]
    if minutes < 1:
        time_str = "即将到达"
    elif minutes == 1:
        time_str = "1 分钟后到达"
    else:
        time_str = f"{minutes} 分钟后到达"
    
    message = f"{next_train['route']} 线下一班车 {time_str}，方向 {next_train['direction']}"
    
    return {
        "stop_id": stop_id,
        "route": next_train["route"],
        "direction": next_train["direction"],
        "minutes": minutes,
        "time": next_train["time"],
        "has_data": True,  # 明确标记有数据
        "message": message
    }


def get_both_directions(stop_id: str, route_id: str) -> dict:
    """
    获取两个方向的下一班车
    
    参数:
        stop_id: 站点 ID，如 "place-harsq"
        route_id: 线路 ID，如 "Red"
    
    返回:
        {"stop_id": "place-harsq", "route": "Red", "directions": {...}}
    """
    result = get_predictions(stop_id, route_id)
    
    if "error" in result:
        return result
    
    if not result["predictions"]:
        # 没有预测数据 - 明确告诉 Agent 不要编造
        return {
            "stop_id": stop_id,
            "route": route_id,
            "has_data": False,  # 明确标记没有数据
            "directions": {},
            "message": f"⚠️ {route_id} 线在该站当前没有列车数据。可能原因：线路停运、维修中、或不在运营时间。"
        }
    
    # 按方向分组，每个方向取第一班
    directions = {}
    for pred in result["predictions"]:
        dir_name = pred["direction"]
        if dir_name not in directions:
            directions[dir_name] = {
                "minutes": pred["minutes"],
                "time": pred["time"]
            }
    
    # 生成消息
    lines = [f"{route_id} 线:"]
    for dir_name, info in directions.items():
        mins = info["minutes"]
        if mins < 1:
            lines.append(f"  → {dir_name}: 即将到达")
        else:
            lines.append(f"  → {dir_name}: {mins} 分钟后")
    
    return {
        "stop_id": stop_id,
        "route": route_id,
        "has_data": True,  # 明确标记有数据
        "directions": directions,
        "message": "\n".join(lines)
    }


# ============================================================
# GPT Function Calling 工具定义
# ============================================================

MBTA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "获取 MBTA 服务警报（停运、延误、维修等）。当查询不到列车数据时，应该调用此函数检查是否有服务中断。也可以主动查询线路状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "route_id": {
                        "type": "string",
                        "description": "线路ID（可选），如 'Red', 'Green-B'。不填则返回所有地铁线路的警报。",
                        "enum": ["Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_stops",
            "description": "按名称搜索地铁站。当用户提到一个站名但你不确定具体是哪个站时，先用这个搜索。返回所有匹配的站点及其ID。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如 'Harvard', 'Park'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_train",
            "description": "获取某站的下一班列车。需要提供精确的站点ID（如 place-harsq）。如果不确定站点ID，先用 search_stops 搜索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {
                        "type": "string",
                        "description": "精确的站点ID，如 'place-harsq'（Harvard Square）、'place-pktrm'（Park Street）"
                    },
                    "route_id": {
                        "type": "string",
                        "description": "线路ID（可选）",
                        "enum": ["Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"]
                    },
                    "direction": {
                        "type": "string",
                        "description": "方向/终点站（可选），如 'Alewife', 'Ashmont', 'Boston College'"
                    }
                },
                "required": ["stop_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_predictions",
            "description": "获取某站点的多班列车到站预测。需要精确的站点ID。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {
                        "type": "string",
                        "description": "精确的站点ID"
                    },
                    "route_id": {
                        "type": "string",
                        "description": "线路ID（可选）"
                    },
                    "direction": {
                        "type": "string",
                        "description": "方向（可选）"
                    }
                },
                "required": ["stop_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_both_directions",
            "description": "同时获取两个方向的下一班车。当用户没指定方向时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {
                        "type": "string",
                        "description": "精确的站点ID"
                    },
                    "route_id": {
                        "type": "string",
                        "description": "线路ID",
                        "enum": ["Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"]
                    }
                },
                "required": ["stop_id", "route_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_routes",
            "description": "获取波士顿地铁的所有线路列表。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stops",
            "description": "获取某条线路的所有站点列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "route_id": {
                        "type": "string",
                        "description": "线路ID，如 'Red', 'Green-B'"
                    }
                },
                "required": ["route_id"]
            }
        }
    }
]


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🚇 MBTA 工具模块测试")
    print("=" * 50)
    
    # 测试 1: 搜索站点
    print("\n📌 测试 search_stops('Harvard')")
    results = search_stops("Harvard")
    print(f"   找到 {results['count']} 个匹配:")
    for r in results["results"]:
        print(f"     - {r['id']}: {r['name']}")
    
    # 测试 2: 搜索 Park
    print("\n📌 测试 search_stops('Park')")
    results = search_stops("Park")
    print(f"   找到 {results['count']} 个匹配:")
    for r in results["results"]:
        print(f"     - {r['id']}: {r['name']}")
    
    # 测试 3: 用精确 ID 查询
    print("\n📌 测试 get_next_train('place-harsq', 'Red')")
    result = get_next_train("place-harsq", "Red")
    print(f"   {result.get('message', result)}")
    
    # 测试 4: 查询两个方向
    print("\n📌 测试 get_both_directions('place-harsq', 'Red')")
    result = get_both_directions("place-harsq", "Red")
    print(f"   {result.get('message', result)}")
    
    # 测试 5: 指定方向
    print("\n📌 测试 get_next_train('place-harsq', 'Red', 'Alewife')")
    result = get_next_train("place-harsq", "Red", "Alewife")
    print(f"   {result.get('message', result)}")
    
    # 测试 6: 获取线路站点
    print("\n📌 测试 get_stops('Red')")
    result = get_stops("Red")
    print(f"   红线有 {len(result['stops'])} 个站点")
    print(f"   方向: {result['directions']}")
    
    print("\n" + "=" * 50)
    print("✅ 测试完成")
    print("=" * 50)