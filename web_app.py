"""
声乐评估系统 - Web版入口文件
使用新的分层架构

运行方式：
    python web_app.py

访问地址：
    http://localhost:5000

环境变量:
    FLASK_DEBUG=1  启用调试模式（开发用，生产环境请勿使用）
"""
import os
from api import create_app

# 创建应用
app = create_app()

if __name__ == '__main__':
    # debug=True 仅在生产环境通过环境变量 FLASK_DEBUG=1 启用
    # Werkzeug debugger 可执行任意代码，生产环境严禁开启
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'

    print("=" * 50)
    print("声乐评估系统 Web版 - http://localhost:5000")
    if debug_mode:
        print("[WARNING] 调试模式已开启，生产环境请勿使用！")
        print("[WARNING] 设置 FLASK_DEBUG=0 关闭调试模式")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=debug_mode, threaded=True, use_reloader=False)
