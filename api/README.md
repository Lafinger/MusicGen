# MusicGen API 服务

基于 Facebook 的 MusicGen 模型实现的音乐生成 API 服务。本项目提供了一个易于使用的 FastAPI 接口，支持流式响应的文本到音乐生成功能。

## 项目特点

- 使用 FastAPI 搭建高性能 API
- 支持 SSE (Server-Sent Events) 流式响应，实时展示生成进度
- 基于 Facebook 的 MusicGen 大型音乐生成模型
- 支持多波段扩散 (Multi-Band Diffusion) 增强音质
- 完整的日志追踪系统，支持全链路请求跟踪
- 提供同步和异步两种客户端示例
- 客户端连接中断会打断语音生成，语音生成完成服务器会主动断开连接

## 架构设计

项目采用三层架构设计:

1. **Controller 层**: 负责处理 HTTP 请求和响应，参数验证和格式转换
2. **Service 层**: 封装核心业务逻辑，管理模型资源
3. **模型层**: 封装 MusicGen 和 MultiBandDiffusion 模型的调用

### 主要文件说明

- `main.py`: 服务入口，包含 FastAPI 路由和中间件配置
- `controller.py`: 控制器层，处理请求参数验证和响应格式化
- `service.py`: 服务层，封装 MusicGen 模型调用的核心逻辑
- `client_requests.py`: 基于 requests 的同步客户端示例
- `client_aiohttp.py`: 基于 aiohttp 的异步客户端示例
- `loguru_settings.py`: 日志配置，支持全链路追踪
- `uvicorn_config.json`: uvicorn 服务器配置

## 快速开始

### 环境要求

- Python 3.9+
- CUDA 支持的 GPU (用于模型推理)
- 以下依赖包：
  ```
  uvicorn==0.24.0
  fastapi==0.104.1
  scipy==1.13.0
  loguru==0.7.2
  ```
- Facebook 的 Audiocraft 库 (包含 MusicGen 模型)

### 安装步骤

1. 克隆项目并进入目录
   ```bash
   git clone <repository_url>
   cd MusicGen/api
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 安装 Audiocraft 库
   ```bash
   pip install git+https://github.com/facebookresearch/audiocraft.git
   ```

### 启动服务

```bash
python main.py --host 0.0.0.0 --port 5555 --music_model_name facebook/musicgen-large
```

可选参数:
- `--host`: 服务监听地址，默认为 0.0.0.0
- `--port`: 服务监听端口，默认为 5555
- `--music_model_name`: 音乐生成模型名称，默认为 facebook/musicgen-large

### Docker 构建与部署

本项目提供了完整的 Docker 支持，可以通过以下步骤快速构建和部署 MusicGen API 服务。

#### 1. 准备工作

确保你的系统已安装 Docker 和 NVIDIA Container Toolkit（用于 GPU 支持）。

```bash
# 安装 NVIDIA Container Toolkit（如果尚未安装）
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### 2. 构建 Docker 镜像

项目提供了多个 Dockerfile，用于不同的场景：

- `Dockerfile.audiocraft.cuda121.models.all`: 构建包含所有 MusicGen 模型的基础镜像
- `Dockerfile.musicgen.cuda121.models.tiny`: 构建仅包含小型模型的轻量级镜像
- `Dockerfile.musicgen.model.all.fastapi`: 构建完整的 MusicGen API 服务镜像

##### 构建基础镜像（如果需要）

```bash
cd api/docker
docker build -f Dockerfile.audiocraft.cuda121.models.all -t musicgen:cuda121-models-all .
```

##### 构建 API 服务镜像

```bash
cd api/docker
docker build -f Dockerfile.musicgen.model.all.fastapi -t musicgen:cuda121-models-all-fastapi .
```

#### 3. 运行 Docker 容器

使用以下命令启动 MusicGen API 服务容器：

```bash
docker run -d --restart=unless-stopped --gpus all -p 5555:5555 musicgen:cuda121-models-all-fastapi
```

参数说明：
- `-d`: 后台运行容器
- `--restart=unless-stopped`: 容器异常退出时自动重启
- `--gpus all`: 允许容器访问所有 GPU 资源
- `-p 5555:5555`: 将容器的 5555 端口映射到主机的 5555 端口

#### 4. 自定义模型选择

如果需要使用不同的模型，可以在启动容器时通过环境变量或命令行参数指定：

```bash
docker run -d --restart=unless-stopped --gpus all -p 5555:5555 \
  musicgen:cuda121-models-all-fastapi \
  python3 ./main.py --host 0.0.0.0 --port 5555 --music_model_name facebook/musicgen-medium
```

可选的模型包括：
- `facebook/musicgen-small`
- `facebook/musicgen-medium`
- `facebook/musicgen-large`
- `facebook/musicgen-melody`
- `facebook/musicgen-melody-large`
- `facebook/musicgen-stereo-small`
- `facebook/musicgen-stereo-medium`
- `facebook/musicgen-stereo-large`

#### 5. 使用 Docker Compose 部署

项目提供了 `docker-compose.yml` 文件，可以更方便地部署和管理 MusicGen API 服务：

```bash
cd api/docker
docker-compose up -d
```

Docker Compose 配置具有以下特点：
- 自动构建和启动 API 服务
- 挂载 `output` 和 `log` 目录，方便访问生成的音频文件和日志
- 设置了 GPU 资源分配
- 配置了自动重启策略
- 支持通过环境变量和命令参数自定义配置

如需停止服务：

```bash
cd api/docker
docker-compose down
```

如需修改配置，可以编辑 `docker-compose.yml` 文件，例如更改端口映射或选择不同的模型。

### API 端点

#### 生成音乐
- **URL**: `/api/v1/generate_music`
- **方法**: POST
- **Content-Type**: application/json
- **Accept**: text/event-stream

**请求参数**:
```json
{
  "description": "电子音乐带有强烈的鼓点和节奏感",
  "duration": 30,
  "mbd": false,
  "top_k": 250,
  "top_p": 0.0,
  "temperature": 3.0,
  "cfg_coef": 3.0
}
```

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|-------|------|------|-------|------|
| description | string | 是 | - | 用于音乐生成的文本提示 |
| duration | integer | 否 | 30 | 生成音乐的时长(秒)，范围1-60 |
| mbd | boolean | 否 | false | 是否使用多波段扩散模型增强音质 |
| top_k | integer | 否 | 250 | 采样时考虑的最高概率的标记数 |
| top_p | number | 否 | 0.0 | 采样时考虑的累积概率阈值 (0-1) |
| temperature | number | 否 | 3.0 | 采样温度，控制随机性 |
| cfg_coef | number | 否 | 3.0 | 无分类器指导系数 |

**响应**: 流式 SSE 事件

事件类型:
1. **开始事件**:
   ```json
   data: {"event": "start"}
   ```

2. **进度事件**:
   ```json
   data: {"event": "progress", "progress": 50.0}
   ```

3. **完成事件**:
   ```json
   data: {"event": "completed", "audio": "base64编码的WAV音频数据"}
   ```

4. **错误事件**:
   ```json
   data: {"event": "error", "message": "错误信息"}
   ```

## 客户端示例

### 同步客户端 (requests)

```python
from client_requests import MusicGenClient

client = MusicGenClient(server_url="http://localhost:5555")

params = {
    "description": "电子音乐带有强烈的鼓点和节奏感",
    "duration": 10,
    "mbd": False,
    "top_k": 250,
    "top_p": 0.0,
    "temperature": 1.0,
    "cfg_coef": 3.0
}

client.generate_music(**params)
```

### 异步客户端 (aiohttp)

```python
import asyncio
from client_aiohttp import MusicGenClient

async def main():
    client = MusicGenClient(server_url="http://localhost:5555")
    
    params = {
        "description": "电子音乐带有强烈的鼓点和节奏感",
        "duration": 10,
        "mbd": False,
        "top_k": 250,
        "top_p": 0.0,
        "temperature": 1.0,
        "cfg_coef": 3.0
    }
    
    await client.generate_music(**params)

if __name__ == "__main__":
    asyncio.run(main())
```

## 注意事项

1. 服务使用了信号量限制，同一时间只能处理一个生成请求，多余的请求会返回 503 状态码
2. 生成过程较为耗时，根据模型大小和参数设置，可能需要几十秒到几分钟不等
3. 服务使用较多的 GPU 内存，请确保有足够的 VRAM
4. 音频结果以 Base64 编码的 WAV 格式返回

## 日志系统

项目使用 loguru 配置了详细的日志系统：

- 支持全链路请求追踪，通过 X-Request-Id 头部关联请求
- 日志保存在 log 目录下
- 日志格式包含时间、请求ID、日志级别、进程/线程信息和消息内容

## 未来计划

- [ ] 添加批处理模式，支持批量生成
- [ ] 实现模型预热功能，提高首次生成速度
- [ ] 添加更多风格控制参数
- [ ] 支持提示词增强功能
- [ ] 实现WebSocket接口，增强实时交互能力

## 许可证

[添加项目许可证信息]
