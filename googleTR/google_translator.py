import sys
import requests
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QComboBox, QMessageBox, QAction, QMenu, QToolBar,
                             QStatusBar, QSplitter, QFrame, QShortcut, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QSize, QUrl, QTranslator, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QThread, QObject
from PyQt5.QtGui import QFont, QIcon, QClipboard, QKeySequence, QColor, QPalette, QLinearGradient, QRadialGradient, QBrush, QPainter
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class LoadingIndicator(QWidget):
    def __init__(self, parent=None):
        super(LoadingIndicator, self).__init__(parent)
        self.setFixedSize(40, 40)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.setVisible(False)
        self.color = QColor("#4285f4")
        
    def rotate(self):
        self.angle = (self.angle + 8) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        
        painter.setPen(Qt.NoPen)
        for i in range(8):
            painter.rotate(45)
            alpha = 255 if i == 0 else int(255 * (8 - i) / 8)
            color = QColor(self.color)
            color.setAlpha(alpha)
            painter.setBrush(color)
            painter.drawRoundedRect(-4, -15, 8, 12, 4, 4)
            
    def start(self):
        self.setVisible(True)
        self.timer.start(80)  # 降低更新频率，减少卡顿
        
    def stop(self):
        self.timer.stop()
        self.setVisible(False)


class SimpleButton(QPushButton):
    """简化的按钮类，减少动画和效果以提高性能"""
    def __init__(self, text, parent=None):
        super(SimpleButton, self).__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5294ff;
            }
            QPushButton:pressed {
                background-color: #3367d6;
            }
        """)


class CopyableTextEdit(QTextEdit):
    """带右键复制功能的文本编辑器"""
    def __init__(self, parent=None):
        super(CopyableTextEdit, self).__init__(parent)
        self.setReadOnly(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.statusBar = None
        
    def setStatusBar(self, statusBar):
        self.statusBar = statusBar
        
    def showContextMenu(self, position):
        menu = QMenu(self)
        copyAction = QAction("复制全部", self)
        copyAction.triggered.connect(self.copyAll)
        menu.addAction(copyAction)
        menu.exec_(self.mapToGlobal(position))
        
    def copyAll(self):
        if self.toPlainText():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.toPlainText())
            if self.statusBar:
                self.statusBar.showMessage("已复制翻译结果到剪贴板", 3000)
    
    # 添加双击复制功能
    def mouseDoubleClickEvent(self, event):
        self.copyAll()
        super().mouseDoubleClickEvent(event)

    # 设置文本的同时将内容复制到剪贴板
    def setTextAndCopy(self, text):
        self.setText(text)
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            if self.statusBar:
                self.statusBar.showMessage("翻译结果已自动复制到剪贴板", 3000)


class GoogleTranslator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("谷歌翻译")
        self.setMinimumSize(800, 500)
        
        # 静态背景颜色
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QTextEdit {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 14px;
                padding: 10px;
                border: 1px solid #444444;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QTextEdit:focus {
                border: 1px solid #4285f4;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 14px;
                font-weight: bold;
                color: #e0e0e0;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #444444;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding-left: 10px;
            }
            QComboBox:hover {
                border: 1px solid #4285f4;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #4285f4;
                outline: none;
            }
            QSplitter::handle {
                background-color: #444444;
            }
            QStatusBar {
                color: #a0a0a0;
                background-color: #1e1e1e;
            }
            QToolBar {
                background-color: #1e1e1e;
                border-bottom: 1px solid #444444;
                spacing: 5px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                color: #e0e0e0;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QToolBar QToolButton:hover {
                background-color: #2d2d2d;
            }
            QToolBar QToolButton:pressed {
                background-color: #3d3d3d;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #5a5a5a;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #2d2d2d;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #5a5a5a;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            
            /* 提示信息 */
            #copyTip {
                color: #a0a0a0;
                font-size: 12px;
                font-style: italic;
                padding: 0px;
                background-color: transparent;
            }
            
            /* 美化翻译结果文本框 */
            #resultTextEdit {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 15px;
                line-height: 1.5;
                color: #ffffff;
                background-color: #2a2a2a;
                border: 1px solid #444444;
                padding: 15px;
            }
        """)
        
        # 创建主窗口部件和布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建翻译界面
        self.create_translation_interface()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 网络管理器
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.handle_network_reply)
        
        # 快捷键
        self.create_shortcuts()
        
        # 加载指示器
        self.loading_indicator = LoadingIndicator(self)
        self.loading_indicator.move(self.width() // 2 - 20, self.height() // 2 - 20)
        
        # 应用黑色主题
        self.apply_dark_theme()
        
        # 使用防抖定时器进行实时翻译
        self.translate_timer = QTimer()
        self.translate_timer.setSingleShot(True)
        self.translate_timer.timeout.connect(self.translate_text)
    
    def apply_dark_theme(self):
        """应用黑色主题到应用程序"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.Base, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.AlternateBase, QColor(60, 60, 60))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.Text, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Link, QColor(66, 133, 244))
        dark_palette.setColor(QPalette.Highlight, QColor(66, 133, 244))
        dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))
        self.setPalette(dark_palette)
    
    def resizeEvent(self, event):
        """重新定位加载指示器"""
        self.loading_indicator.move(self.width() // 2 - 20, self.height() // 2 - 20)
        super().resizeEvent(event)
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 添加工具栏按钮 - 只保留必要的按钮
        action_clear = QAction("清空", self)
        action_clear.triggered.connect(self.clear_text)
        toolbar.addAction(action_clear)
        
        action_swap = QAction("交换语言", self)
        action_swap.triggered.connect(self.swap_languages)
        toolbar.addAction(action_swap)
        
        toolbar.addSeparator()
        
        action_about = QAction("关于", self)
        action_about.triggered.connect(self.show_about)
        toolbar.addAction(action_about)
    
    def create_translation_interface(self):
        # 语言选择框布局
        lang_layout = QHBoxLayout()
        
        # 源语言
        self.source_lang_label = QLabel("源语言:")
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["中文 (简体)", "英语", "日语", "韩语", "法语", "德语", "西班牙语", "俄语"])
        self.source_lang_combo.setCurrentIndex(0)  # 默认中文
        self.source_lang_combo.currentIndexChanged.connect(self.on_language_changed)
        
        # 目标语言
        self.target_lang_label = QLabel("目标语言:")
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["英语", "中文 (简体)", "日语", "韩语", "法语", "德语", "西班牙语", "俄语"])
        self.target_lang_combo.setCurrentIndex(0)  # 默认英语
        self.target_lang_combo.currentIndexChanged.connect(self.on_language_changed)
        
        # 添加到布局
        lang_layout.addWidget(self.source_lang_label)
        lang_layout.addWidget(self.source_lang_combo)
        lang_layout.addStretch()
        lang_layout.addWidget(self.target_lang_label)
        lang_layout.addWidget(self.target_lang_combo)
        
        self.main_layout.addLayout(lang_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(10)
        
        # 源文本区域
        source_frame = QFrame()
        source_frame.setFrameShape(QFrame.StyledPanel)
        source_frame.setStyleSheet("background-color: rgba(45, 45, 45, 225);")
        source_layout = QVBoxLayout(source_frame)
        
        self.source_label = QLabel("输入要翻译的文本:")
        source_layout.addWidget(self.source_label)
        
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("在此输入文本，自动翻译并复制到剪贴板...")
        self.source_text.textChanged.connect(self.on_text_changed)
        source_layout.addWidget(self.source_text)
        
        # 目标文本区域 - 美化翻译结果显示
        target_frame = QFrame()
        target_frame.setFrameShape(QFrame.StyledPanel)
        target_frame.setStyleSheet("""
            background-color: #252525;
            border: 1px solid #333333;
            border-radius: 5px;
        """)
        target_layout = QVBoxLayout(target_frame)
        
        # 结果标题区域
        result_header = QFrame()
        result_header.setStyleSheet("""
            background-color: #333333;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            padding: 5px;
        """)
        result_header_layout = QHBoxLayout(result_header)
        result_header_layout.setContentsMargins(10, 5, 10, 5)
        
        self.target_label = QLabel("翻译结果:")
        self.target_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        result_header_layout.addWidget(self.target_label)
        result_header_layout.addStretch()
        
        # 添加自动复制提示
        self.copy_tip = QLabel("已自动复制到剪贴板，随时可粘贴使用")
        self.copy_tip.setObjectName("copyTip")
        result_header_layout.addWidget(self.copy_tip)
        
        target_layout.addWidget(result_header)
        
        # 使用自定义可复制文本框
        self.target_text = CopyableTextEdit()
        self.target_text.setObjectName("resultTextEdit")
        self.target_text.setPlaceholderText("翻译结果将显示在这里...")
        self.target_text.setStatusBar(self.statusBar)
        self.target_text.setStyleSheet("""
            border-top: none;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            padding: 15px;
            font-size: 15px;
            line-height: 1.5;
        """)
        target_layout.addWidget(self.target_text)
        
        # 添加到分割器
        splitter.addWidget(source_frame)
        splitter.addWidget(target_frame)
        splitter.setSizes([200, 200])  # 设置初始大小
        
        self.main_layout.addWidget(splitter)
    
    def create_shortcuts(self):
        # 清空
        shortcut_clear = QShortcut(QKeySequence("Ctrl+D"), self)
        shortcut_clear.activated.connect(self.clear_text)
        
        # 交换语言
        shortcut_swap = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_swap.activated.connect(self.swap_languages)
        
        # 复制翻译结果 (可选，因为已经自动复制)
        shortcut_copy = QShortcut(QKeySequence("Ctrl+C"), self)
        shortcut_copy.activated.connect(lambda: self.target_text.copyAll())
    
    def on_text_changed(self):
        """当文本变化时启动延迟翻译"""
        text = self.source_text.toPlainText()
        if text:
            # 重启定时器，实现防抖功能，避免频繁翻译
            self.translate_timer.stop()
            self.translate_timer.start(300)  # 300毫秒后执行翻译
        else:
            self.target_text.clear()
    
    def on_language_changed(self):
        """当语言选择变化时重新翻译"""
        if self.source_text.toPlainText():
            self.translate_timer.stop()
            self.translate_timer.start(100)  # 快速重新翻译
    
    def translate_text(self):
        """执行翻译操作"""
        text = self.source_text.toPlainText()
        if not text:
            return
        
        # 获取语言代码
        source_lang = self.get_language_code(self.source_lang_combo.currentText())
        target_lang = self.get_language_code(self.target_lang_combo.currentText())
        
        # 显示翻译中状态
        self.statusBar.showMessage("正在翻译...")
        self.loading_indicator.start()
        
        # 使用Google翻译API
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={text}"
        
        # 发送网络请求
        request = QNetworkRequest(QUrl(url))
        self.network_manager.get(request)
    
    def handle_network_reply(self, reply):
        """处理网络响应"""
        self.loading_indicator.stop()
        
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll().data().decode('utf-8')
            try:
                json_data = json.loads(data)
                translated_text = ""
                # 解析Google翻译API的响应
                for sentence in json_data[0]:
                    if sentence[0]:
                        translated_text += sentence[0]
                
                # 设置翻译结果，并自动复制到剪贴板
                self.target_text.setTextAndCopy(translated_text)
                self.statusBar.showMessage("翻译完成并已复制到剪贴板")
            except Exception as e:
                self.statusBar.showMessage(f"解析翻译结果出错: {str(e)}")
        else:
            self.statusBar.showMessage(f"翻译请求失败: {reply.errorString()}")
    
    def get_language_code(self, language):
        """获取语言代码"""
        language_codes = {
            "中文 (简体)": "zh-CN",
            "英语": "en",
            "日语": "ja",
            "韩语": "ko",
            "法语": "fr",
            "德语": "de",
            "西班牙语": "es",
            "俄语": "ru"
        }
        return language_codes.get(language, "en")
    
    def clear_text(self):
        """清空文本框"""
        self.source_text.clear()
        self.target_text.clear()
        self.statusBar.showMessage("已清空", 2000)
    
    def swap_languages(self):
        """交换源语言和目标语言"""
        source_index = self.source_lang_combo.currentIndex()
        target_index = self.target_lang_combo.currentIndex()
        
        self.source_lang_combo.setCurrentIndex(target_index)
        self.target_lang_combo.setCurrentIndex(source_index)
        
        # 同时交换文本
        source_text = self.source_text.toPlainText()
        target_text = self.target_text.toPlainText()
        
        self.source_text.setText(target_text)
        self.target_text.setText(source_text)
        
        self.statusBar.showMessage("已交换语言", 2000)
    
    def show_about(self):
        """显示关于对话框"""
        about_msg = QMessageBox(self)
        about_msg.setWindowTitle("关于")
        about_msg.setText("谷歌翻译桌面应用")
        about_msg.setInformativeText("一个简单高效的翻译工具\n支持多种语言互译\n基于PyQt5开发\n实时翻译，自动复制到剪贴板，随时可粘贴使用")
        about_msg.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #5294ff;
            }
        """)
        about_msg.setIcon(QMessageBox.Information)
        about_msg.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    translator = GoogleTranslator()
    translator.show()
    sys.exit(app.exec_())
