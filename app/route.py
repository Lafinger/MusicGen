from .controller import MusicController

from flask import Blueprint, request, jsonify, Response, stream_with_context, copy_current_request_context
import json


from queue import Queue, Empty
import threading
import logging

logger = logging.getLogger(__name__)
music_controller = MusicController()
health_bp = Blueprint('health_bp', __name__)
music_bp = Blueprint('music_bp', __name__)

# 添加信号量来控制并发
generation_lock = threading.Semaphore(1)

@health_bp.route('/healthcheck', methods=['GET'])
def handle_healthcheck():
    if not generation_lock.acquire(blocking=False):
        return jsonify({"status": "busy"}), 503
    generation_lock.release()  # 立即释放锁
    return jsonify({"status": "healthy"}), 200

@music_bp.route('/music', methods=['POST'])
def handle_music_generation():
    # 尝试获取锁
    if not generation_lock.acquire(blocking=False):
        return jsonify({"status": "busy"}), 503
    
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        if not request.json or not isinstance(request.json, dict):
            return jsonify({"error": "Description is required."}), 400
        
        # 复制请求数据
        request_data = request.json.copy()

        # 创建进度队列和控制标志
        progress_queue = Queue()
        result_queue = Queue()
        should_stop = threading.Event()
        
        def progress_callback(percentage: float):
            if should_stop and should_stop.is_set():
                raise InterruptedError("Music generation stopped by client")
            progress_queue.put(percentage)
        

        def generate():
            try:
                # 发送开始信号
                yield f'event: start\ndata: {json.dumps({"status": "started"})}\n\n'
                
                # 在后台线程中生成音频
                @copy_current_request_context
                def generate_audio():
                    try:
                        audio_data = music_controller.generate_music_with_progress(
                            request_data,
                            progress_callback=progress_callback,
                        )
                        if not should_stop.is_set():
                            result_queue.put(("success", audio_data))
                        else:
                            logger.info("Music generation stopped due to client disconnection")
                    except Exception as e:
                        if not should_stop.is_set():
                            result_queue.put(("error", str(e)))
                    finally:
                        # 确保在音频生成完成后释放锁
                        generation_lock.release()
                        

                audio_thread = threading.Thread(target=generate_audio)
                audio_thread.start()
                
                # 持续发送进度更新直到生成完成或连接断开
                while audio_thread.is_alive():
                    # 检查客户端连接状态
                    wsgi_input = request.environ.get('wsgi.input')
                    if wsgi_input and getattr(wsgi_input, 'closed', False):
                        logger.info("Client connection closed, stopping music generation")
                        should_stop.set()  # 设置停止标志
                        break

                    try:
                        # 非阻塞方式获取进度
                        progress = progress_queue.get(timeout=0.1)
                        yield f'event: progress\ndata: {json.dumps({"status": "generating", "progress": progress})}\n\n'
                    except Empty:
                        continue
                
                audio_thread.join()  # 等待线程结束
                
                # 获取生成结果
                try:
                    status, data = result_queue.get(timeout=1.0)  # 设置超时以防止永久阻塞
                    
                    if status == "error":
                        raise Exception(data)
                    
                    # 发送完成信号和音频数据
                    yield f'event: complete\ndata: {json.dumps({"status": "completed", "audio_data": data})}\n\n'
                except Empty:
                    logger.warning("No result received from music generation thread")
                    yield f'event: error\ndata: {json.dumps({"error": "Music generation timeout"})}\n\n'
                
            except Exception as e:
                # 发送错误信号
                yield f'event: error\ndata: {json.dumps({"error": str(e)})}\n\n'
            finally:
                # 确保设置停止标志
                should_stop.set()
                

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )
        
    except Exception as e:
        # 确保在发生异常时释放锁
        generation_lock.release()
        return jsonify({"error": str(e)}), 500