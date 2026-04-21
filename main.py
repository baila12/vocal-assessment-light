"""
声乐评估系统 - 应用入口
"""
import sys
from pathlib import Path
print("启动程序...")

print("导入PySide6...")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream
print("PySide6导入成功")

print("导入MainWindow...")
from windows import MainWindow
print("MainWindow导入成功")


def load_stylesheet(app: QApplication):
    style_path = Path(__file__).parent / "styles" / "light_theme.qss"
    if style_path.exists():
        file = QFile(str(style_path))
        if file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(file)
            app.setStyleSheet(stream.readAll())
            file.close()


def main():
    print("创建QApplication...")
    app = QApplication(sys.argv)
    print("QApplication创建成功")

    app.setApplicationName("声乐评估系统")
    app.setApplicationVersion("1.0.0")

    print("加载样式表...")
    load_stylesheet(app)
    print("样式表加载完成")

    print("创建MainWindow...")
    window = MainWindow()
    print("MainWindow创建成功")

    print("显示窗口...")
    window.show()
    print("窗口已显示，进入事件循环...")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()