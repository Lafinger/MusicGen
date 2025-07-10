# MusicGen API Docker 部署

本目录包含用于构建和部署 MusicGen API 服务的 Docker 配置文件。

## 文件说明

- `Dockerfile.audiocraft.cuda121.models.all` - 包含所有 MusicGen 模型的基础镜像
- `Dockerfile.musicgen.cuda121.models.tiny` - 仅包含小型模型的轻量级镜像
- `Dockerfile.musicgen.model.all.fastapi` - 完整的 MusicGen API 服务镜像
- `docker-compose.yml` - Docker Compose 配置文件
- `docker_install.txt` - Docker 安装和使用的简要说明

## 构建和运行

### 使用 Docker 命令

1. 构建基础镜像（如果需要）：
   ```bash
   docker build -f Dockerfile.audiocraft.cuda121.models.all -t musicgen:cuda121-models-all .
   ```

2. 构建 API 服务镜像：
   ```bash
   docker build -f Dockerfile.musicgen.model.all.fastapi -t musicgen:cuda121-models-all-fastapi .
   ```

3. 运行容器：
   ```bash
   docker run -d --restart=unless-stopped --gpus all -p 5555:5555 musicgen:cuda121-models-all-fastapi
   ```

### 使用 Docker Compose

1. 一键部署：
   ```bash
   docker compose up -d
   ```

2. 停止服务：
   ```bash
   docker compose down
   ```

## 目录挂载

Docker Compose 配置中挂载了以下目录：

- `../output:/workspace/MusicGen/api/output` - 生成的音频文件保存位置
- `../log:/workspace/MusicGen/api/log` - 日志文件保存位置

## 自定义配置

可以通过修改 `docker-compose.yml` 文件自定义以下配置：

- 端口映射
- 使用的模型
- GPU 资源分配
- 时区设置
- 挂载目录

## 注意事项

- 确保主机已安装 NVIDIA Container Toolkit
- 基础镜像较大，首次构建可能需要较长时间
- 使用 `--no-cache` 参数可以强制重新构建镜像 