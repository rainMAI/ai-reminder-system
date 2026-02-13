"""
Auth Routes - 用户认证API路由
"""
from flask import Blueprint, request, jsonify, send_file
from services.auth_service import AuthService
from functools import wraps

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()


def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        result = auth_service.verify_token(token)

        if not result['success']:
            return jsonify({'success': False, 'error': result.get('error', 'Invalid token')}), 401

        # 将用户信息添加到request
        request.user = result['user']
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """
    用户注册

    Request Body:
        {
            "username": "string",
            "password": "string",
            "email": "string" (optional),
            "full_name": "string" (optional),
            "devices": [
                {"device_name": "string", "mac_address": "string"}
            ]
        }

    Response:
        {"success": bool, "user_id": int, "error": str}
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        full_name = data.get('full_name')
        devices = data.get('devices', [])

        # 验证必填字段
        if not username or not password:
            return jsonify({'success': False, 'error': 'Missing username or password'}), 400

        # 验证用户名长度
        if len(username) < 3 or len(username) > 50:
            return jsonify({'success': False, 'error': 'Username must be 3-50 characters'}), 400

        # 验证密码长度
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        result = auth_service.register(username, password, email, full_name, devices)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        print(f"[AuthRoutes] Error in register: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录

    Request Body:
        {
            "username": "string",
            "password": "string"
        }

    Response:
        {
            "success": bool,
            "token": "string",
            "user": {...}
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'error': 'Missing username or password'}), 400

        result = auth_service.login(username, password)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401

    except Exception as e:
        print(f"[AuthRoutes] Error in login: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify():
    """
    验证token

    Headers:
        Authorization: Bearer <token>

    Response:
        {"success": bool, "user": {...}}
    """
    return jsonify({
        'success': True,
        'user': request.user
    })


@auth_bp.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """
    用户登出

    Headers:
        Authorization: Bearer <token>

    Response:
        {"success": bool}
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        result = auth_service.logout(token)
        return jsonify(result)
    except Exception as e:
        print(f"[AuthRoutes] Error in logout: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/user', methods=['GET'])
@require_auth
def get_user():
    """
    获取当前用户信息

    Headers:
        Authorization: Bearer <token>

    Response:
        {"success": bool, "user": {...}}
    """
    return jsonify({
        'success': True,
        'user': request.user
    })


@auth_bp.route('/api/auth/devices', methods=['GET'])
@require_auth
def get_user_devices():
    """
    获取用户的设备列表

    Headers:
        Authorization: Bearer <token>

    Response:
        {"success": bool, "devices": [...]}
    """
    return jsonify({
        'success': True,
        'devices': request.user.get('devices', [])
    })


def register_auth_routes(app):
    """注册认证路由"""
    app.register_blueprint(auth_bp)
    print("[OK] Auth routes registered:")
    print("     - POST /api/auth/register")
    print("     - POST /api/auth/login")
    print("     - GET  /api/auth/verify")
    print("     - POST /api/auth/logout")
    print("     - GET  /api/auth/user")
    print("     - GET  /api/auth/devices")
