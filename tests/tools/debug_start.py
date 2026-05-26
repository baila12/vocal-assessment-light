"""
诊断启动脚本 - 查找崩溃原因
"""
import sys
import traceback

def main():
    print("=" * 50)
    print("声乐评估系统诊断启动")
    print("=" * 50)

    try:
        print("\n[1/6] 导入PySide6...")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QFile, QTextStream, QTimer
        print("      成功")

        print("\n[2/6] 创建QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("声乐评估系统")
        print("      成功")

        print("\n[3/6] 导入主窗口模块...")
        from windows.main_window import MainWindow
        print("      成功")

        print("\n[4/6] 创建主窗口...")
        window = MainWindow()
        print("      成功")

        print("\n[5/6] 显示窗口...")
        window.show()
        print(f"      成功 - 窗口大小: {window.width()}x{window.height()}")
        print(f"      可见: {window.isVisible()}")

        print("\n[6/6] 进入事件循环...")
        print("      如果窗口闪退，请查看下方错误信息")
        print("-" * 50)

        app.exec()

        print("\n程序正常退出")

    except Exception as e:
        print(f"\n!!! 错误发生 !!!")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {e}")
        print("\n完整堆栈:")
        traceback.print_exc()

        input("\n按回车键退出...")

if __name__ == "__main__":
    main()
