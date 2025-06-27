from audiocraft.models import MusicGen
from audiocraft.models import MultiBandDiffusion
import torchaudio
import torch

# 是否使用扩散解码器
USE_DIFFUSION_DECODER = True


# 使用小型模型，使用 'medium' 或 'large' 可以获得更好的效果
model = MusicGen.get_pretrained('facebook/musicgen-small')

# 设置生成参数
model.set_generation_params(
    use_sampling = True,
    top_k = 250,
    top_p = 0.0,
    temperature = 1.0,
    duration = 30.0,
    cfg_coef = 3.0
)

# 基于文本的音乐生成
output = model.generate(
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
    return_tokens=True  # 返回生成的token序列
)

# 保存生成的音频到文件
output_path = "generated_music.wav"
# 确保音频张量是2D的 [channels, samples]
audio = output[0].cpu().squeeze(0)  # 移除批次维度
if audio.dim() == 1:
    print("audio.dim() == 1")
    audio = audio.unsqueeze(0)  # 添加通道维度
# 确保音频格式正确
audio = audio.float()  # 确保是浮点数格式
torchaudio.save(output_path, audio, sample_rate=32000, format="wav")  # 保存为WAV格式，采样率32kHz
print(f"音频已保存到: {output_path}")


# 如果启用了扩散解码器，则同时生成扩散版本的音频
if USE_DIFFUSION_DECODER:
    mbd = MultiBandDiffusion.get_mbd_musicgen()

if USE_DIFFUSION_DECODER:
    out_diffusion = mbd.tokens_to_wav(output[1])  # 将token转换为波形
    # 同样处理扩散解码器的输出
    audio_diffusion = out_diffusion.cpu().squeeze(0)  # 移除批次维度
    if audio_diffusion.dim() == 1:
        audio_diffusion = audio_diffusion.unsqueeze(0)  # 添加通道维度
    audio_diffusion = audio_diffusion.float()  # 确保是浮点数格式
    torchaudio.save("generated_music_diffusion.wav", audio_diffusion, sample_rate=32000, format="wav")  # 保存扩散版本的音频
    print("使用扩散解码器的音频已保存到: generated_music_diffusion.wav")