import os
import json
import shutil
import subprocess
import sys
import requests
import zipfile
import platform
import configparser
import webbrowser
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from threading import Thread
from queue import Queue
from urllib.parse import quote

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QComboBox, QProgressBar,
                             QTextEdit, QTabWidget, QFrame, QScrollArea, QGroupBox,
                             QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
                             QSplitter, QSizePolicy, QDialog, QGridLayout, QListWidget,
                             QListWidgetItem, QSlider, QCheckBox, QSpacerItem, QStackedWidget)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QRect, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QPainter, QPainterPath, QMovie, QBrush
from PyQt5 import QtGui

# 自定义圆角按钮类
class RoundedButton(QPushButton):
    def __init__(self, text, parent=None, radius=10, bg_color="#4A6FA5", text_color="#FFFFFF"):
        super().__init__(text, parent)
        self.radius = radius
        self.bg_color = bg_color
        self.text_color = text_color
        self.setMinimumHeight(35)
        self.setCursor(Qt.PointingHandCursor)
        
        # 设置样式
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: {radius}px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color(bg_color, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self.adjust_color(bg_color, -20)};
            }}
            QPushButton:disabled {{
                background-color: #CCCCCC;
                color: #666666;
            }}
        """)
    
    def adjust_color(self, color, amount):
        # 简单的颜色调整函数
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        
        return f"#{r:02x}{g:02x}{b:02x}"

# 自定义半透明窗口类
class TransparentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        
        # 绘制半透明背景
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.drawRoundedRect(self.rect(), 15, 15)

# 自定义半透明文本框类
class TransparentTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTextEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                padding: 5px;
            }
        """)

# 自定义半透明组合框类
class TransparentComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox::down-arrow {
                image: none;
                border: 0px;
            }
        """)

# 自定义半透明进度条类
class TransparentProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                text-align: center;
                background-color: rgba(240, 240, 240, 150);
            }
            QProgressBar::chunk {
                background-color: #4A6FA5;
                border-radius: 5px;
            }
        """)

# 加载动画标签
class LoadingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.movie = QMovie()
        self.setAlignment(Qt.AlignCenter)
        
    def start_animation(self):
        # 创建一个简单的旋转动画
        self.movie = QMovie()
        # 使用CSS动画模拟加载
        self.setStyleSheet("""
            border: 4px solid #f3f3f3;
            border-radius: 50%;
            border-top: 4px solid #3498db;
            width: 30px;
            height: 30px;
            animation: spin 2s linear infinite;
        """)
    
    def stop_animation(self):
        self.setStyleSheet("")
        self.clear()

# 游戏下载模块
class GameDownloadWidget(QWidget):
    progress_signal = pyqtSignal(int, str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, minecraft_dir, mirrors, current_mirror):
        super().__init__()
        self.minecraft_dir = minecraft_dir
        self.mirrors = mirrors
        self.current_mirror = current_mirror
        self.download_thread = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 版本选择
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("选择版本:"))
        self.version_combobox = TransparentComboBox()
        version_layout.addWidget(self.version_combobox)
        layout.addLayout(version_layout)
        
        # 按钮框架
        btn_layout = QHBoxLayout()
        self.download_btn = RoundedButton("下载选中版本", bg_color="#388E3C")
        self.download_btn.clicked.connect(self.start_download_thread)
        btn_layout.addWidget(self.download_btn)
        
        refresh_btn = RoundedButton("刷新列表", bg_color="#5A7FB5")
        refresh_btn.clicked.connect(self.load_version_list)
        btn_layout.addWidget(refresh_btn)
        
        layout.addLayout(btn_layout)
        
        # 进度条
        self.progress = TransparentProgressBar()
        layout.addWidget(self.progress)
        
        # 进度标签
        self.progress_label = QLabel("就绪")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.progress_label)
    
    def load_version_list(self):
        """加载版本列表"""
        try:
            # 获取版本列表
            version_manifest_url = f"{self.mirrors[self.current_mirror]}/mc/game/version_manifest.json"
            response = requests.get(version_manifest_url)
            version_manifest = response.json()
            versions = [v['id'] for v in version_manifest['versions']]
            
            # 过滤旧版本 (只显示1.7.10及以上)
            filtered_versions = [v for v in versions if self.is_version_supported(v)]
            
            # 更新版本选择框
            self.version_combobox.clear()
            self.version_combobox.addItems(filtered_versions)
            
            if filtered_versions:
                # 默认选择1.12.2
                if "1.12.2" in filtered_versions:
                    self.version_combobox.setCurrentText("1.12.2")
                else:
                    self.version_combobox.setCurrentIndex(0)
                    
        except Exception as e:
            # 切换下载源
            self.current_mirror = (self.current_mirror + 1) % len(self.mirrors)
            self.log_signal.emit(f"错误: {str(e)}")
            self.load_version_list()
    
    def is_version_supported(self, version_str):
        """检查版本是否支持 (1.7.10及以上)"""
        try:
            parts = version_str.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            
            # 支持1.7.10及以上版本
            if major > 1:
                return True
            if major == 1 and minor > 7:
                return True
            if major == 1 and minor == 7 and patch >= 10:
                return True
            return False
        except:
            return False
    
    def start_download_thread(self):
        """启动下载线程"""
        selected_version = self.version_combobox.currentText()
        if not selected_version:
            self.log_signal.emit("请先选择一个版本！")
            return
        
        # 获取版本数据
        try:
            version_manifest_url = f"{self.mirrors[self.current_mirror]}/mc/game/version_manifest.json"
            response = requests.get(version_manifest_url)
            version_manifest = response.json()
            
            version_data = None
            for v in version_manifest['versions']:
                if v['id'] == selected_version:
                    version_data = v
                    break
            
            if not version_data:
                self.log_signal.emit(f"找不到版本数据: {selected_version}")
                return
        except Exception as e:
            self.log_signal.emit(f"获取版本数据失败: {str(e)}")
            return
        
        # 创建并启动下载线程
        self.download_thread = DownloadThread(
            version_data, self.minecraft_dir, "", "Player", "2048"
        )
        self.download_thread.progress_signal.connect(self.on_download_progress)
        self.download_thread.log_signal.connect(self.log_signal.emit)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        
        self.download_btn.setEnabled(False)
        self.download_thread.start()
    
    def on_download_progress(self, progress, message):
        """下载进度更新"""
        self.progress.setValue(progress)
        self.progress_label.setText(message)
    
    def on_download_finished(self, success, message):
        """下载完成"""
        if success:
            self.progress.setValue(100)
            self.progress_label.setText("下载完成")
            self.finished_signal.emit(True, message)
        else:
            self.progress_label.setText(f"下载失败: {message}")
            self.finished_signal.emit(False, message)
        
        self.download_btn.setEnabled(True)

# 工作线程类
class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, version_data, minecraft_dir, java_path, username, memory):
        super().__init__()
        self.version_data = version_data
        self.minecraft_dir = minecraft_dir
        self.java_path = java_path
        self.username = username
        self.memory = memory
        self.stop_requested = False
    
    def run(self):
        try:
            version_id = self.version_data['id']
            self.log_signal.emit(f"开始下载版本: {version_id}")
            
            # 创建版本目录
            version_dir = self.minecraft_dir / 'versions' / version_id
            os.makedirs(version_dir, exist_ok=True)
            
            # 下载版本JSON文件
            json_url = self.version_data['url']
            self.log_signal.emit(f"下载版本清单: {json_url}")
            self.progress_signal.emit(10, "下载版本清单")
            
            response = requests.get(json_url)
            version_json = response.json()
            
            # 保存版本JSON
            json_path = version_dir / f"{version_id}.json"
            with open(json_path, 'w') as f:
                json.dump(version_json, f, indent=2)
            
            # 下载客户端JAR文件
            client_jar_url = version_json['downloads']['client']['url']
            client_jar_path = version_dir / f"{version_id}.jar"
            
            self.log_signal.emit(f"下载客户端: {client_jar_url}")
            self.progress_signal.emit(30, "下载客户端")
            
            self.download_file(client_jar_url, client_jar_path)
            
            # 下载资源文件
            self.progress_signal.emit(50, "下载资源文件")
            assets_index_url = version_json['assetIndex']['url']
            assets_index_path = self.minecraft_dir / 'assets' / 'indexes' / f"{version_json['assetIndex']['id']}.json"
            
            os.makedirs(assets_index_path.parent, exist_ok=True)
            
            self.download_file(assets_index_url, assets_index_path)
            
            # 下载库文件
            self.progress_signal.emit(70, "下载库文件")
            libraries_dir = self.minecraft_dir / 'libraries'
            os.makedirs(libraries_dir, exist_ok=True)
            
            total_libs = len(version_json['libraries'])
            for i, lib in enumerate(version_json['libraries']):
                if self.stop_requested:
                    break
                    
                # 检查库规则（如操作系统限制）
                if 'rules' in lib:
                    allow = False
                    for rule in lib['rules']:
                        if rule['action'] == 'allow':
                            if 'os' in rule:
                                if rule['os']['name'] == platform.system().lower():
                                    allow = True
                                else:
                                    allow = False
                            else:
                                allow = True
                        elif rule['action'] == 'disallow':
                            if 'os' in rule and rule['os']['name'] == platform.system().lower():
                                allow = False
                    
                    if not allow:
                        continue
                
                # 下载库文件
                lib_path = None
                if 'downloads' in lib and 'artifact' in lib['downloads']:
                    lib_url = lib['downloads']['artifact']['url']
                    lib_path = libraries_dir / lib['downloads']['artifact']['path']
                elif 'url' in lib:
                    # 旧版本格式
                    base_url = lib['url']
                    lib_name = lib['name']
                    group_id, artifact_id, version = lib_name.split(':')
                    lib_path = libraries_dir / group_id.replace('.', '/') / artifact_id / version / f"{artifact_id}-{version}.jar"
                    lib_url = f"{base_url}{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
                
                if lib_path and lib_url:
                    os.makedirs(lib_path.parent, exist_ok=True)
                    if not lib_path.exists():
                        self.log_signal.emit(f"下载库: {lib_path.name}")
                        self.download_file(lib_url, lib_path)
                
                # 更新进度
                progress = 70 + int(30 * (i + 1) / total_libs)
                self.progress_signal.emit(progress, f"下载库文件 ({i+1}/{total_libs})")
            
            if not self.stop_requested:
                self.progress_signal.emit(100, "下载完成")
                self.log_signal.emit("版本下载完成")
                self.finished_signal.emit(True, "")
            else:
                self.finished_signal.emit(False, "下载被取消")
                
        except Exception as e:
            self.log_signal.emit(f"下载错误: {str(e)}")
            self.finished_signal.emit(False, str(e))
    
    def download_file(self, url, path):
        """下载文件并显示进度"""
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(path, 'wb') as f:
            downloaded = 0
            for data in response.iter_content(chunk_size=4096):
                if self.stop_requested:
                    raise Exception("下载被取消")
                
                downloaded += len(data)
                f.write(data)
                
                # 计算进度百分比
                if total_size > 0:
                    progress = int(downloaded / total_size * 100)
                    self.progress_signal.emit(progress, f"下载 {path.name}")

# 启动线程类
class LaunchThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, version_id, minecraft_dir, java_path, username, memory):
        super().__init__()
        self.version_id = version_id
        self.minecraft_dir = minecraft_dir
        self.java_path = java_path
        self.username = username
        self.memory = memory
    
    def run(self):
        try:
            # 读取版本JSON
            version_dir = self.minecraft_dir / 'versions' / self.version_id
            json_path = version_dir / f"{self.version_id}.json"
            
            with open(json_path, 'r') as f:
                version_data = json.load(f)
            
            # 构建Java命令
            cmd = [self.java_path]
            
            # 添加JVM参数
            if self.memory:
                cmd.extend([f"-Xmx{self.memory}M", f"-Xms{self.memory}M"])
            
            # 添加库路径
            libraries = []
            libraries_dir = self.minecraft_dir / 'libraries'
            
            for lib in version_data['libraries']:
                # 检查库规则
                if 'rules' in lib:
                    allow = False
                    for rule in lib['rules']:
                        if rule['action'] == 'allow':
                            if 'os' in rule:
                                if rule['os']['name'] == platform.system().lower():
                                    allow = True
                                else:
                                    allow = False
                            else:
                                allow = True
                        elif rule['action'] == 'disallow':
                            if 'os' in rule and rule['os']['name'] == platform.system().lower():
                                allow = False
                    
                    if not allow:
                        continue
                
                # 添加库路径
                if 'downloads' in lib and 'artifact' in lib['downloads']:
                    lib_path = libraries_dir / lib['downloads']['artifact']['path']
                elif 'name' in lib:
                    # 旧版本格式
                    group_id, artifact_id, version = lib['name'].split(':')
                    lib_path = libraries_dir / group_id.replace('.', '/') / artifact_id / version / f"{artifact_id}-{version}.jar"
                
                if lib_path.exists():
                    libraries.append(str(lib_path))
            
            # 添加客户端JAR
            client_jar = version_dir / f"{self.version_id}.jar"
            if not client_jar.exists():
                raise Exception(f"客户端JAR不存在: {client_jar}")
            
            # 构建类路径
            classpath = os.pathsep.join(libraries + [str(client_jar)])
            cmd.extend(["-cp", classpath])
            
            # 添加主类
            main_class = version_data['mainClass']
            cmd.append(main_class)
            
            # 添加游戏参数
            if 'arguments' in version_data and 'game' in version_data['arguments']:
                for arg in version_data['arguments']['game']:
                    if isinstance(arg, str):
                        # 替换占位符
                        arg = arg.replace("${auth_player_name}", self.username)
                        arg = arg.replace("${version_name}", self.version_id)
                        arg = arg.replace("${game_directory}", str(self.minecraft_dir))
                        arg = arg.replace("${assets_root}", str(self.minecraft_dir / 'assets'))
                        arg = arg.replace("${assets_index_name}", version_data['assetIndex']['id'])
                        arg = arg.replace("${auth_uuid}", str(uuid4()))
                        arg = arg.replace("${auth_access_token}", "token")
                        arg = arg.replace("${user_properties}", "{}")
                        arg = arg.replace("${user_type}", "mojang")
                        
                        cmd.append(arg)
            else:
                # 旧版本参数
                cmd.extend([
                    "--username", self.username,
                    "--version", self.version_id,
                    "--gameDir", str(self.minecraft_dir),
                    "--assetsDir", str(self.minecraft_dir / 'assets'),
                    "--assetIndex", version_data['assetIndex']['id'],
                    "--uuid", str(uuid4()),
                    "--accessToken", "token",
                    "--userProperties", "{}",
                    "--userType", "mojang"
                ])
            
            self.log_signal.emit(f"启动命令: {' '.join(cmd)}")
            
            # 启动游戏 - 隐藏命令提示符窗口
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.minecraft_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # 对于非Windows系统，使用常规方式启动
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.minecraft_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
            
            # 输出游戏日志
            for line in process.stdout:
                self.log_signal.emit(line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                self.finished_signal.emit(True, "游戏正常退出")
            else:
                self.finished_signal.emit(False, f"游戏异常退出，代码: {process.returncode}")
                
        except Exception as e:
            self.log_signal.emit(f"启动错误: {str(e)}")
            self.finished_signal.emit(False, str(e))

# 模组搜索线程
class ModSearchThread(QThread):
    finished_signal = pyqtSignal(list, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, api, query, version_filter=None, mod_type="mod"):
        super().__init__()
        self.api = api
        self.query = query
        self.version_filter = version_filter
        self.mod_type = mod_type
    
    def run(self):
        try:
            if self.api == "CurseForge":
                results = self.search_curseforge()
            else:  # Modrinth
                results = self.search_modrinth()
            
            self.finished_signal.emit(results, self.api)
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def search_curseforge(self):
        # CurseForge API需要密钥，这里使用模拟数据
        return [
            {
                "id": f"cf-{i}",
                "name": f"示例CurseForge模组 {i}",
                "description": "这是一个示例模组描述",
                "downloads": 1000 + i * 100,
                "versions": ["1.12.2", "1.16.5", "1.18.2"],
                "url": "https://www.curseforge.com",
                "icon_url": ""
            } for i in range(1, 6)
        ]
    
    def search_modrinth(self):
        try:
            # 构建查询参数
            facets = [["project_type:" + self.mod_type]]
            if self.version_filter:
                facets.append([f"versions:{self.version_filter}"])
            
            facets_json = json.dumps(facets)
            query = quote(self.query)
            
            url = f"https://api.modrinth.com/v2/search?query={query}&facets={facets_json}&limit=20"
            
            response = requests.get(url)
            data = response.json()
            
            results = []
            for hit in data.get("hits", []):
                project = hit
                results.append({
                    "id": project.get("project_id", ""),
                    "name": project.get("title", "未知"),
                    "description": project.get("description", "无描述"),
                    "downloads": project.get("downloads", 0),
                    "versions": project.get("versions", []),
                    "url": f"https://modrinth.com/{project.get('project_type', 'mod')}/{project.get('slug', '')}",
                    "icon_url": project.get("icon_url", "")
                })
            
            return results
        except Exception as e:
            self.error_signal.emit(f"Modrinth搜索错误: {str(e)}")
            return []

# 主窗口类
class MinecraftLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XHL Minecraft Launcher")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(900, 600)
        
        # 背景图片相关
        self.background_image = None
        self.background_opacity = 0.7
        
        # 配置文件
        self.config = configparser.ConfigParser()
        self.config_file = Path("launcher_config.ini")
        
        # 默认 Minecraft 目录
        self.minecraft_dir = Path(os.environ.get('APPDATA', Path.home())) / '.minecraft'
        self.versions_dir = self.minecraft_dir / 'versions'
        self.libraries_dir = self.minecraft_dir / 'libraries'
        self.assets_dir = self.minecraft_dir / 'assets'
        self.natives_dir = self.minecraft_dir / 'natives'
        self.mods_dir = self.minecraft_dir / 'mods'
        self.shaderpacks_dir = self.minecraft_dir / 'shaderpacks'
        
        # 确保必要的目录存在
        os.makedirs(self.mods_dir, exist_ok=True)
        os.makedirs(self.shaderpacks_dir, exist_ok=True)
        
        # 下载源列表
        self.mirrors = [
            "https://launchermeta.mojang.com",
            "https://bmclapi2.bangbang93.com"
        ]
        self.current_mirror = 0
        
        # 模组和光影API
        self.mod_apis = {
            "CurseForge": "https://api.curseforge.com",
            "Modrinth": "https://api.modrinth.com"
        }
        self.current_mod_api = "Modrinth"
        
        # 任务队列
        self.task_queue = Queue()
        
        # 当前下载线程
        self.download_thread = None
        self.launch_thread = None
        
        # 加载配置
        self.load_config()
        
        # 初始化UI
        self.init_ui()
        
        # 加载版本列表
        Thread(target=self.load_version_list, daemon=True).start()
    
    def load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            self.config.read(self.config_file)
            
            # 读取 Minecraft 目录
            if self.config.has_option('Settings', 'minecraft_dir'):
                custom_dir = self.config.get('Settings', 'minecraft_dir')
                if custom_dir and Path(custom_dir).exists():
                    self.minecraft_dir = Path(custom_dir)
            
            # 读取背景图片设置
            if self.config.has_option('Settings', 'background_image'):
                bg_path = self.config.get('Settings', 'background_image')
                if bg_path and Path(bg_path).exists():
                    self.background_image = bg_path
            
            if self.config.has_option('Settings', 'background_opacity'):
                self.background_opacity = self.config.getfloat('Settings', 'background_opacity')
            
            # 更新目录路径
            self.versions_dir = self.minecraft_dir / 'versions'
            self.libraries_dir = self.minecraft_dir / 'libraries'
            self.assets_dir = self.minecraft_dir / 'assets'
            self.natives_dir = self.minecraft_dir / 'natives'
            self.mods_dir = self.minecraft_dir / 'mods'
            self.shaderpacks_dir = self.minecraft_dir / 'shaderpacks'
    
    def save_config(self):
        """保存配置文件"""
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        
        self.config.set('Settings', 'minecraft_dir', str(self.minecraft_dir))
        
        if self.background_image:
            self.config.set('Settings', 'background_image', self.background_image)
        
        self.config.set('Settings', 'background_opacity', str(self.background_opacity))
        
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
    
    def init_ui(self):
        """初始化UI"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 设置主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("XHL Minecraft Launcher")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet("color: #333333;")
        title_bar_layout.addWidget(title_label)
        
        # 最小化和关闭按钮
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #CCCCCC;
                border-radius: 15px;
                color: #333333;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        minimize_btn.clicked.connect(self.showMinimized)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #CCCCCC;
                border-radius: 15px;
                color: #333333;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF5555;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(minimize_btn)
        title_bar_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 10px;
                background-color: rgba(255, 255, 255, 200);
            }
            QTabBar::tab {
                background-color: rgba(240, 240, 240, 200);
                border: 1px solid rgba(200, 200, 200, 100);
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: rgba(255, 255, 255, 255);
                border-bottom: 1px solid white;
            }
        """)
        
        # 创建游戏选项卡
        self.game_tab = self.create_game_tab()
        self.tab_widget.addTab(self.game_tab, "启动")
        
        # 创建模组选项卡
        self.mods_tab = self.create_mods_tab()
        self.tab_widget.addTab(self.mods_tab, "模组")
        
        # 创建光影选项卡
        self.shaders_tab = self.create_shaders_tab()
        self.tab_widget.addTab(self.shaders_tab, "光影")
        
        # 创建设置选项卡
        self.settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "设置")
        
        # 创建工具箱选项卡
        self.toolbox_tab = self.create_toolbox_tab()
        self.tab_widget.addTab(self.toolbox_tab, "工具箱")
        
        main_layout.addWidget(self.tab_widget)
        
        # 创建状态栏
        status_bar = QWidget()
        status_bar.setFixedHeight(30)
        status_bar_layout = QHBoxLayout(status_bar)
        status_bar_layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666666;")
        status_bar_layout.addWidget(self.status_label)
        
        # 加载动画
        self.loading_label = LoadingLabel()
        self.loading_label.setFixedSize(20, 20)
        status_bar_layout.addWidget(self.loading_label)
        
        version_label = QLabel("XHL Minecraft Launcher v2.0")
        version_label.setStyleSheet("color: #666666;")
        status_bar_layout.addWidget(version_label, alignment=Qt.AlignRight)
        
        main_layout.addWidget(status_bar)
        
        # 应用背景图片
        self.apply_background()
    
    def apply_background(self):
        """应用背景图片"""
        if self.background_image and Path(self.background_image).exists():
            palette = self.palette()
            pixmap = QPixmap(self.background_image)
            scaled_pixmap = pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            palette.setBrush(QPalette.Window, QBrush(scaled_pixmap))
            self.setPalette(palette)
            self.setAutoFillBackground(True)
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self.apply_background()
    
    def create_game_tab(self):
        """创建游戏选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 创建内容框架
        content_frame = TransparentWidget()
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        
        # 左侧面板 (设置)
        left_panel = QGroupBox("设置")
        left_panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        left_panel_layout = QGridLayout(left_panel)
        left_panel_layout.setVerticalSpacing(10)
        
        # Minecraft 目录选择
        left_panel_layout.addWidget(QLabel(".minecraft 目录:"), 0, 0)
        self.minecraft_dir_entry = QLineEdit(str(self.minecraft_dir))
        self.minecraft_dir_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        left_panel_layout.addWidget(self.minecraft_dir_entry, 0, 1)
        
        browse_btn = RoundedButton("浏览", radius=5, bg_color="#5A7FB5")
        browse_btn.clicked.connect(self.select_minecraft_dir)
        left_panel_layout.addWidget(browse_btn, 0, 2)
        
        # 用户名输入
        left_panel_layout.addWidget(QLabel("用户名:"), 1, 0)
        self.username_entry = QLineEdit("Player")
        self.username_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        left_panel_layout.addWidget(self.username_entry, 1, 1, 1, 2)
        
        # Java 路径
        left_panel_layout.addWidget(QLabel("Java 路径:"), 2, 0)
        self.java_path_entry = QLineEdit(self.find_java())
        self.java_path_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        left_panel_layout.addWidget(self.java_path_entry, 2, 1)
        
        find_java_btn = RoundedButton("自动查找", radius=5, bg_color="#5A7FB5")
        find_java_btn.clicked.connect(self.find_java_and_update)
        left_panel_layout.addWidget(find_java_btn, 2, 2)
        
        # 内存设置
        left_panel_layout.addWidget(QLabel("内存 (MB):"), 3, 0)
        self.memory_entry = QLineEdit("2048")
        self.memory_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        left_panel_layout.addWidget(self.memory_entry, 3, 1, 1, 2)
        
        content_layout.addWidget(left_panel)
        
        # 右侧面板 (游戏)
        right_panel = QGroupBox("游戏")
        right_panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setSpacing(10)
        
        # 已安装版本列表
        installed_versions_layout = QHBoxLayout()
        installed_versions_layout.addWidget(QLabel("已安装版本:"))
        self.installed_versions_combo = TransparentComboBox()
        installed_versions_layout.addWidget(self.installed_versions_combo)
        right_panel_layout.addLayout(installed_versions_layout)
        
        # 刷新版本列表按钮
        refresh_btn = RoundedButton("刷新版本列表", bg_color="#5A7FB5")
        refresh_btn.clicked.connect(self.refresh_installed_versions)
        right_panel_layout.addWidget(refresh_btn)
        
        # 启动按钮
        self.launch_btn = RoundedButton("启动游戏", bg_color="#388E3C")
        self.launch_btn.clicked.connect(self.start_launch_thread)
        self.launch_btn.setEnabled(False)
        right_panel_layout.addWidget(self.launch_btn)
        
        content_layout.addWidget(right_panel)
        
        layout.addWidget(content_frame)
        
        # 游戏下载模块
        download_frame = QGroupBox("游戏下载")
        download_frame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        download_layout = QVBoxLayout(download_frame)
        
        # 创建游戏下载模块
        self.game_download_widget = GameDownloadWidget(self.minecraft_dir, self.mirrors, self.current_mirror)
        self.game_download_widget.log_signal.connect(self.log_to_console)
        self.game_download_widget.finished_signal.connect(self.on_download_finished)
        download_layout.addWidget(self.game_download_widget)
        
        layout.addWidget(download_frame)
        
        # 控制台输出
        console_frame = QGroupBox("控制台输出")
        console_frame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        console_layout = QVBoxLayout(console_frame)
        
        self.console_text = TransparentTextEdit()
        self.console_text.setReadOnly(True)
        console_layout.addWidget(self.console_text)
        
        layout.addWidget(console_frame)
        
        # 初始加载已安装版本
        self.refresh_installed_versions()
        
        return tab
    
    def create_mods_tab(self):
        """创建模组选项卡 - 仿PCL2设计"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 搜索和过滤框架
        search_frame = TransparentWidget()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(15, 10, 15, 10)
        
        # 搜索框
        search_layout.addWidget(QLabel("搜索:"))
        self.mod_search_entry = QLineEdit()
        self.mod_search_entry.setPlaceholderText("输入模组名称")
        self.mod_search_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        search_layout.addWidget(self.mod_search_entry)
        
        # 版本过滤器
        search_layout.addWidget(QLabel("游戏版本:"))
        self.mod_version_filter = TransparentComboBox()
        self.mod_version_filter.addItem("所有版本")
        search_layout.addWidget(self.mod_version_filter)
        
        # 分类过滤器
        search_layout.addWidget(QLabel("分类:"))
        self.mod_category_filter = TransparentComboBox()
        self.mod_category_filter.addItems(["所有分类", "技术", "魔法", "冒险", "装饰", "辅助", "库"])
        search_layout.addWidget(self.mod_category_filter)
        
        # 搜索按钮
        search_btn = RoundedButton("搜索", radius=5, bg_color="#5A7FB5")
        search_btn.clicked.connect(self.search_mods)
        search_layout.addWidget(search_btn)
        
        layout.addWidget(search_frame)
        
        # API选择框架
        api_frame = TransparentWidget()
        api_layout = QHBoxLayout(api_frame)
        api_layout.setContentsMargins(15, 10, 15, 10)
        
        api_layout.addWidget(QLabel("模组平台:"))
        self.mod_api_combo = TransparentComboBox()
        self.mod_api_combo.addItems(["CurseForge", "Modrinth"])
        self.mod_api_combo.setCurrentText(self.current_mod_api)
        self.mod_api_combo.currentTextChanged.connect(self.change_mod_api)
        api_layout.addWidget(self.mod_api_combo)
        
        layout.addWidget(api_frame)
        
        # 模组列表和详情框架
        mods_content_frame = QSplitter(Qt.Horizontal)
        mods_content_frame.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(200, 200, 200, 100);
            }
        """)
        
        # 模组列表
        mods_list_frame = QGroupBox("模组列表")
        mods_list_frame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        mods_list_layout = QVBoxLayout(mods_list_frame)
        
        self.mods_tree = QTreeWidget()
        self.mods_tree.setHeaderLabels(["模组名称", "版本", "下载量"])
        self.mods_tree.setStyleSheet("""
            QTreeWidget {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.mods_tree.itemSelectionChanged.connect(self.on_mod_select)
        mods_list_layout.addWidget(self.mods_tree)
        
        mods_content_frame.addWidget(mods_list_frame)
        
        # 模组详情
        mod_details_frame = QGroupBox("模组详情")
        mod_details_frame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        mod_details_layout = QVBoxLayout(mod_details_frame)
        
        # 模组版本选择
        mod_version_layout = QHBoxLayout()
        mod_version_layout.addWidget(QLabel("选择版本:"))
        self.mod_version_combo = TransparentComboBox()
        mod_version_layout.addWidget(self.mod_version_combo)
        
        # 加载器选择
        mod_version_layout.addWidget(QLabel("加载器:"))
        self.mod_loader_combo = TransparentComboBox()
        self.mod_loader_combo.addItems(["Forge", "Fabric", "Quilt", "所有"])
        mod_version_layout.addWidget(self.mod_loader_combo)
        mod_details_layout.addLayout(mod_version_layout)
        
        self.mod_details_text = TransparentTextEdit()
        self.mod_details_text.setReadOnly(True)
        mod_details_layout.addWidget(self.mod_details_text)
        
        mods_content_frame.addWidget(mod_details_frame)
        
        # 设置初始大小比例
        mods_content_frame.setSizes([400, 600])
        
        layout.addWidget(mods_content_frame)
        
        # 按钮框架
        btn_frame = TransparentWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(15, 10, 15, 10)
        
        self.download_mod_btn = RoundedButton("下载选中模组", bg_color="#388E3C")
        self.download_mod_btn.clicked.connect(self.download_selected_mod)
        self.download_mod_btn.setEnabled(False)
        btn_layout.addWidget(self.download_mod_btn)
        
        open_folder_btn = RoundedButton("打开模组文件夹", bg_color="#5A7FB5")
        open_folder_btn.clicked.connect(self.open_mods_folder)
        btn_layout.addWidget(open_folder_btn)
        
        refresh_btn = RoundedButton("刷新列表", bg_color="#5A7FB5")
        refresh_btn.clicked.connect(self.search_mods)
        btn_layout.addWidget(refresh_btn)
        
        layout.addWidget(btn_frame)
        
        return tab
    
    def create_shaders_tab(self):
        """创建光影选项卡 - 仿PCL2设计"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 搜索和过滤框架
        search_frame = TransparentWidget()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(15, 10, 15, 10)
        
        # 搜索框
        search_layout.addWidget(QLabel("搜索:"))
        self.shader_search_entry = QLineEdit()
        self.shader_search_entry.setPlaceholderText("输入光影名称")
        self.shader_search_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        search_layout.addWidget(self.shader_search_entry)
        
        # 版本过滤器
        search_layout.addWidget(QLabel("游戏版本:"))
        self.shader_version_filter = TransparentComboBox()
        self.shader_version_filter.addItem("所有版本")
        search_layout.addWidget(self.shader_version_filter)
        
        # 搜索按钮
        search_btn = RoundedButton("搜索", radius=5, bg_color="#5A7FB5")
        search_btn.clicked.connect(self.search_shaders)
        search_layout.addWidget(search_btn)
        
        layout.addWidget(search_frame)
        
        # 光影列表
        shaders_list_frame = QGroupBox("光影列表")
        shaders_list_frame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        shaders_list_layout = QVBoxLayout(shaders_list_frame)
        
        self.shaders_tree = QTreeWidget()
        self.shaders_tree.setHeaderLabels(["光影名称", "版本", "下载量"])
        self.shaders_tree.setStyleSheet("""
            QTreeWidget {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.shaders_tree.itemDoubleClicked.connect(self.on_shader_double_click)
        shaders_list_layout.addWidget(self.shaders_tree)
        
        layout.addWidget(shaders_list_frame)
        
        # 光影详情
        shader_details_frame = QGroupBox("光影详情")
        shader_details_frame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        shader_details_layout = QVBoxLayout(shader_details_frame)
        
        # 光影版本选择
        shader_version_layout = QHBoxLayout()
        shader_version_layout.addWidget(QLabel("选择版本:"))
        self.shader_version_combo = TransparentComboBox()
        shader_version_layout.addWidget(self.shader_version_combo)
        shader_details_layout.addLayout(shader_version_layout)
        
        self.shader_details_text = TransparentTextEdit()
        self.shader_details_text.setReadOnly(True)
        shader_details_layout.addWidget(self.shader_details_text)
        
        layout.addWidget(shader_details_frame)
        
        # 按钮框架
        btn_frame = TransparentWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(15, 10, 15, 10)
        
        self.download_shader_btn = RoundedButton("下载选中光影", bg_color="#388E3C")
        self.download_shader_btn.clicked.connect(self.download_selected_shader)
        self.download_shader_btn.setEnabled(False)
        btn_layout.addWidget(self.download_shader_btn)
        
        open_folder_btn = RoundedButton("打开光影文件夹", bg_color="#5A7FB5")
        open_folder_btn.clicked.connect(self.open_shaders_folder)
        btn_layout.addWidget(open_folder_btn)
        
        refresh_btn = RoundedButton("刷新列表", bg_color="#5A7FB5")
        refresh_btn.clicked.connect(self.search_shaders)
        btn_layout.addWidget(refresh_btn)
        
        layout.addWidget(btn_frame)
        
        return tab
    
    def create_settings_tab(self):
        """创建设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Minecraft目录设置
        mc_dir_frame = TransparentWidget()
        mc_dir_layout = QHBoxLayout(mc_dir_frame)
        mc_dir_layout.setContentsMargins(15, 10, 15, 10)
        
        mc_dir_layout.addWidget(QLabel(".minecraft 目录:"))
        self.settings_mc_dir_entry = QLineEdit(str(self.minecraft_dir))
        self.settings_mc_dir_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        mc_dir_layout.addWidget(self.settings_mc_dir_entry)
        
        browse_btn = RoundedButton("浏览", radius=5, bg_color="#5A7FB5")
        browse_btn.clicked.connect(self.select_minecraft_dir_from_settings)
        mc_dir_layout.addWidget(browse_btn)
        
        layout.addWidget(mc_dir_frame)
        
        # 背景图片设置
        bg_frame = TransparentWidget()
        bg_layout = QHBoxLayout(bg_frame)
        bg_layout.setContentsMargins(15, 10, 15, 10)
        
        bg_layout.addWidget(QLabel("背景图片:"))
        self.bg_path_entry = QLineEdit(self.background_image or "")
        self.bg_path_entry.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 150);
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        bg_layout.addWidget(self.bg_path_entry)
        
        bg_browse_btn = RoundedButton("浏览", radius=5, bg_color="#5A7FB5")
        bg_browse_btn.clicked.connect(self.select_background_image)
        bg_layout.addWidget(bg_browse_btn)
        
        layout.addWidget(bg_frame)
        
        # 背景透明度设置
        opacity_frame = TransparentWidget()
        opacity_layout = QHBoxLayout(opacity_frame)
        opacity_layout.setContentsMargins(15, 10, 15, 10)
        
        opacity_layout.addWidget(QLabel("背景透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self.background_opacity * 100))
        self.opacity_slider.valueChanged.connect(self.change_background_opacity)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel(f"{int(self.background_opacity * 100)}%")
        opacity_layout.addWidget(self.opacity_label)
        
        layout.addWidget(opacity_frame)
        
        # 下载源选择
        mirror_frame = TransparentWidget()
        mirror_layout = QHBoxLayout(mirror_frame)
        mirror_layout.setContentsMargins(15, 10, 15, 10)
        
        mirror_layout.addWidget(QLabel("下载源:"))
        self.mirror_combo = TransparentComboBox()
        self.mirror_combo.addItems(self.mirrors)
        self.mirror_combo.setCurrentText(self.mirrors[self.current_mirror])
        mirror_layout.addWidget(self.mirror_combo)
        
        layout.addWidget(mirror_frame)
        
        # 模组API选择
        mod_api_frame = TransparentWidget()
        mod_api_layout = QHBoxLayout(mod_api_frame)
        mod_api_layout.setContentsMargins(15, 10, 15, 10)
        
        mod_api_layout.addWidget(QLabel("模组API:"))
        self.settings_mod_api_combo = TransparentComboBox()
        self.settings_mod_api_combo.addItems(["CurseForge", "Modrinth"])
        self.settings_mod_api_combo.setCurrentText(self.current_mod_api)
        mod_api_layout.addWidget(self.settings_mod_api_combo)
        
        layout.addWidget(mod_api_frame)
        
        # 应用按钮
        apply_btn = RoundedButton("应用设置", bg_color="#388E3C")
        apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(apply_btn, alignment=Qt.AlignCenter)
        
        # 添加弹性空间
        layout.addStretch()
        
        return tab
    
    def create_toolbox_tab(self):
        """创建工具箱选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 内存优化组
        memory_group = QGroupBox("内存优化")
        memory_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        memory_layout = QVBoxLayout(memory_group)
        
        # 内存清理按钮
        memory_clean_btn = RoundedButton("清理内存", bg_color="#5A7FB5")
        memory_clean_btn.clicked.connect(self.clean_memory)
        memory_layout.addWidget(memory_clean_btn)
        
        # 内存优化说明
        memory_info = QLabel("清理未使用的内存资源，提高启动器性能")
        memory_info.setStyleSheet("color: #666666; font-size: 12px;")
        memory_info.setWordWrap(True)
        memory_layout.addWidget(memory_info)
        
        layout.addWidget(memory_group)
        
        # 游戏修复组
        repair_group = QGroupBox("游戏修复")
        repair_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        repair_layout = QVBoxLayout(repair_group)
        
        # 修复游戏文件按钮
        repair_files_btn = RoundedButton("修复游戏文件", bg_color="#5A7FB5")
        repair_files_btn.clicked.connect(self.repair_game_files)
        repair_layout.addWidget(repair_files_btn)
        
        # 修复说明
        repair_info = QLabel("检查并修复损坏的游戏文件")
        repair_info.setStyleSheet("color: #666666; font-size: 12px;")
        repair_info.setWordWrap(True)
        repair_layout.addWidget(repair_info)
        
        layout.addWidget(repair_group)
        
        # 其他工具组
        tools_group = QGroupBox("其他工具")
        tools_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 100);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        tools_layout = QVBoxLayout(tools_group)
        
        # 打开游戏目录按钮
        open_dir_btn = RoundedButton("打开游戏目录", bg_color="#5A7FB5")
        open_dir_btn.clicked.connect(lambda: self.open_directory(self.minecraft_dir))
        tools_layout.addWidget(open_dir_btn)
        
        # 打开模组目录按钮
        open_mods_btn = RoundedButton("打开模组目录", bg_color="#5A7FB5")
        open_mods_btn.clicked.connect(self.open_mods_folder)
        tools_layout.addWidget(open_mods_btn)
        
        # 打开光影目录按钮
        open_shaders_btn = RoundedButton("打开光影目录", bg_color="#5A7FB5")
        open_shaders_btn.clicked.connect(self.open_shaders_folder)
        tools_layout.addWidget(open_shaders_btn)
        
        layout.addWidget(tools_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        return tab
    
    def clean_memory(self):
        """清理内存"""
        try:
            # 清理Python垃圾
            import gc
            gc.collect()
            
            # 清理Qt缓存
            QApplication.processEvents()
            
            QMessageBox.information(self, "成功", "内存清理完成")
            self.log_to_console("内存清理完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"内存清理失败: {str(e)}")
            self.log_to_console(f"内存清理错误: {str(e)}")
    
    def repair_game_files(self):
        """修复游戏文件"""
        try:
            # 这里实现游戏文件修复逻辑
            # 检查并重新下载损坏的文件
            
            self.log_to_console("开始检查游戏文件完整性...")
            
            # 模拟修复过程
            for version_dir in self.versions_dir.iterdir():
                if version_dir.is_dir():
                    json_file = version_dir / f"{version_dir.name}.json"
                    jar_file = version_dir / f"{version_dir.name}.jar"
                    
                    if json_file.exists() and not jar_file.exists():
                        self.log_to_console(f"发现损坏版本: {version_dir.name}，需要重新下载")
            
            QMessageBox.information(self, "完成", "游戏文件检查完成")
            self.log_to_console("游戏文件检查完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"修复游戏文件失败: {str(e)}")
            self.log_to_console(f"修复游戏文件错误: {str(e)}")
    
    def open_directory(self, directory):
        """打开目录"""
        try:
            if platform.system() == "Windows":
                os.startfile(directory)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", str(directory)])
            else:  # Linux
                subprocess.call(["xdg-open", str(directory)])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开目录: {str(e)}")
    
    def refresh_installed_versions(self):
        """刷新已安装版本列表"""
        self.installed_versions_combo.clear()
        
        if not self.versions_dir.exists():
            return
        
        for version_dir in self.versions_dir.iterdir():
            if version_dir.is_dir():
                jar_file = version_dir / f"{version_dir.name}.jar"
                if jar_file.exists():
                    self.installed_versions_combo.addItem(version_dir.name)
        
        # 如果有已安装版本，启用启动按钮
        if self.installed_versions_combo.count() > 0:
            self.launch_btn.setEnabled(True)
    
    def find_java(self, version=None):
        """查找 Java 安装路径，根据版本号选择"""
        # 根据版本确定需要的Java版本
        java_version = 8  # 默认Java 8
        
        if version:
            try:
                parts = version.split('.')
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0
                
                # Minecraft版本与Java版本对应关系
                if major == 1:
                    if minor >= 17:  # 1.17+ 需要Java 16+
                        java_version = 16
                    elif minor >= 12:  # 1.12-1.16 需要Java 8+
                        java_version = 8
                    elif minor >= 7:  # 1.7-1.11 需要Java 8
                        java_version = 8
            except:
                pass
        
        # 检查 JAVA_HOME 环境变量
        java_home = os.environ.get('JAVA_HOME')
        if java_home:
            java_path = Path(java_home) / 'bin' / 'java'
            if java_path.exists():
                # 检查Java版本
                try:
                    result = subprocess.run([str(java_path), '-version'], 
                                          capture_output=True, text=True, timeout=5)
                    version_output = result.stderr
                    if f'version "{java_version}' in version_output or f'version "1.{java_version}' in version_output:
                        return str(java_path)
                except:
                    pass
        
        # 检查常见安装路径
        common_paths = []
        if platform.system() == "Windows":
            # 搜索不同版本的Java
            java_versions = [
                f"jdk-{java_version}", f"jre-{java_version}",
                f"jdk1.{java_version}.0", f"jre1.{java_version}.0"
            ]
            
            program_files = [os.environ.get('ProgramFiles', 'C:\\Program Files')]
            if os.environ.get('ProgramFiles(x86)'):
                program_files.append(os.environ.get('ProgramFiles(x86)'))
            
            for pf in program_files:
                for jv in java_versions:
                    common_paths.append(Path(pf) / "Java" / jv / "bin" / "java.exe")
        else:  # Linux/macOS
            common_paths = [
                Path("/usr/bin/java"),
                Path("/usr/local/bin/java"),
                Path("/opt/java/bin/java")
            ]
        
        for path in common_paths:
            if path.exists():
                # 检查Java版本
                try:
                    result = subprocess.run([str(path), '-version'], 
                                          capture_output=True, text=True, timeout=5)
                    version_output = result.stderr
                    if f'version "{java_version}' in version_output or f'version "1.{java_version}' in version_output:
                        return str(path)
                except:
                    continue
        
        # 最后尝试使用系统路径中的 java
        return "java"
    
    def find_java_and_update(self):
        """查找并更新 Java 路径"""
        selected_version = self.installed_versions_combo.currentText()
        java_path = self.find_java(selected_version)
        self.java_path_entry.setText(java_path)
    
    def select_minecraft_dir(self):
        """选择 .minecraft 目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择 .minecraft 目录")
        if directory:
            self.minecraft_dir = Path(directory)
            self.minecraft_dir_entry.setText(str(self.minecraft_dir))
            self.versions_dir = self.minecraft_dir / 'versions'
            self.libraries_dir = self.minecraft_dir / 'libraries'
            self.assets_dir = self.minecraft_dir / 'assets'
            self.natives_dir = self.minecraft_dir / 'natives'
            self.mods_dir = self.minecraft_dir / 'mods'
            self.shaderpacks_dir = self.minecraft_dir / 'shaderpacks'
            self.save_config()
            self.refresh_installed_versions()
            # 更新下载模块的目录
            self.game_download_widget.minecraft_dir = self.minecraft_dir
    
    def select_minecraft_dir_from_settings(self):
        """从设置中选择 .minecraft 目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择 .minecraft 目录")
        if directory:
            self.minecraft_dir = Path(directory)
            self.settings_mc_dir_entry.setText(str(self.minecraft_dir))
            self.minecraft_dir_entry.setText(str(self.minecraft_dir))
            self.versions_dir = self.minecraft_dir / 'versions'
            self.libraries_dir = self.minecraft_dir / 'libraries'
            self.assets_dir = self.minecraft_dir / 'assets'
            self.natives_dir = self.minecraft_dir / 'natives'
            self.mods_dir = self.minecraft_dir / 'mods'
            self.shaderpacks_dir = self.minecraft_dir / 'shaderpacks'
            self.save_config()
            self.refresh_installed_versions()
            # 更新下载模块的目录
            self.game_download_widget.minecraft_dir = self.minecraft_dir
    
    def select_background_image(self):
        """选择背景图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.background_image = file_path
            self.bg_path_entry.setText(file_path)
            self.apply_background()
            self.save_config()
    
    def change_background_opacity(self, value):
        """改变背景透明度"""
        self.background_opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")
        self.apply_background()
        self.save_config()
    
    def load_version_list(self):
        """加载版本列表"""
        try:
            self.update_status("正在加载版本列表...")
            
            # 获取版本列表
            version_manifest_url = f"{self.mirrors[self.current_mirror]}/mc/game/version_manifest.json"
            response = requests.get(version_manifest_url)
            version_manifest = response.json()
            versions = [v['id'] for v in version_manifest['versions']]
            
            # 过滤旧版本 (只显示1.7.10及以上)
            filtered_versions = [v for v in versions if self.is_version_supported(v)]
            
            # 更新模组和光影版本过滤器
            self.mod_version_filter.clear()
            self.mod_version_filter.addItem("所有版本")
            self.mod_version_filter.addItems(filtered_versions)
            
            self.shader_version_filter.clear()
            self.shader_version_filter.addItem("所有版本")
            self.shader_version_filter.addItems(filtered_versions)
            
            self.update_status("版本列表加载完成")
        except Exception as e:
            # 切换下载源
            self.current_mirror = (self.current_mirror + 1) % len(self.mirrors)
            self.update_status(f"加载失败: {str(e)}，尝试切换下载源")
            self.log_to_console(f"错误: {str(e)}")
            self.load_version_list()
    
    def is_version_supported(self, version_str):
        """检查版本是否支持 (1.7.10及以上)"""
        try:
            parts = version_str.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            
            # 支持1.7.10及以上版本
            if major > 1:
                return True
            if major == 1 and minor > 7:
                return True
            if major == 1 and minor == 7 and patch >= 10:
                return True
            return False
        except:
            return False
    
    def start_launch_thread(self):
        """启动游戏线程"""
        selected_version = self.installed_versions_combo.currentText()
        if not selected_version:
            QMessageBox.critical(self, "错误", "请先选择一个版本！")
            return
        
        # 检查版本是否已下载
        version_dir = self.minecraft_dir / 'versions' / selected_version
        jar_path = version_dir / f"{selected_version}.jar"
        
        if not jar_path.exists():
            QMessageBox.critical(self, "错误", f"版本 {selected_version} 尚未下载，请先下载！")
            return
        
        # 获取用户设置
        java_path = self.java_path_entry.text()
        username = self.username_entry.text()
        memory = self.memory_entry.text()
        
        # 创建并启动启动线程
        self.launch_thread = LaunchThread(
            selected_version, self.minecraft_dir, java_path, username, memory
        )
        self.launch_thread.log_signal.connect(self.log_to_console)
        self.launch_thread.finished_signal.connect(self.on_launch_finished)
        
        # 开始加载动画
        self.loading_label.start_animation()
        
        # 禁用按钮
        self.launch_btn.setEnabled(False)
        
        self.launch_thread.start()
    
    def on_launch_finished(self, success, message):
        """启动完成"""
        # 停止加载动画
        self.loading_label.stop_animation()
        
        if success:
            self.update_status("游戏已退出")
            QMessageBox.information(self, "信息", "游戏已退出")
        else:
            self.update_status(f"启动失败: {message}")
            QMessageBox.critical(self, "错误", f"启动失败: {message}")
        
        # 启用按钮
        self.launch_btn.setEnabled(True)
    
    def on_download_finished(self, success, message):
        """下载完成"""
        if success:
            self.update_status("下载完成")
            QMessageBox.information(self, "成功", "版本下载完成")
            # 刷新已安装版本列表
            self.refresh_installed_versions()
        else:
            self.update_status(f"下载失败: {message}")
            QMessageBox.critical(self, "错误", f"下载失败: {message}")
    
    def search_mods(self):
        """搜索模组"""
        search_term = self.mod_search_entry.text()
        if not search_term:
            QMessageBox.warning(self, "警告", "请输入搜索关键词")
            return
        
        # 获取版本过滤器
        version_filter = None
        if self.mod_version_filter.currentText() != "所有版本":
            version_filter = self.mod_version_filter.currentText()
        
        # 清空现有列表
        self.mods_tree.clear()
        
        # 更新状态
        self.update_status(f"正在搜索模组: {search_term}")
        
        # 开始加载动画
        self.loading_label.start_animation()
        
        # 创建并启动搜索线程
        self.mod_search_thread = ModSearchThread(
            self.current_mod_api, search_term, version_filter, "mod"
        )
        self.mod_search_thread.finished_signal.connect(self.on_mod_search_finished)
        self.mod_search_thread.error_signal.connect(self.on_mod_search_error)
        self.mod_search_thread.start()
    
    def search_shaders(self):
        """搜索光影"""
        search_term = self.shader_search_entry.text()
        if not search_term:
            QMessageBox.warning(self, "警告", "请输入搜索关键词")
            return
        
        # 获取版本过滤器
        version_filter = None
        if self.shader_version_filter.currentText() != "所有版本":
            version_filter = self.shader_version_filter.currentText()
        
        # 清空现有列表
        self.shaders_tree.clear()
        
        # 更新状态
        self.update_status(f"正在搜索光影: {search_term}")
        
        # 开始加载动画
        self.loading_label.start_animation()
        
        # 创建并启动搜索线程
        self.shader_search_thread = ModSearchThread(
            "Modrinth", search_term, version_filter, "shader"
        )
        self.shader_search_thread.finished_signal.connect(self.on_shader_search_finished)
        self.shader_search_thread.error_signal.connect(self.on_shader_search_error)
        self.shader_search_thread.start()
    
    def on_mod_search_finished(self, results, api):
        """模组搜索完成"""
        # 停止加载动画
        self.loading_label.stop_animation()
        
        # 清空现有列表
        self.mods_tree.clear()
        
        # 添加结果到列表
        for mod in results:
            item = QTreeWidgetItem(self.mods_tree)
            item.setText(0, mod["name"])
            item.setText(1, ", ".join(mod["versions"][:3]) if mod["versions"] else "未知")
            item.setText(2, str(mod["downloads"]))
            # 存储完整数据
            item.setData(0, Qt.UserRole, mod)
        
        self.update_status(f"找到 {len(results)} 个模组")
    
    def on_mod_search_error(self, error):
        """模组搜索错误"""
        # 停止加载动画
        self.loading_label.stop_animation()
        
        QMessageBox.critical(self, "错误", f"搜索模组时出错: {error}")
        self.update_status("搜索失败")
    
    def on_shader_search_finished(self, results, api):
        """光影搜索完成"""
        # 停止加载动画
        self.loading_label.stop_animation()
        
        # 清空现有列表
        self.shaders_tree.clear()
        
        # 添加结果到列表
        for shader in results:
            item = QTreeWidgetItem(self.shaders_tree)
            item.setText(0, shader["name"])
            item.setText(1, ", ".join(shader["versions"][:3]) if shader["versions"] else "未知")
            item.setText(2, str(shader["downloads"]))
            # 存储完整数据
            item.setData(0, Qt.UserRole, shader)
        
        self.update_status(f"找到 {len(results)} 个光影")
    
    def on_shader_search_error(self, error):
        """光影搜索错误"""
        # 停止加载动画
        self.loading_label.stop_animation()
        
        QMessageBox.critical(self, "错误", f"搜索光影时出错: {error}")
        self.update_status("搜索失败")
    
    def on_mod_select(self):
        """模组列表选择事件"""
        selected_items = self.mods_tree.selectedItems()
        if not selected_items:
            self.download_mod_btn.setEnabled(False)
            return
        
        item = selected_items[0]
        mod_data = item.data(0, Qt.UserRole)
        
        # 更新版本选择框
        self.mod_version_combo.clear()
        if mod_data["versions"]:
            self.mod_version_combo.addItems(mod_data["versions"])
        else:
            self.mod_version_combo.addItem("未知")
        
        # 显示模组详情
        self.mod_details_text.clear()
        self.mod_details_text.append(f"名称: {mod_data['name']}")
        self.mod_details_text.append(f"下载量: {mod_data['downloads']}")
        self.mod_details_text.append(f"支持版本: {', '.join(mod_data['versions'])}")
        self.mod_details_text.append("")
        self.mod_details_text.append(f"描述: {mod_data['description']}")
        
        # 启用下载按钮
        self.download_mod_btn.setEnabled(True)
    
    def on_shader_double_click(self, item, column):
        """光影列表双击事件"""
        shader_data = item.data(0, Qt.UserRole)
        
        # 更新版本选择框
        self.shader_version_combo.clear()
        if shader_data["versions"]:
            self.shader_version_combo.addItems(shader_data["versions"])
        else:
            self.shader_version_combo.addItem("未知")
        
        # 显示光影详情
        self.shader_details_text.clear()
        self.shader_details_text.append(f"名称: {shader_data['name']}")
        self.shader_details_text.append(f"下载量: {shader_data['downloads']}")
        self.shader_details_text.append(f"支持版本: {', '.join(shader_data['versions'])}")
        self.shader_details_text.append("")
        self.shader_details_text.append(f"描述: {shader_data['description']}")
        
        # 启用下载按钮
        self.download_shader_btn.setEnabled(True)
    
    def download_selected_mod(self):
        """下载选中的模组"""
        selected_items = self.mods_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个模组")
            return
        
        item = selected_items[0]
        mod_data = item.data(0, Qt.UserRole)
        selected_version = self.mod_version_combo.currentText()
        selected_loader = self.mod_loader_combo.currentText()
        
        if selected_version == "未知":
            QMessageBox.warning(self, "警告", "无法确定模组版本")
            return
        
        # 开始下载
        self.update_status(f"开始下载模组: {mod_data['name']}")
        self.log_to_console(f"开始下载模组: {mod_data['name']} ({selected_version}, {selected_loader})")
        
        # 这里实现模组下载逻辑
        # 注意: 实际实现需要根据API和版本下载正确的文件
        
        QMessageBox.information(self, "信息", f"模组 {mod_data['name']} 下载功能尚未完全实现")
    
    def download_selected_shader(self):
        """下载选中的光影"""
        selected_items = self.shaders_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个光影")
            return
        
        item = selected_items[0]
        shader_data = item.data(0, Qt.UserRole)
        selected_version = self.shader_version_combo.currentText()
        
        if selected_version == "未知":
            QMessageBox.warning(self, "警告", "无法确定光影版本")
            return
        
        # 开始下载
        self.update_status(f"开始下载光影: {shader_data['name']}")
        self.log_to_console(f"开始下载光影: {shader_data['name']} ({selected_version})")
        
        # 这里实现光影下载逻辑
        # 注意: 实际实现需要根据API和版本下载正确的文件
        
        QMessageBox.information(self, "信息", f"光影 {shader_data['name']} 下载功能尚未完全实现")
    
    def open_mods_folder(self):
        """打开模组文件夹"""
        try:
            if platform.system() == "Windows":
                os.startfile(self.mods_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", str(self.mods_dir)])
            else:  # Linux
                subprocess.call(["xdg-open", str(self.mods_dir)])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开模组文件夹: {str(e)}")
    
    def open_shaders_folder(self):
        """打开光影文件夹"""
        try:
            if platform.system() == "Windows":
                os.startfile(self.shaderpacks_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", str(self.shaderpacks_dir)])
            else:  # Linux
                subprocess.call(["xdg-open", str(self.shaderpacks_dir)])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开光影文件夹: {str(e)}")
    
    def change_mod_api(self, api):
        """更改模组API"""
        self.current_mod_api = api
    
    def apply_settings(self):
        """应用设置"""
        # 应用下载源设置
        new_mirror = self.mirror_combo.currentText()
        if new_mirror in self.mirrors:
            self.current_mirror = self.mirrors.index(new_mirror)
            self.game_download_widget.current_mirror = self.current_mirror
        
        # 应用模组API设置
        new_mod_api = self.settings_mod_api_combo.currentText()
        if new_mod_api != self.current_mod_api:
            self.current_mod_api = new_mod_api
            self.mod_api_combo.setCurrentText(new_mod_api)
        
        # 保存设置
        self.save_config()
        
        QMessageBox.information(self, "成功", "设置已应用")
    
    def update_status(self, message):
        """更新状态标签"""
        self.status_label.setText(message)
    
    def log_to_console(self, message):
        """将消息记录到控制台"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_text.append(f"[{timestamp}] {message}")
        # 滚动到底部
        self.console_text.verticalScrollBar().setValue(
            self.console_text.verticalScrollBar().maximum()
        )

# 主函数
def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    launcher = MinecraftLauncher()
    launcher.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()