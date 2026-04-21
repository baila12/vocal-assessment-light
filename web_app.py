"""
声乐评估系统 - Web版入口文件
使用新的分层架构

运行方式：
    python web_app.py

访问地址：
    http://localhost:5000
"""
from api import create_app

# 创建应用
app = create_app()

if __name__ == '__main__':
    print("=" * 50)
    print("声乐评估系统 Web版 - http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
