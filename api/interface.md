# 音乐生成服务 API 文档

## 简介

音乐生成服务是基于Facebook的MusicGen模型构建的音乐生成API服务。该服务支持通过文本描述生成音乐，并使用Server-Sent Events (SSE)提供实时进度反馈。

## 基本信息

- **基础URL**: http://[host]:[port]
- **默认端口**: 5555
- **协议**: HTTP

## 注意事项

1. 服务使用单例模式，同一时间只能处理一个请求，并发数为1，自动释放资源机制
2. 音频生成需要CUDA支持
3. 返回的音频数据为WAV格式，采样率为32000Hz，16位整数编码，支持单声道和立体声输出
4. 支持实时进度反馈
5. 支持客户端中断生成，连接断开自动中断
6. 消息为Server-Sent Events (SSE)标准事件

## API 端点

### 生成音乐

**端点**: `/api/v1/generate_music`

**方法**: POST

**描述**: 根据文本描述生成音乐，并以流式方式返回生成进度和结果。

#### 请求参数

请求体为JSON格式，包含以下字段：

| 参数名 | 类型 | 必需 | 默认值 | 描述 |
|--------|------|------|--------|------|
| description | string | 是 | - | 音乐描述文本，用于指导音乐生成 |
| duration | integer | 否 | 30 | 音频时长（秒），范围：1-60秒 |
| mbd | boolean | 否 | false | 是否使用MultiBand Diffusion增强生成质量 |
| top_k | integer | 否 | 250 | top-k采样参数，控制生成多样性 |
| top_p | float | 否 | 0.0 | top-p采样参数，范围：0-1.0 |
| temperature | float | 否 | 1.0 | 温度参数，控制随机性 |
| cfg_coef | float | 否 | 3.0 | 无分类器指导系数 |

**请求示例**:

```json
{
  "description": "电子音乐带有强烈的鼓点和节奏感",
  "duration": 15,
  "mbd": false,
  "top_k": 250,
  "top_p": 0.0,
  "temperature": 1.0,
  "cfg_coef": 3.0
}
```

#### 响应格式

响应使用Server-Sent Events (SSE)格式，包含以下事件类型：

1. **start**: 表示生成过程已开始
   ```
   data: {"event": "start"}
   ```

2. **progress**: 报告生成进度
   ```
   data: {"event": "progress", "progress": 25.5}
   ```
   - `progress`: 浮点数，表示生成进度百分比（0-100）

3. **completed**: 生成完成，返回音频数据
   ```
   data: {"event": "completed", "audio": "BASE64_ENCODED_WAV_DATA"}
   ```
   - `audio`: Base64编码的WAV格式音频数据

4. **error**: 发生错误
   ```
   data: {"event": "error", "message": "错误信息"}
   ```
   - `message`: 错误描述信息

#### 错误码

| 状态码 | 描述 |
|--------|------|
| 400 | 请求格式错误，通常是因为JSON格式不正确 |
| 503 | 服务器繁忙，当前正在处理其他请求 |
| 500 | 服务器内部错误 |

## 限制和注意事项

1. 服务使用信号量进行限流，同一时间只能处理一个音乐生成请求
2. 每次请求的音频时长最长为60秒
3. 生成过程可能需要较长时间，根据请求参数和服务器性能不同而异
4. 客户端需支持Server-Sent Events (SSE)以接收实时进度

## 客户端示例

### Python 异步客户端

```python
import asyncio
import aiohttp
import json
import base64
import os

async def generate_music(description, duration=30, server_url="http://localhost:5555"):
    """生成音乐并保存到文件
    
    Args:
        description: 音乐描述
        duration: 音频时长（秒）
        server_url: 服务器地址
    """
    params = {
        "description": description,
        "duration": duration,
        "mbd": False,
        "top_k": 250,
        "top_p": 0.0,
        "temperature": 1.0,
        "cfg_coef": 3.0
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{server_url}/api/v1/generate_music", 
            json=params,
            headers=headers
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"错误: {error_text}")
                return
                
            buffer = ""
            async for line in response.content:
                line = line.decode('utf-8')
                buffer += line
                
                if buffer.endswith('\n\n'):
                    for event_data in buffer.split('\n\n'):
                        if event_data.startswith('data: '):
                            data = json.loads(event_data[6:])
                            
                            if data["event"] == "start":
                                print("开始生成音乐...")
                            elif data["event"] == "progress":
                                print(f"生成进度: {data.get('progress', 0):.2f}%")
                            elif data["event"] == "completed":
                                print("音乐生成完成！")
                                if "audio" in data:
                                    # 保存音频文件
                                    audio_data = base64.b64decode(data["audio"])
                                    os.makedirs("output", exist_ok=True)
                                    output_file = os.path.join("output", "generated_music.wav")
                                    with open(output_file, "wb") as f:
                                        f.write(audio_data)
                                    print(f"音频已保存到: {output_file}")
                                return
                            elif data["event"] == "error":
                                print(f"错误: {data.get('message', '未知错误')}")
                                return
                    buffer = ""

# 使用示例
asyncio.run(generate_music("电子舞曲带有明亮的合成器和强烈的节拍", duration=15))
```

### JavaScript 客户端

```javascript
async function generateMusic(description, duration = 30) {
  const serverUrl = 'http://localhost:5555';
  const params = {
    description,
    duration,
    mbd: false,
    top_k: 250,
    top_p: 0.0,
    temperature: 1.0,
    cfg_coef: 3.0
  };

  try {
    // 创建EventSource连接
    const response = await fetch(`${serverUrl}/api/v1/generate_music`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(params)
    });
    
    // 使用ReadableStream读取SSE响应
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // 处理完整的SSE消息
      const messages = buffer.split('\n\n');
      buffer = messages.pop() || '';  // 保留最后一个不完整的消息
      
      for (const message of messages) {
        if (message.startsWith('data: ')) {
          const data = JSON.parse(message.substring(6));
          
          switch (data.event) {
            case 'start':
              console.log('开始生成音乐...');
              break;
            case 'progress':
              console.log(`生成进度: ${data.progress.toFixed(2)}%`);
              break;
            case 'completed':
              console.log('音乐生成完成！');
              if (data.audio) {
                // 将Base64音频转换为Blob
                const audioBlob = base64ToBlob(data.audio, 'audio/wav');
                // 创建下载链接
                const audioUrl = URL.createObjectURL(audioBlob);
                const a = document.createElement('a');
                a.href = audioUrl;
                a.download = 'generated_music.wav';
                a.click();
                URL.revokeObjectURL(audioUrl);
              }
              return;
            case 'error':
              console.error(`错误: ${data.message || '未知错误'}`);
              return;
          }
        }
      }
    }
  } catch (error) {
    console.error('请求失败:', error);
  }
}

// 辅助函数：Base64转Blob
function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteArrays = [];
  
  for (let offset = 0; offset < byteCharacters.length; offset += 512) {
    const slice = byteCharacters.slice(offset, offset + 512);
    const byteNumbers = new Array(slice.length);
    
    for (let i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i);
    }
    
    const byteArray = new Uint8Array(byteNumbers);
    byteArrays.push(byteArray);
  }
  
  return new Blob(byteArrays, { type: mimeType });
}

// 使用示例
generateMusic('钢琴独奏带有情感的旋律', 20);
```
