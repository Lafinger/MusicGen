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

    def init_music_model(self, model_name: str = 'facebook/musicgen-large') -> None:
        self.musicgen_service.init_music_model(model_name)

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

        try:
            # 参数验证
            assert params and isinstance(params, dict) and 'description' in params

            mbd = params.get('mbd', False)
            assert isinstance(mbd, bool)

            duration = params.get('duration', 30)
            assert isinstance(duration, int) and 1 <= duration <= 60

            top_k = params.get('top_k', 250)
            assert isinstance(top_k, int) and top_k > 0

            top_p = params.get('top_p', 0.0)
            assert isinstance(top_p, (int, float)) and 0 <= top_p <= 1

            temperature = params.get('temperature', 3.0)
            assert isinstance(temperature, (int, float)) and temperature >= 0

            cfg_coef = params.get('cfg_coef', 3.0)
            assert isinstance(cfg_coef, (int, float))
        except AssertionError as e:
            raise AssertionError(e)

        # 创建内存缓冲区存储音频
        audio_buffer = io.BytesIO()
        
        # 生成音频
        audio_tensor, sampling_rate = self.musicgen_service.generate_music(
            params['description'], 
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