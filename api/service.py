from loguru import logger
from audiocraft.models.encodec import InterleaveStereoCompressionModel
from audiocraft.models import MusicGen, MultiBandDiffusion
from audiocraft.data.audio import audio_write

import torch
import time
import typing as tp
from einops import rearrange

class MusicGenService:
    ''' 音乐生成服务 '''

    _instance: tp.Optional['MusicGenService'] = None

    def __new__(cls):
        ''' 单例模式 '''
        if cls._instance is None:
            cls._instance = super(MusicGenService, cls).__new__(cls)
        else:
            logger.warning("MusicGenService already initialized")
        return cls._instance

    def init_music_model(self, model_name: str = 'facebook/musicgen-large'):
        ''' 初始化模型和处理器资源 '''

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available")

        self.model = MusicGen.get_pretrained(model_name)
        self.mbd_model = MultiBandDiffusion.get_mbd_musicgen()
    
    def enhance_user_prompt(self, user_prompt: str):
        # client = OpenAI(api_key=os.environ.get("o_key"))
        # completion = client.chat.completions.create(
        # model="gpt-4o-mini",
        # messages=[
        #     {"role": "system", "content": "You are a prompt creator for text to music models but prompt should be less than 200 characters. enhance the provide prompt by adding more detailed into it and give the one enhance prompt only does not include anything else"},
        #     {"role": "user", "content": user_prompt}  # <-- This is the user message for which the model will generate a response
        # ]
        # )
        # return completion.choices[0].message.content
        return user_prompt

    

    def generate_music(
        self, 
        user_prompt: str, 
        mbd: bool = False, 
        duration: int = 30, 
        top_k: int = 250, 
        top_p: float = 0.0, 
        temperature: float = 1.0, 
        cfg_coef: float = 3.0,
        progress_callback: tp.Optional[tp.Callable[[float], None]] = None
        ):
        """生成音频数据

        Args:
            user_prompt (str): 用户输入的音乐描述
            mbd (bool, optional): 是否使用MultiBand Diffusion. Defaults to False.
            duration (int, optional): 音频时长（秒）. Defaults to 30.
            top_k (int, optional): top-k采样参数. Defaults to 250.
            top_p (float, optional): top-p采样参数. Defaults to 0.0.
            temperature (float, optional): 温度参数. Defaults to 1.0.
            cfg_coef (float, optional): 无分类器指导系数. Defaults to 3.0.
            progress_callback: 音乐处理中的回调函数. Defaults to None.

        Returns:
            tuple: (audio_tensor, sample_rate)
            
        Raises:
            InterruptedError: 当生成过程被用户中断时抛出
            Exception: 其他生成过程中的错误
        """
        logger.info("Generate audio start")
        start_time = time.time()

        def progress_handler(generated, to_generate):
            percentage = (generated/to_generate)*100
            logger.info(f"generate music progress: {percentage:.2f}%")
            if progress_callback:
                progress_callback(percentage)

        self.model.set_custom_progress_callback(progress_handler)

        self.model.set_generation_params(
            top_k = top_k,
            top_p = top_p,
            temperature = temperature,
            duration = duration,
            cfg_coef = cfg_coef
        )
        
        enhanced_prompt = self.enhance_user_prompt(user_prompt)
        logger.info(f"Enhanced prompt : {enhanced_prompt}")

        outputs = self.model.generate(
            descriptions=[enhanced_prompt],
            progress=True,
            return_tokens=mbd
        )

        if mbd:
            tokens = outputs[1]
            if isinstance(self.model.compression_model, InterleaveStereoCompressionModel):
                left, right = self.model.compression_model.get_left_right_codes(tokens)
                tokens = torch.cat([left, right])
            outputs_diffusion = self.mbd_model.tokens_to_wav(tokens)
            if isinstance(self.model.compression_model, InterleaveStereoCompressionModel):
                assert outputs_diffusion.shape[1] == 1  # output is mono
                outputs_diffusion = rearrange(outputs_diffusion, '(s b) c t -> b (s c) t', s=2)
            audio_tensor = torch.cat([outputs[0], outputs_diffusion], dim=0)
        else:
            audio_tensor = outputs[0]  # 只获取音频数据，不需要tokens
        
        # 确保音频数据格式正确并转换为numpy数组
        audio_tensor = audio_tensor.detach().cpu()
        
        # 如果是批处理输出，只取第一个样本
        if audio_tensor.dim() == 3:  # (batch, channels, samples)
            audio_tensor = audio_tensor[0]  # 只取第一个样本，变成 (channels, samples)
        
        # 转换为numpy数组
        audio_tensor = audio_tensor.numpy()
        
        # 如果是单声道，压缩为1D数组
        if audio_tensor.shape[0] == 1:  # 如果是单声道
            logger.info("Audio tensor squeeze")
            audio_tensor = audio_tensor.squeeze()  # 移除多余的维度
        
        logger.info(f"Generate audio completed, elapsed time: {time.time() - start_time:.2f} seconds")
        return audio_tensor, self.model.sample_rate