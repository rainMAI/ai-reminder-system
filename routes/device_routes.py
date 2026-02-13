"""
Device Management API Routes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import re

from database.connection import get_db

device_bp = Blueprint('devices', __name__, url_prefix='/api/devices')


def validate_mac_address(mac: str) -> bool:
    """
    Validate MAC address format
    Accepted formats:
    - aa:bb:cc:dd:ee:ff
    - AA:BB:CC:DD:EE:FF
    - aabb.ccdd.eeff
    """
    patterns = [
        r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        r'^([0-9A-Fa-f]{4}\.){2}([0-9A-Fa-f]{4})$'
    ]
    return any(re.match(pattern, mac) for pattern in patterns)


def normalize_mac_address(mac: str) -> str:
    """Normalize MAC address to lowercase aa:bb:cc:dd:ee:ff format"""
    # Remove any separators
    mac_clean = re.sub(r'[:.-]', '', mac)
    # Convert to lowercase and add colons
    return ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)]).lower()


@device_bp.route('/register', methods=['POST'])
def register_device():
    """
    Register a new ESP32 device (used by ESP32)
    Headers:
        Device-Id: MAC address

    Request Body:
        {
            "device_name": "Living Room Device",
            "firmware_version": "2.6.2"
        }
    """
    try:
        # Get MAC address from header
        mac_address = request.headers.get('Device-Id')
        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'Missing Device-Id header'
            }), 400

        # Validate MAC address
        if not validate_mac_address(mac_address):
            return jsonify({
                'success': False,
                'error': 'Invalid MAC address format'
            }), 400

        mac_address = normalize_mac_address(mac_address)

        # Get request data
        data = request.get_json() or {}
        device_name = data.get('device_name', f'Device {mac_address[-8:]}')
        firmware_version = data.get('firmware_version', 'unknown')

        db = get_db()

        # Check if device already exists
        existing = db.execute(
            "SELECT id FROM devices WHERE mac_address = ?",
            (mac_address,),
            fetch_one=True
        )

        now = datetime.now().isoformat()

        if existing:
            # Update existing device
            db.execute(
                """UPDATE devices
                   SET device_name = ?, firmware_version = ?,
                       last_online_at = ?, is_online = 1
                   WHERE mac_address = ?""",
                (device_name, firmware_version, now, mac_address)
            )
            device_id = existing[0]
            action = 'updated'
        else:
            # Register new device
            db.execute(
                """INSERT INTO devices (mac_address, device_name, firmware_version, last_online_at, is_online)
                   VALUES (?, ?, ?, ?, 1)""",
                (mac_address, device_name, firmware_version, now)
            )
            device_id = db.execute("SELECT last_insert_rowid()", fetch_one=True)[0]
            action = 'registered'

        return jsonify({
            'success': True,
            'device_id': device_id,
            'mac_address': mac_address,
            'action': action,
            'registered_at': now
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/manual', methods=['POST'])
def add_device_manual():
    """
    Manually add a device (used by Web UI)
    Request Body:
        {
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "device_name": "Living Room Device"
        }
    Headers:
        Authorization: Bearer <token> (required)
    """
    try:
        # 验证用户身份
        from services.auth_service import AuthService
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({
                'success': False,
                'error': 'Missing authorization token'
            }), 401

        auth_service = AuthService()
        result = auth_service.verify_token(token)

        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Invalid token')
            }), 401

        user_id = result['user']['id']

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400

        mac_address = data.get('mac_address')
        device_name = data.get('device_name')

        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'mac_address is required'
            }), 400

        if not device_name:
            return jsonify({
                'success': False,
                'error': 'device_name is required'
            }), 400

        # Validate MAC address
        if not validate_mac_address(mac_address):
            return jsonify({
                'success': False,
                'error': 'Invalid MAC address format. Use format: aa:bb:cc:dd:ee:ff'
            }), 400

        mac_address = normalize_mac_address(mac_address)
        db = get_db()

        # Check if device already exists
        existing = db.execute(
            "SELECT id, owner_id FROM devices WHERE mac_address = ?",
            (mac_address,),
            fetch_one=True
        )

        if existing:
            device_id, existing_owner_id = existing
            # 如果设备存在但没有所有者，更新所有者
            if existing_owner_id is None:
                db.execute(
                    "UPDATE devices SET owner_id = ?, device_name = ? WHERE id = ?",
                    (user_id, device_name, device_id)
                )
                return jsonify({
                    'success': True,
                    'device_id': device_id,
                    'mac_address': mac_address,
                    'device_name': device_name,
                    'action': 'claimed'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': f'Device with MAC address {mac_address} already exists'
                }), 409

        # Create new device with owner
        now = datetime.now().isoformat()
        db.execute(
            """INSERT INTO devices (mac_address, device_name, firmware_version, is_online, owner_id, created_at)
               VALUES (?, ?, 'unknown', 0, ?, ?)""",
            (mac_address, device_name, user_id, now)
        )
        device_id = db.execute("SELECT last_insert_rowid()", fetch_one=True)[0]

        return jsonify({
            'success': True,
            'device_id': device_id,
            'mac_address': mac_address,
            'device_name': device_name,
            'created_at': now
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/', methods=['GET'])
def list_devices():
    """
    List devices owned by current user
    Query Params:
        status: 'online' | 'offline' | 'all' (default: 'all')

    Headers:
        Authorization: Bearer <token> (required)
    """
    try:
        from datetime import timedelta
        from services.auth_service import AuthService

        # 验证用户身份
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({
                'success': False,
                'error': 'Missing authorization token'
            }), 401

        auth_service = AuthService()
        result = auth_service.verify_token(token)

        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Invalid token')
            }), 401

        user_id = result['user']['id']
        db = get_db()
        status_filter = request.args.get('status', 'all')

        # 只查询当前用户拥有的设备
        query = """
            SELECT id, mac_address, device_name, firmware_version,
                   is_online, last_online_at, last_sync_at, created_at
            FROM devices
            WHERE owner_id = ?
        """
        params = [user_id]

        if status_filter == 'online':
            query += " AND is_online = 1"
        elif status_filter == 'offline':
            query += " AND is_online = 0"

        query += " ORDER BY last_online_at DESC"

        rows = db.execute(query, tuple(params), fetch_all=True)

        # Timeout threshold: device is offline if no sync for 3 minutes
        offline_threshold = datetime.now() - timedelta(minutes=3)

        devices = []
        for row in rows:
            # Get reminder count for this device
            count_row = db.execute(
                "SELECT COUNT(*) FROM reminders WHERE device_id = ? AND status = 'active'",
                (row[0],),
                fetch_one=True
            )
            reminder_count = count_row[0] if count_row else 0

            # Check if device should be marked as offline due to timeout
            is_online = bool(row[4])
            last_online_at = row[5]

            if is_online and last_online_at:
                try:
                    last_online_time = datetime.fromisoformat(last_online_at)
                    # If last online time is older than threshold, mark as offline
                    if last_online_time < offline_threshold:
                        is_online = False
                        # Update database to reflect offline status
                        db.execute(
                            "UPDATE devices SET is_online = 0 WHERE id = ?",
                            (row[0],)
                        )
                except:
                    pass

            devices.append({
                'id': row[0],
                'mac_address': row[1],
                'device_name': row[2],
                'firmware_version': row[3],
                'is_online': is_online,
                'last_online_at': row[5],
                'last_sync_at': row[6],
                'created_at': row[7],
                'reminder_count': reminder_count
            })

        return jsonify({
            'success': True,
            'devices': devices,
            'total_count': len(devices)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/<int:device_id>', methods=['GET'])
def get_device(device_id: int):
    """Get device details"""
    try:
        db = get_db()

        # Get device info
        device_row = db.execute(
            """SELECT id, mac_address, device_name, firmware_version,
                      is_online, last_online_at, last_sync_at, created_at
               FROM devices WHERE id = ?""",
            (device_id,),
            fetch_one=True
        )

        if not device_row:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404

        device = {
            'id': device_row[0],
            'mac_address': device_row[1],
            'device_name': device_row[2],
            'firmware_version': device_row[3],
            'is_online': bool(device_row[4]),
            'last_online_at': device_row[5],
            'last_sync_at': device_row[6],
            'created_at': device_row[7]
        }

        # Get active reminders
        reminder_rows = db.execute(
            """SELECT id, content, reminder_type, scheduled_timestamp, scheduled_time, created_at
               FROM reminders
               WHERE device_id = ? AND status = 'active'
               ORDER BY scheduled_timestamp ASC, created_at ASC""",
            (device_id,),
            fetch_all=True
        )

        device['active_reminders'] = []
        for row in reminder_rows:
            device['active_reminders'].append({
                'id': row[0],
                'content': row[1],
                'reminder_type': row[2],
                'scheduled_timestamp': row[3],
                'scheduled_time': row[4],
                'created_at': row[5]
            })

        return jsonify({
            'success': True,
            'device': device
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/<int:device_id>', methods=['PUT'])
def update_device(device_id: int):
    """
    Update device information
    Request Body:
        {
            "device_name": "New Name"
        }
    """
    try:
        data = request.get_json() or {}
        device_name = data.get('device_name')

        if not device_name:
            return jsonify({
                'success': False,
                'error': 'device_name is required'
            }), 400

        db = get_db()

        # Check if device exists
        existing = db.execute(
            "SELECT id FROM devices WHERE id = ?",
            (device_id,),
            fetch_one=True
        )

        if not existing:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404

        # Update device
        db.execute(
            "UPDATE devices SET device_name = ? WHERE id = ?",
            (device_name, device_id)
        )

        return jsonify({
            'success': True,
            'device_id': device_id,
            'updated_at': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/<int:device_id>', methods=['DELETE'])
def delete_device(device_id: int):
    """Delete a device (cascades to reminders)"""
    try:
        db = get_db()

        # Check if device exists
        existing = db.execute(
            "SELECT id FROM devices WHERE id = ?",
            (device_id,),
            fetch_one=True
        )

        if not existing:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404

        # Delete device (reminders will be cascade deleted)
        db.execute("DELETE FROM devices WHERE id = ?", (device_id,))

        return jsonify({
            'success': True,
            'message': 'Device deleted successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@device_bp.route('/heartbeat', methods=['POST'])
def device_heartbeat():
    """
    Update device online status and last online time
    Headers:
        Device-Id: MAC address
    """
    try:
        mac_address = request.headers.get('Device-Id')
        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'Missing Device-Id header'
            }), 400

        mac_address = normalize_mac_address(mac_address)
        db = get_db()
        now = datetime.now().isoformat()

        # Update device status
        db.execute(
            """UPDATE devices
               SET last_online_at = ?, is_online = 1
               WHERE mac_address = ?""",
            (now, mac_address)
        )

        return jsonify({
            'success': True,
            'timestamp': now
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_device_routes(app):
    """Register device routes with Flask app"""
    app.register_blueprint(device_bp)
    print("[OK] Device management routes registered")
    print("     Endpoints:")
    print("       POST   /api/devices/register  (ESP32 auto-register)")
    print("       POST   /api/devices/manual    (Manual add)")
    print("       GET    /api/devices")
    print("       GET    /api/devices/<id>")
    print("       PUT    /api/devices/<id>")
    print("       DELETE /api/devices/<id>")
    print("       POST   /api/devices/heartbeat")
