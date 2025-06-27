import asyncio
from websockets.client import connect
from websockets.exceptions import ConnectionClosed
import json
import uuid
import time

async def test_music_generation():
    """
    测试音乐生成WebSocket服务
    """
    # 生成唯一的客户端ID
    client_id = str(uuid.uuid4())
    uri = f"ws://localhost:8888/ws/{client_id}"
    
    print(f"开始测试 - 客户端ID: {client_id}")
    
    try:
        async with connect(uri) as websocket:
            print("WebSocket连接成功")
            
            # 准备音乐生成请求
            request_data = {
                "type": "generate",
                "prompt": "电子音乐，带有强烈的节奏感和动感的旋律",
                "duration": 10,  # 为了测试，使用较短的时间
                "mbd": False
            }
            
            print(f"发送生成请求: {request_data}")
            await websocket.send(json.dumps(request_data))
            
            # 等待并处理服务器响应
            generation_start_time = time.time()
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "progress":
                        print(f"生成进度: {data['data']:.2f}%")
                    elif data["type"] == "complete":
                        generation_time = time.time() - generation_start_time
                        print(f"生成完成！")
                        print(f"生成文件: {data['data']}")
                        print(f"总耗时: {generation_time:.2f} 秒")
                        break
                        
                except ConnectionClosed:
                    print("WebSocket连接已关闭")
                    break
                    
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        return False
        
    return True

async def run_tests():
    """
    运行所有测试用例
    """
    print("=== 开始运行测试用例 ===")
    
    # 测试音乐生成
    print("\n1. 测试音乐生成功能")
    success = await test_music_generation()
    
    if success:
        print("\n✅ 所有测试通过")
    else:
        print("\n❌ 测试失败")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_tests()) 