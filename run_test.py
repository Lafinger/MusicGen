import pytest
import sys

if __name__ == '__main__':
    # 运行app目录下的所有测试
    sys.exit(pytest.main(['-v', 'app/test.py'])) 