from service import MusicGenService

import io
import re
import scipy
from loguru import logger
import numpy as np

import base64
import typing as tp

class MusicController:
    def __init__(self):
        self.musicgen_service = MusicGenService()

    def generate_music_with_progress(self, params: tp.Optional[dict] = None, progress_callback: tp.Optional[tp.Callable[[float], None]] = None) -> str:
        """处理音乐生成请求

        Args:
            params (Optional[dict]): 包含生成参数的字典
                - description: 音乐描述
                - duration: 音频时长（可选，默认30秒）
                - mbd: 是否使用MultiBand Diffusion（可选，默认False）
                - top_k: top-k采样参数（可选，默认250）
                - top_p: top-p采样参数（可选，默认0.0）
                - temperature: 温度参数（可选，默认1.0）
                - cfg_coef: 无分类器指导系数（可选，默认3.0）
            progress_callback: 进度回调函数

        Returns:
            str: Base64编码的WAV音频数据
        """
        # 检查必需参数
        if not params or not isinstance(params, dict):
            raise ValueError("Invalid parameters")
        
        if 'description' not in params:
            raise ValueError("Description is required")
        
        description = params['description']

        # 参数验证
        mbd = params.get('mbd', False)
        if not isinstance(mbd, bool):
            raise ValueError("MBD parameter must be a boolean")
        
        duration = params.get('duration', 30)
        if not isinstance(duration, int) or duration < 1:
            raise ValueError("Duration must be a positive integer")

        top_k = params.get('top_k', 250)
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")

        top_p = params.get('top_p', 0.0)
        if not isinstance(top_p, (int, float)) or not 0 <= top_p <= 1:
            raise ValueError("top_p must be a float between 0 and 1")

        temperature = params.get('temperature', 3.0)
        if not isinstance(temperature, (int, float)) or temperature < 0:
            raise ValueError("temperature must be a positive number")

        cfg_coef = params.get('cfg_coef', 3.0)
        if not isinstance(cfg_coef, (int, float)):
            raise ValueError("cfg_coef must be a number")

        try:
            # 创建内存缓冲区存储音频
            audio_buffer = io.BytesIO()
            
            # 生成音频
            audio_tensor, sampling_rate = self.musicgen_service.generate_music(
                description, 
                mbd=mbd,
                duration=duration, 
                top_k=top_k, 
                top_p=top_p, 
                temperature=temperature,
                cfg_coef=cfg_coef, 
                progress_callback=progress_callback 
            )
            
            # 确保音频数组维度正确
            if audio_tensor.ndim > 2:
                audio_tensor = audio_tensor[0]  # 移除批次维度
            
            # 转换为16位整数格式
            audio_numpy = (audio_tensor * 32767).clip(-32768, 32767).astype(np.int16)
            
            # 写入WAV文件
            scipy.io.wavfile.write(
                audio_buffer,
                rate=sampling_rate,
                data=audio_numpy
            )
            
            # 重置缓冲区位置并转换为Base64
            audio_buffer.seek(0)
            audio_base64 = base64.b64encode(audio_buffer.read()).decode('utf-8')
            
            return audio_base64
        
        except InterruptedError as e:
            logger.error(f"InterruptedError during music generation: {str(e)}")
            raise InterruptedError(f"InterruptedError during music generation: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error during music generation: {str(e)}")
            raise ValueError(f"Error during music generation: {str(e)}")