"""
ESP32 Device Synchronization API Routes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import time

from database.connection import get_db

sync_bp = Blueprint('sync', __name__, url_prefix='/api/sync')


def normalize_mac_address(mac: str) -> str:
    """Normalize MAC address"""
    import re
    mac_clean = re.sub(r'[:.-]', '', mac)
    return ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)]).lower()


def get_device_by_mac(mac_address: str):
    """Get device info by MAC address"""
    db = get_db()
    row = db.execute(
        "SELECT id, device_name FROM devices WHERE mac_address = ?",
        (mac_address,),
        fetch_one=True
    )
    return row


@sync_bp.route('/pull', methods=['GET'])
def sync_pull():
    """
    ESP32 pulls reminders from server
    Headers:
        Device-Id: MAC address

    Response:
        {
            "success": true,
            "server_time": 1736331600,
            "reminders": [
                {
                    "id": 456,
                    "remote_id": "1736331234_12345",
                    "content": "Meeting at 3pm",
                    "timestamp": 1736346000,
                    "created_at": 1736331234
                }
            ]
        }
    """
    try:
        # Get device MAC from header
        mac_address = request.headers.get('Device-Id')
        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'Missing Device-Id header'
            }), 400

        mac_address = normalize_mac_address(mac_address)

        # Get device
        device = get_device_by_mac(mac_address)
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not registered'
            }), 404

        device_id, device_name = device[0], device[1]

        # Update device last sync time and online status
        now = datetime.now().isoformat()
        db = get_db()
        db.execute(
            "UPDATE devices SET last_sync_at = ?, last_online_at = ?, is_online = 1 WHERE id = ?",
            (now, now, device_id)
        )

        # Get all active reminders for this device
        rows = db.execute(
            """SELECT id, remote_id, content, reminder_type,
                      scheduled_timestamp, scheduled_time, created_at
               FROM reminders
               WHERE device_id = ? AND status = 'active'
               ORDER BY scheduled_timestamp ASC, created_at ASC""",
            (device_id,),
            fetch_all=True
        )

        current_time = int(time.time())
        reminders = []
        expired_reminder_ids = []

        for row in rows:
            reminder_id = row[0]
            reminder_type = row[3]
            scheduled_timestamp = row[4]
            scheduled_time = row[5]

            # Convert scheduled_time (HH:MM) to timestamp if it's a recurring reminder
            timestamp = scheduled_timestamp  # for one-time
            if reminder_type == 'daily' and scheduled_time:
                # For daily reminders, calculate next occurrence
                # TODO: Use scheduler to calculate precise next timestamp
                # For now, return the time string and let ESP32 handle scheduling
                timestamp = int(time.time()) + 3600  # Default: 1 hour from now
            elif reminder_type == 'once' and scheduled_timestamp:
                # For one-time reminders, check if expired
                if scheduled_timestamp < current_time:
                    # Mark as completed and don't send to ESP32
                    expired_reminder_ids.append(reminder_id)
                    continue  # Skip this reminder

            reminders.append({
                'id': row[0],
                'remote_id': row[1],  # ESP32-side ID for tracking
                'content': row[2],
                'timestamp': timestamp,
                'scheduled_time': row[5],  # For recurring reminders
                'created_at': int(datetime.fromisoformat(row[6]).timestamp())
            })

        # Mark expired one-time reminders as completed
        if expired_reminder_ids:
            for rid in expired_reminder_ids:
                db.execute(
                    "UPDATE reminders SET status = 'completed', completed_at = ? WHERE id = ?",
                    (now, rid)
                )
            print(f"[SyncPull] Marked {len(expired_reminder_ids)} expired reminder(s) as completed")

        return jsonify({
            'success': True,
            'server_time': int(time.time()),
            'reminders': reminders,
            'device_settings': {
                'timezone': '+08:00',
                'sync_interval': 300  # 5 minutes
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/push', methods=['POST'])
def sync_push():
    """
    ESP32 pushes local reminders to server
    Headers:
        Device-Id: MAC address

    Request Body:
        {
            "reminders": [
                {
                    "remote_id": "1736331234_12345",
                    "content": "Buy groceries",
                    "timestamp": 1736350000,
                    "created_at": 1736331234
                }
            ]
        }
    """
    try:
        # Get device MAC from header
        mac_address = request.headers.get('Device-Id')
        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'Missing Device-Id header'
            }), 400

        mac_address = normalize_mac_address(mac_address)

        # Get device
        device = get_device_by_mac(mac_address)
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not registered'
            }), 404

        device_id = device[0]

        # Get request data
        data = request.get_json()
        if not data or 'reminders' not in data:
            return jsonify({
                'success': False,
                'error': 'reminders array is required'
            }), 400

        reminders = data['reminders']
        if not isinstance(reminders, list):
            return jsonify({
                'success': False,
                'error': 'reminders must be an array'
            }), 400

        db = get_db()
        synced_count = 0
        now = datetime.now().isoformat()

        for reminder in reminders:
            # Validate required fields
            if 'remote_id' not in reminder or 'content' not in reminder:
                continue

            remote_id = reminder['remote_id']
            content = reminder['content']
            timestamp = reminder.get('timestamp')
            created_at = reminder.get('created_at', int(time.time()))

            # Check if reminder already exists (by remote_id)
            existing = db.execute(
                "SELECT id FROM reminders WHERE remote_id = ? AND device_id = ?",
                (remote_id, device_id),
                fetch_one=True
            )

            if existing:
                # Update existing reminder
                db.execute(
                    """UPDATE reminders
                       SET content = ?, scheduled_timestamp = ?, updated_at = ?
                       WHERE id = ?""",
                    (content, timestamp, now, existing[0])
                )
            else:
                # Create new reminder
                # Determine reminder_type based on content keywords
                # Detect daily reminder patterns in content
                daily_keywords = ['每天', '每日', '每日一次', '每天一次', '每天都要', '每日都要']
                reminder_type = 'daily' if any(kw in content for kw in daily_keywords) else 'once'

                db.execute(
                    """INSERT INTO reminders
                       (device_id, remote_id, content, reminder_type, scheduled_timestamp, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (device_id, remote_id, content, reminder_type, timestamp, now)
                )

            synced_count += 1

        # Update device last sync time
        db.execute(
            "UPDATE devices SET last_sync_at = ? WHERE id = ?",
            (now, device_id)
        )

        # Log sync
        db.execute(
            """INSERT INTO sync_logs (device_id, sync_direction, reminders_sent, reminders_received, sync_status)
               VALUES (?, 'push', 0, ?, 'success')""",
            (device_id, synced_count)
        )

        return jsonify({
            'success': True,
            'synced_count': synced_count,
            'synced_at': now
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/complete', methods=['POST'])
def sync_complete():
    """
    ESP32 confirms reminder completion
    Headers:
        Device-Id: MAC address

    Request Body:
        {
            "remote_id": "1736331234_12345",
            "completed_at": 1736335000
        }
    """
    try:
        # Get device MAC from header
        mac_address = request.headers.get('Device-Id')
        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'Missing Device-Id header'
            }), 400

        mac_address = normalize_mac_address(mac_address)

        # Get device
        device = get_device_by_mac(mac_address)
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not registered'
            }), 404

        device_id = device[0]

        # Get request data
        data = request.get_json()
        if not data or 'remote_id' not in data:
            return jsonify({
                'success': False,
                'error': 'remote_id is required'
            }), 400

        remote_id = data['remote_id']
        completed_at = data.get('completed_at', int(time.time()))

        # Update reminder status
        db = get_db()
        now = datetime.now().isoformat()

        updated = db.execute(
            """UPDATE reminders
               SET status = 'completed', completed_at = ?, updated_at = ?
               WHERE remote_id = ? AND device_id = ?""",
            (datetime.fromtimestamp(completed_at).isoformat(), now, remote_id, device_id)
        )

        if updated > 0:
            return jsonify({
                'success': True,
                'message': 'Reminder marked as completed'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Reminder not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/status', methods=['GET'])
def sync_status():
    """
    Get synchronization status for device
    Headers:
        Device-Id: MAC address
    """
    try:
        # Get device MAC from header
        mac_address = request.headers.get('Device-Id')
        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'Missing Device-Id header'
            }), 400

        mac_address = normalize_mac_address(mac_address)

        # Get device
        device = get_device_by_mac(mac_address)
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not registered'
            }), 404

        device_id = device[0]

        # Get sync logs
        db = get_db()
        logs = db.execute(
            """SELECT sync_direction, reminders_sent, reminders_received,
                      sync_status, created_at
               FROM sync_logs
               WHERE device_id = ?
               ORDER BY created_at DESC
               LIMIT 10""",
            (device_id,),
            fetch_all=True
        )

        sync_logs = []
        for row in logs:
            sync_logs.append({
                'direction': row[0],
                'sent': row[1],
                'received': row[2],
                'status': row[3],
                'timestamp': row[4]
            })

        return jsonify({
            'success': True,
            'sync_logs': sync_logs
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_sync_routes(app):
    """Register sync routes with Flask app"""
    app.register_blueprint(sync_bp)
    print("[OK] Device sync routes registered")
    print("     Endpoints:")
    print("       GET    /api/sync/pull")
    print("       POST   /api/sync/push")
    print("       POST   /api/sync/complete")
    print("       GET    /api/sync/status")
