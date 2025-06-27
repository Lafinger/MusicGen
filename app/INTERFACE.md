# MusicGen API 接口文档

## 基础信息
- 基础URL: `/api`
- 所有请求和响应均使用JSON格式
- 服务采用单例模式，同一时间只能处理一个音乐生成请求

## 1. 健康检查接口

### GET /api/healthcheck

检查服务是否可用。

**响应格式：**
```json
{
    "status": "healthy" | "busy"
}
```

**响应状态码：**
- 200: 服务正常
- 503: 服务正忙

## 2. 音乐生成接口

### POST /api/music

使用文本描述生成音乐，支持Server-Sent Events (SSE)实时进度反馈。

**请求参数：**
```json
{
    "description": "string",       // 必需，音乐描述文本
    "duration": number,           // 可选，音频时长(秒)，默认30
    "mbd": boolean,              // 可选，是否使用MultiBand Diffusion，默认false
    "top_k": number,             // 可选，top-k采样参数，默认250
    "top_p": number,             // 可选，top-p采样参数，默认0.0，范围[0,1]
    "temperature": number,       // 可选，温度参数，默认1.0，必须>0
    "cfg_coef": number          // 可选，无分类器指导系数，默认3.0
}
```

**参数验证规则：**
- `duration`: 必须为正整数
- `mbd`: 必须为布尔值
- `top_k`: 必须为正整数
- `top_p`: 必须为0到1之间的浮点数
- `temperature`: 必须为正数
- `cfg_coef`: 必须为数字类型

**SSE事件流：**

1. 开始事件
```json
{
    "status": "started"
}
```

2. 进度事件
```json
{
    "status": "generating",
    "progress": number  // 生成进度百分比(0-100)
}
```

3. 完成事件
```json
{
    "status": "completed",
    "audio_data": "string"  // Base64编码的WAV音频数据
}
```

4. 错误事件
```json
{
    "error": "string"  // 错误信息
}
```

**响应状态码：**
- 200: 成功启动音乐生成
- 400: 请求参数错误
- 503: 服务正忙
- 500: 服务器内部错误

## 注意事项

1. 服务使用单例模式，同一时间只能处理一个请求，并发数为1，自动释放资源机制
2. 生成过程中断开连接会自动停止生成
3. 音频生成需要CUDA支持
4. 返回的音频数据为WAV格式，采样率为32000Hz，16位整数编码，支持单声道和立体声输出
5. 支持实时进度反馈
6. 支持客户端中断生成，连接断开自动中断


## 示例代码

### Python 客户端示例
```python
import requests
import json

# 健康检查
response = requests.get('http://localhost:5000/api/healthcheck')
print(response.json())

# 生成音乐（SSE方式）
params = {
    "description": "电子音乐，带有强烈的鼓点",
    "duration": 30,
    "mbd": False,
    "top_k": 250,
    "top_p": 0.0,
    "temperature": 1.0,
    "cfg_coef": 3.0
}

response = requests.post(
    'http://localhost:5000/api/music',
    json=params,
    headers={'Accept': 'text/event-stream'},
    stream=True
)

for line in response.iter_lines():
    if line:
        event_data = json.loads(line.decode('utf-8').split('data: ')[1])
        if event_data.get('status') == 'completed':
            # 处理返回的音频数据
            audio_data = event_data['audio_data']
            # 解码Base64并保存为WAV文件
            ...
        elif event_data.get('status') == 'generating':
            # 显示进度
            print(f"生成进度: {event_data['progress']}%")
```

### curl 示例
```bash
# 健康检查
curl http://localhost:5000/api/healthcheck

# 生成音乐
curl -X POST http://localhost:5000/api/music \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"description": "电子音乐，带有强烈的鼓点", "duration": 30}'
```
