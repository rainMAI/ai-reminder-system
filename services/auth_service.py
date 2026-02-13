"""
Auth Service - 用户认证和授权服务
"""
import os
import sys
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db


class AuthService:
    """用户认证服务"""

    def __init__(self):
        # Session有效期：30天
        self.session_expiry_days = 30

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str, email: str = None,
                 full_name: str = None, devices: List[Dict] = None) -> Dict:
        """
        用户注册

        Args:
            username: 用户名
            password: 密码
            email: 邮箱
            full_name: 姓名
            devices: 设备列表 [{"device_name": "...", "mac_address": "..."}]

        Returns:
            {"success": bool, "user_id": int, "error": str}
        """
        try:
            db = get_db()

            # 检查用户名是否已存在
            existing = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
                fetch_one=True
            )

            if existing:
                return {'success': False, 'error': '用户名已存在'}

            # 创建用户
            password_hash = self.hash_password(password)
            now = datetime.now().isoformat()

            user_id = db.execute(
                """INSERT INTO users (username, password_hash, email, full_name, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (username, password_hash, email, full_name, now, now)
            )

            # 关联设备
            if devices:
                for device_data in devices:
                    self._link_device(user_id, device_data)

            return {
                'success': True,
                'user_id': user_id,
                'username': username
            }

        except Exception as e:
            print(f"[AuthService] Error in register: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def login(self, username: str, password: str) -> Dict:
        """
        用户登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            {"success": bool, "token": str, "user": dict, "error": str}
        """
        try:
            db = get_db()

            # 查找用户
            user = db.execute(
                "SELECT id, username, password_hash, email, full_name FROM users WHERE username = ?",
                (username,),
                fetch_one=True
            )

            if not user:
                return {'success': False, 'error': '用户名或密码错误'}

            user_id, username, password_hash, email, full_name = user

            # 验证密码
            if password_hash != self.hash_password(password):
                return {'success': False, 'error': '用户名或密码错误'}

            # 生成session token
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(days=self.session_expiry_days)).isoformat()

            # 保存session
            db.execute(
                """INSERT INTO user_sessions (user_id, session_token, expires_at, created_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, token, expires_at, datetime.now().isoformat())
            )

            # 获取用户设备
            user_devices = self.get_user_devices(user_id)

            return {
                'success': True,
                'token': token,
                'user': {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name,
                    'devices': user_devices
                }
            }

        except Exception as e:
            print(f"[AuthService] Error in login: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def verify_token(self, token: str) -> Dict:
        """
        验证session token

        Args:
            token: session token

        Returns:
            {"success": bool, "user": dict, "error": str}
        """
        try:
            db = get_db()

            # 查找session
            session = db.execute(
                """SELECT us.user_id, us.expires_at, u.username, u.email, u.full_name
                   FROM user_sessions us
                   JOIN users u ON us.user_id = u.id
                   WHERE us.session_token = ?""",
                (token,),
                fetch_one=True
            )

            if not session:
                return {'success': False, 'error': 'Invalid token'}

            user_id, expires_at, username, email, full_name = session

            # 检查是否过期
            if datetime.now() > datetime.fromisoformat(expires_at):
                # 删除过期session
                db.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))
                return {'success': False, 'error': 'Token expired'}

            # 获取用户设备
            user_devices = self.get_user_devices(user_id)

            return {
                'success': True,
                'user': {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name,
                    'devices': user_devices
                }
            }

        except Exception as e:
            print(f"[AuthService] Error in verify_token: {e}")
            return {'success': False, 'error': str(e)}

    def logout(self, token: str) -> Dict:
        """
        用户登出

        Args:
            token: session token

        Returns:
            {"success": bool}
        """
        try:
            db = get_db()
            db.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))
            return {'success': True}
        except Exception as e:
            print(f"[AuthService] Error in logout: {e}")
            return {'success': False, 'error': str(e)}

    def _link_device(self, user_id: int, device_data: Dict) -> bool:
        """
        关联设备到用户

        Args:
            user_id: 用户ID
            device_data: 设备数据 {"device_name": str, "mac_address": str}

        Returns:
            是否成功
        """
        try:
            db = get_db()
            mac_address = device_data['mac_address'].lower()

            # 查找或创建设备
            device = db.execute(
                "SELECT id FROM devices WHERE mac_address = ?",
                (mac_address,),
                fetch_one=True
            )

            if device:
                device_id = device[0]
            else:
                # 创建新设备
                device_id = db.execute(
                    """INSERT INTO devices (mac_address, device_name, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (mac_address, device_data.get('device_name', 'Unknown'),
                     datetime.now().isoformat(), datetime.now().isoformat())
                )

            # 关联用户和设备
            try:
                db.execute(
                    """INSERT INTO user_devices (user_id, device_id, device_name, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, device_id, device_data.get('device_name', 'Unknown'),
                     datetime.now().isoformat())
                )
            except Exception:
                # 可能已存在，忽略
                pass

            return True

        except Exception as e:
            print(f"[AuthService] Error in _link_device: {e}")
            return False

    def get_user_devices(self, user_id: int) -> List[Dict]:
        """获取用户拥有的所有设备（根据 owner_id）"""
        try:
            db = get_db()

            # 只查询 owner_id 等于当前用户的设备
            rows = db.execute(
                """SELECT d.id, d.mac_address, d.device_name, d.owner_id
                   FROM devices d
                   WHERE d.owner_id = ?""",
                (user_id,),
                fetch_all=True
            )

            return [
                {
                    'id': row[0],
                    'mac_address': row[1],
                    'device_name': row[2]
                }
                for row in rows
            ]

        except Exception as e:
            print(f"[AuthService] Error in get_user_devices: {e}")
            return []
