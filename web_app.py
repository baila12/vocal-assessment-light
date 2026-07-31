"""
v7.6 入口重定向 — Flask 绞杀者已完成, 请使用 FastAPI

启动命令:
  python backend/main.py          # FastAPI 开发模式 (:8000)

旧 Flask 入口 (python web_app.py) 已废弃。
Flask 路由层 (api/routes/) 已移除 — 所有功能已迁移至 FastAPI /api/v1/。
"""
import sys
import os

if __name__ == "__main__":
    print(__doc__)
    print("正在启动 FastAPI 开发服务器...")
    os.execl(sys.executable, sys.executable, "backend/main.py")
