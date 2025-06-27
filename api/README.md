# 音乐生成 WebSocket 服务

这是一个基于 FastAPI 和 WebSocket 的音乐生成服务，使用 Facebook 的 MusicGen 模型来生成音乐。

## 功能特点

- 实时音乐生成进度更新
- WebSocket 连接支持
- 自动保存生成历史
- 支持自定义音乐生成参数

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行服务

```bash
python api/main.py
```

服务将在 `http://localhost:8000` 启动。

## WebSocket API 使用说明

1. 连接 WebSocket：
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{client_id}');
```

2. 发送生成请求：
```javascript
ws.send(JSON.stringify({
    type: 'generate',
    prompt: '你的音乐描述',
    duration: 30,  // 可选，默认30秒
    mbd: false     // 可选，默认false
}));
```

3. 接收进度更新：
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'progress') {
        console.log(`生成进度: ${data.data}%`);
    } else if (data.type === 'complete') {
        console.log(`生成完成，文件名: ${data.data}`);
    }
};
```

## 生成的文件

生成的音频文件将保存在 `audios` 目录下，文件名格式为 `jc_music_gen_timestamp.wav`。

## 历史记录

所有生成历史将被记录在 `history.json` 文件中。