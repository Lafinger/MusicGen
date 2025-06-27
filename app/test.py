import pytest
from flask import Flask
import json
import numpy as np
from app.route import music_bp, health_bp
from app.controller import MusicController
from app.service import MusicGenService

@pytest.fixture
def app():
    """创建测试用的Flask应用"""
    app = Flask(__name__)
    app.register_blueprint(music_bp)
    app.register_blueprint(health_bp)
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def music_service():
    """获取MusicGenService实例"""
    return MusicGenService()

@pytest.fixture
def music_controller():
    """获取MusicController实例"""
    return MusicController()

class TestHealthCheck:
    """健康检查接口测试"""
    
    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get('/healthcheck')
        assert response.status_code == 200
        assert response.json == {"message": "Service is healthy."}

class TestMusicGeneration:
    """音乐生成功能测试"""
    
    def test_missing_description(self, client):
        """测试缺少描述参数的情况"""
        response = client.post('/music', json={})
        assert response.status_code == 400
        assert response.json == {"error": "Description is required."}

    def test_invalid_duration(self, client):
        """测试无效的duration参数"""
        response = client.post('/music', json={
            "description": "test music",
            "duration": -1
        })
        assert response.status_code == 400
        assert response.json == {"error": "Duration must be a positive integer."}

    def test_invalid_mbd_type(self, client):
        """测试无效的mbd参数类型"""
        response = client.post('/music', json={
            "description": "test music",
            "mbd": "true"  # 应该是布尔值
        })
        assert response.status_code == 400
        assert response.json == {"error": "MBD parameter must be a boolean."}

    def test_invalid_top_k(self, client):
        """测试无效的top_k参数"""
        response = client.post('/music', json={
            "description": "test music",
            "top_k": -1
        })
        assert response.status_code == 400
        assert response.json == {"error": "top_k must be a positive integer."}

    def test_invalid_top_p(self, client):
        """测试无效的top_p参数"""
        response = client.post('/music', json={
            "description": "test music",
            "top_p": 2.0
        })
        assert response.status_code == 400
        assert response.json == {"error": "top_p must be a float between 0 and 1."}

    def test_invalid_temperature(self, client):
        """测试无效的temperature参数"""
        response = client.post('/music', json={
            "description": "test music",
            "temperature": -1.0
        })
        assert response.status_code == 400
        assert response.json == {"error": "temperature must be a positive number."}

    def test_invalid_cfg_coef(self, client):
        """测试无效的cfg_coef参数"""
        response = client.post('/music', json={
            "description": "test music",
            "cfg_coef": "invalid"
        })
        assert response.status_code == 400
        assert response.json == {"error": "cfg_coef must be a number."}

    def test_successful_generation(self, client):
        """测试成功生成音乐"""
        response = client.post('/music', json={
            "description": "test electronic music",
            "duration": 5,
            "mbd": False,
            "top_k": 250,
            "top_p": 0.0,
            "temperature": 1.0,
            "cfg_coef": 3.0
        })
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'audio/wav'
        assert response.headers['Content-Disposition'].startswith('attachment; filename=')

class TestMusicController:
    """控制器层测试"""

    def test_sanitize_description(self, music_controller):
        """测试描述文本清理功能"""
        description = "Test! @#$% Music 123"
        sanitized = music_controller._sanitize_description(description)
        assert len(sanitized) <= 20
        assert all(c.isalnum() for c in sanitized)

    def test_generate_music_params_validation(self, music_controller):
        """测试参数验证"""
        # 测试缺少描述
        response, status = music_controller.generate_music({})
        assert status == 400
        assert response["error"] == "Description is required."

        # 测试无效duration
        response, status = music_controller.generate_music({
            "description": "test",
            "duration": "invalid"
        })
        assert status == 400
        assert response["error"] == "Duration must be a positive integer."

class TestMusicService:
    """服务层测试"""

    def test_singleton_instance(self):
        """测试单例模式"""
        service1 = MusicGenService()
        service2 = MusicGenService()
        assert service1 is service2

    def test_model_initialization(self, music_service):
        """测试模型初始化"""
        assert music_service.model is not None
        assert music_service.mbd_model is not None

    def test_audio_generation(self, music_service):
        """测试音频生成"""
        description = "test electronic music"
        audio_tensor, sample_rate = music_service.generate_audio(
            description,
            duration=5,
            mbd=False,
            top_k=250,
            top_p=0.0,
            temperature=1.0,
            cfg_coef=3.0
        )
        
        # 检查生成的音频数据
        assert isinstance(audio_tensor, np.ndarray)
        assert sample_rate == 32000  # 默认采样率
        assert len(audio_tensor.shape) in [1, 2]  # 单声道或立体声
        
        # 检查音频长度（近似值，考虑到生成过程的变化）
        expected_length = 5 * sample_rate  # duration * sample_rate
        assert abs(audio_tensor.shape[-1] - expected_length) < sample_rate  # 允许1秒的误差

if __name__ == '__main__':
    pytest.main(['-v', 'test.py'])
