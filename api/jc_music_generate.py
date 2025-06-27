from audiocraft.models import MusicGen
from audiocraft.models import MultiBandDiffusion
import torchaudio
import time
import json
import os
from typing import Callable, Optional, Any

# from openai import OpenAI 
# from dotenv import load_dotenv
# load_dotenv()


class JcMusicGenerate:
    def __init__(self) -> None:
        self.model = MusicGen.get_pretrained('facebook/musicgen-small')
        self._progress_callback: Optional[Callable[[int, int], Any]] = None
        
    def set_progress_callback(self, callback: Callable[[int, int], Any]) -> None:
        """设置进度回调函数"""
        self._progress_callback = callback
        
    def generate_music(self, user_prompt: str, mbd: bool = False, duration: int = 30):
        print("GENERATION STARTED.......")
        # 使用类的回调函数
        if self._progress_callback:
            self.model.set_custom_progress_callback(self._progress_callback)
        else:
            self.model.set_custom_progress_callback(self.progress_callback)
            
        self.model.set_generation_params(
            use_sampling = True,
            top_k = 250,
            top_p = 0.0,
            temperature = 1.0,
            duration = duration,
            cfg_coef = 3.0
        )
        enhanced_prompt = self.enhance_user_prompt(user_prompt)
        print("Enhanced prompt :", enhanced_prompt)

        outputs = self.model.generate(
            descriptions=[
                #'80s pop track with bassy drums and synth',  # 80年代流行音乐，重低音鼓点和合成器
                #'90s rock song with loud guitars and heavy drums',  # 90年代摇滚，响亮的吉他和重鼓点
                #'Progressive rock drum and bass solo',  # 前卫摇滚的鼓点和贝斯独奏
                #'Punk Rock song with loud drum and power guitar',  # 朋克摇滚，响亮的鼓点和强力吉他
                #'Bluesy guitar instrumental with soulful licks and a driving rhythm section',  # 布鲁斯吉他器乐，富有灵魂的旋律和强劲的节奏部分
                #'Jazz Funk song with slap bass and powerful saxophone',  # 爵士放克，击弦贝斯和强力萨克斯
                'drum and bass beat with intense percussions'  # 生成鼓点和重低音节奏
            ],
            progress=True,  # 显示生成进度
            return_tokens=mbd  # 返回生成的token序列
        )

        # # 确保音频张量是2D的 [channels, samples]
        # audio = res[0].cpu().squeeze(0)  # 移除批次维度
        # if audio.dim() == 1:
        #     print("audio.dim() == 1")
        #     audio = audio.unsqueeze(0)  # 添加通道维度
        # # 确保音频格式正确
        # audio = audio.float()  # 确保是浮点数格式

        # folder_path = "audios"
        # self.ensure_folder_exists(folder_path)
        # file_name = self.generate_filename()
        # torchaudio.save(f"{folder_path}/{file_name}", audio, sample_rate=32000, format="wav")  # 保存为WAV格式，采样率32kHz

        # self.save_history({
        #     "user_prompt":user_prompt,
        #     "enchanted_prompt":enhanced_prompt,
        #     "filename":file_name
        # })
        # print(f"GENERATION FINISHED :) File saved as {file_name}")
        # return file_name

        if mbd:
            if gradio_progress is not None:
                gradio_progress(1, desc='Running MultiBandDiffusion...')
            tokens = outputs[1]
            if isinstance(MODEL.compression_model, InterleaveStereoCompressionModel):
                left, right = MODEL.compression_model.get_left_right_codes(tokens)
                tokens = torch.cat([left, right])
            outputs_diffusion = MBD.tokens_to_wav(tokens)
            if isinstance(MODEL.compression_model, InterleaveStereoCompressionModel):
                assert outputs_diffusion.shape[1] == 1  # output is mono
                outputs_diffusion = rearrange(outputs_diffusion, '(s b) c t -> b (s c) t', s=2)
            outputs = torch.cat([outputs[0], outputs_diffusion], dim=0)
        outputs = outputs.detach().cpu().float()
        pending_videos = []
        out_wavs = []
        for output in outputs:
            with NamedTemporaryFile("wb", suffix=".wav", delete=False) as file:
                audio_write(
                    file.name, output, MODEL.sample_rate, strategy="loudness",
                    loudness_headroom_db=16, loudness_compressor=True, add_suffix=False)
                pending_videos.append(pool.submit(make_waveform, file.name))
                out_wavs.append(file.name)
                file_cleaner.add(file.name)
        out_videos = [pending_video.result() for pending_video in pending_videos]
        for video in out_videos:
            file_cleaner.add(video)
        print("batch finished", len(texts), time.time() - be)
        print("Tempfiles currently stored: ", len(file_cleaner.files))
        return out_videos, out_wavs

        
    
    def progress_callback(self, generated: int, to_generate: int):
        """默认的进度回调函数"""
        percentage = (generated/to_generate)*100
        print(f"Progress: {percentage:.2f}%")

    def generate_filename(self):
        timestamp = int(time.time())
        return f"jc_music_gen_{timestamp}.wav"

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

    def ensure_folder_exists(self, folder_path: str):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder_path}' created.")
    
    def save_history(self, new_entry: dict):
        try:
            with open("history.json", "r") as file:
                data = json.load(file)  # Load existing JSON content
        except FileNotFoundError:
            # Initialize data if the file doesn't exist
            data = {"generations": []}

        # Add the new entry to the 'generations' array
        data["generations"].append(new_entry)

        with open("history.json", "w") as file:
            json.dump(data, file, indent=4)

        print("New entry added successfully!")


# # test
# jc_music_generate = JcMusicGenerate()
# jc_music_generate.generate_music("drum and bass beat with intense percussions", mbd=False, duration=30)