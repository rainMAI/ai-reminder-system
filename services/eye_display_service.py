"""
眼睛显示控制服务
通过串口与 ESP32 眼睛设备通信
"""
import serial
import threading
import logging
import time
from typing import Optional, Callable

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EyeDisplayService:
    """眼睛显示控制服务类"""

    def __init__(self, port: str = 'COM3', baudrate: int = 115200):
        """
        初始化眼睛显示服务

        Args:
            port: 串口号 (Windows: COM3, Linux: /dev/ttyUSB0)
            baudrate: 波特率，默认115200
        """
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.is_connected = False
        self.is_connecting = False

        # 触摸事件回调
        self.on_touch_1: Optional[Callable] = None
        self.on_touch_2: Optional[Callable] = None

        # 接收线程
        self._receive_thread: Optional[threading.Thread] = None
        self._running = False

        # 重连配置
        self._auto_reconnect = True
        self._reconnect_interval = 5  # 秒

        logger.info(f"眼睛显示服务已创建: {port}@{baudrate}")

    def connect(self, retry_count: int = 3) -> bool:
        """
        连接到 ESP32 设备

        Args:
            retry_count: 重试次数

        Returns:
            bool: 连接是否成功
        """
        if self.is_connecting:
            logger.warning("正在连接中，请勿重复调用")
            return False

        self.is_connecting = True

        for attempt in range(retry_count):
            try:
                logger.info(f"尝试连接到 {self.port} (第 {attempt + 1}/{retry_count} 次)...")

                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=1,
                    write_timeout=1
                )

                # 清空缓冲区
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()

                self.is_connected = True
                self.is_connecting = False
                logger.info(f"✅ 已成功连接到眼睛设备: {self.port}")

                # 发送初始化命令
                time.sleep(0.1)
                self.set_expression("neutral")
                return True

            except serial.SerialException as e:
                logger.warning(f"连接失败 (第 {attempt + 1} 次): {e}")
                if attempt < retry_count - 1:
                    time.sleep(1)

        self.is_connecting = False
        logger.error(f"❌ 连接失败，已重试 {retry_count} 次")
        return False

    def disconnect(self):
        """断开连接"""
        self._running = False
        self._auto_reconnect = False

        if self._receive_thread:
            self._receive_thread.join(timeout=2)
            self._receive_thread = None

        if self.serial:
            try:
                self.serial.close()
            except:
                pass
            self.serial = None

        self.is_connected = False
        logger.info("已断开眼睛设备连接")

    def start(self) -> bool:
        """
        启动服务

        Returns:
            bool: 启动是否成功
        """
        if not self.connect():
            return False

        self._running = True
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True, name="EyeReceiveThread")
        self._receive_thread.start()

        logger.info("眼睛显示服务已启动")
        return True

    def stop(self):
        """停止服务"""
        self.disconnect()
        logger.info("眼睛显示服务已停止")

    def set_expression(self, emotion: str) -> bool:
        """
        设置表情

        Args:
            emotion: 表情名称 (happy, sad, angry, surprised, neutral, thinking, listening)

        Returns:
            bool: 是否发送成功
        """
        valid_emotions = ["happy", "sad", "angry", "surprised", "neutral", "thinking", "listening"]
        if emotion not in valid_emotions:
            logger.warning(f"无效的表情: {emotion}，有效值: {valid_emotions}")
            return False

        return self._send_command(f"EYE:{emotion}")

    def play_animation(self, animation: str) -> bool:
        """
        播放动画

        Args:
            animation: 动画名称 (blink, talk, listen, think, idle)

        Returns:
            bool: 是否发送成功
        """
        return self._send_command(f"ANIM:{animation}")

    def show_text(self, text: str, duration: int = 3) -> bool:
        """
        显示文字

        Args:
            text: 文字内容
            duration: 显示时长（秒）

        Returns:
            bool: 是否发送成功
        """
        # 限制文字长度
        if len(text) > 20:
            text = text[:20] + "..."
            logger.warning(f"文字过长，已截断: {text}")

        return self._send_command(f"TXT:{text}|{duration}")

    def set_brightness(self, brightness: int) -> bool:
        """
        设置屏幕亮度

        Args:
            brightness: 亮度值 (0-100)

        Returns:
            bool: 是否发送成功
        """
        if not 0 <= brightness <= 100:
            logger.warning(f"亮度值无效: {brightness}，范围应为 0-100")
            return False

        return self._send_command(f"BRIGHT:{brightness}")

    def get_status(self) -> dict:
        """
        获取状态

        Returns:
            dict: 状态信息
        """
        return {
            "connected": self.is_connected,
            "port": self.port,
            "baudrate": self.baudrate,
            "auto_reconnect": self._auto_reconnect
        }

    def _send_command(self, command: str) -> bool:
        """
        发送命令到 ESP32

        Args:
            command: 命令字符串

        Returns:
            bool: 是否发送成功
        """
        if not self.is_connected or not self.serial:
            logger.error("设备未连接")
            # 尝试自动重连
            if self._auto_reconnect:
                logger.info("尝试自动重连...")
                if self.connect(retry_count=1):
                    return self._send_command(command)
            return False

        try:
            cmd_bytes = f"{command}\n".encode('utf-8')
            self.serial.write(cmd_bytes)
            self.serial.flush()
            logger.debug(f"发送命令: {command}")
            return True
        except serial.SerialException as e:
            logger.error(f"发送命令失败: {e}")
            self.is_connected = False
            # 尝试自动重连
            if self._auto_reconnect:
                threading.Thread(target=self._reconnect_loop, daemon=True).start()
            return False
        except Exception as e:
            logger.error(f"发送命令异常: {e}")
            return False

    def _reconnect_loop(self):
        """重连循环"""
        time.sleep(self._reconnect_interval)
        if self._auto_reconnect and not self.is_connected:
            logger.info("尝试重新连接...")
            self.connect(retry_count=3)
            if self.is_connected and self._running:
                # 重新启动接收线程
                self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                self._receive_thread.start()

    def _receive_loop(self):
        """接收 ESP32 消息的循环"""
        buffer = ""
        last_activity = time.time()

        while self._running and self.is_connected:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    last_activity = time.time()

                    # 处理完整的消息行
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            self._handle_message(line)

                # 检测连接超时
                if time.time() - last_activity > 30:
                    # 发送心跳
                    self._send_command("PING")
                    last_activity = time.time()

                time.sleep(0.01)  # 降低CPU占用

            except serial.SerialException as e:
                logger.error(f"接收消息错误: {e}")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"接收循环异常: {e}")
                time.sleep(0.1)

    def _handle_message(self, message: str):
        """
        处理来自 ESP32 的消息

        Args:
            message: 消息内容
        """
        logger.info(f"收到设备消息: {message}")

        # 处理触摸事件
        if message == "TOUCH:1":
            logger.info("👆 触摸传感器1被触发")
            if self.on_touch_1:
                try:
                    self.on_touch_1()
                except Exception as e:
                    logger.error(f"触摸传感器1回调错误: {e}")

        elif message == "TOUCH:2":
            logger.info("👆 触摸传感器2被触发")
            if self.on_touch_2:
                try:
                    self.on_touch_2()
                except Exception as e:
                    logger.error(f"触摸传感器2回调错误: {e}")

        elif message.startswith("ERROR:"):
            error_msg = message[6:]
            logger.error(f"设备错误: {error_msg}")

        elif message == "PONG":
            logger.debug("心跳响应")

        else:
            logger.debug(f"未处理的消息: {message}")

    # 表情快捷方法
    def happy(self) -> bool:
        """设置开心表情"""
        return self.set_expression("happy")

    def sad(self) -> bool:
        """设置伤心表情"""
        return self.set_expression("sad")

    def angry(self) -> bool:
        """设置生气表情"""
        return self.set_expression("angry")

    def surprised(self) -> bool:
        """设置惊讶表情"""
        return self.set_expression("surprised")

    def neutral(self) -> bool:
        """设置中性表情"""
        return self.set_expression("neutral")

    def thinking(self) -> bool:
        """设置思考表情"""
        return self.set_expression("thinking")

    def listening(self) -> bool:
        """设置聆听表情"""
        return self.set_expression("listening")

    def blink(self) -> bool:
        """眨眼动画"""
        return self.play_animation("blink")

    def talk(self) -> bool:
        """说话动画"""
        return self.play_animation("talk")

    def idle(self) -> bool:
        """空闲动画"""
        return self.play_animation("idle")


# 全局服务实例
_eye_service_instance: Optional[EyeDisplayService] = None


def get_eye_service() -> Optional[EyeDisplayService]:
    """获取全局眼睛服务实例"""
    return _eye_service_instance


def init_eye_service(port: str = 'COM3', baudrate: int = 115200, auto_start: bool = True) -> Optional[EyeDisplayService]:
    """
    初始化全局眼睛服务

    Args:
        port: 串口号
        baudrate: 波特率
        auto_start: 是否自动启动服务

    Returns:
        EyeDisplayService: 服务实例
    """
    global _eye_service_instance

    if _eye_service_instance is not None:
        logger.warning("眼睛服务已经初始化，返回现有实例")
        return _eye_service_instance

    _eye_service_instance = EyeDisplayService(port, baudrate)

    if auto_start:
        if not _eye_service_instance.start():
            logger.error("眼睛服务启动失败")
            return None

    return _eye_service_instance


def stop_eye_service():
    """停止全局眼睛服务"""
    global _eye_service_instance

    if _eye_service_instance:
        _eye_service_instance.stop()
        _eye_service_instance = None
