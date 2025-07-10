# MusicGen API 服务

基于 Facebook 的 MusicGen 模型实现的音乐生成 API 服务。本项目提供了一个易于使用的 FastAPI 接口，支持流式响应的文本到音乐生成功能。

## 项目特点

- 使用 FastAPI 搭建高性能 API
- 支持 SSE (Server-Sent Events) 流式响应，实时展示生成进度
- 基于 Facebook 的 MusicGen 大型音乐生成模型
- 支持多波段扩散 (Multi-Band Diffusion) 增强音质
- 完整的日志追踪系统，支持全链路请求跟踪
- 提供同步和异步两种客户端示例
- Docker 部署支持，便于快速搭建服务

## 快速开始

### 1. 直接运行

详细说明请参考 [API 文档](api/README.md)。

```bash
cd api
python main.py --host 0.0.0.0 --port 5555 --music_model_name facebook/musicgen-large
```

### 2. Docker 部署

```bash
cd api/docker
docker-compose up -d
```

## 目录结构

- `api/` - API 服务主目录
  - `main.py` - 服务入口
  - `controller.py` - 控制器层
  - `service.py` - 服务层
  - `client_requests.py` - 同步客户端示例
  - `client_aiohttp.py` - 异步客户端示例
  - `docker/` - Docker 配置目录

## 详细文档

- [API 服务详细文档](api/README.md)
- [Docker 部署说明](api/docker/README.md)

## 许可证

[添加项目许可证信息]
