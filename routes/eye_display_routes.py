"""
眼睛显示相关路由
"""
from flask import Blueprint, request, jsonify
import logging
from services.eye_display_service import get_eye_service, init_eye_service

logger = logging.getLogger(__name__)
bp = Blueprint('eye_display', __name__, url_prefix='/api/eye')


def init_eye_display_routes(port: str = 'COM3', baudrate: int = 115200):
    """
    初始化眼睛显示服务和路由

    Args:
        port: 串口号
        baudrate: 波特率
    """
    # 初始化全局服务
    service = init_eye_service(port, baudrate, auto_start=True)
    if service:
        # 设置触摸传感器回调
        setup_touch_handlers(service)
    return service


def setup_touch_handlers(service):
    """
    设置触摸事件处理器

    Args:
        service: EyeDisplayService 实例
    """
    import random

    def on_touch_1():
        """触摸传感器1：播放随机声音/表情"""
        logger.info("处理触摸传感器1事件")
        expressions = ["happy", "surprised", "blink"]
        expr = random.choice(expressions)

        if expr == "blink":
            service.blink()
        else:
            service.set_expression(expr)

        # TODO: 集成 TTS 服务播放声音
        logger.info(f"触摸传感器1: 触发 {expr}")

    def on_touch_2():
        """触摸传感器2：打断当前操作"""
        logger.info("处理触摸传感器2事件 - 打断操作")

        # TODO: 实现打断逻辑
        # 1. 如果正在播放 TTS，停止播放
        # 2. 如果正在分析，取消分析
        # 3. 播放取消提示音

        service.set_expression("surprised")
        logger.info("触摸传感器2: 触发打断")

    service.on_touch_1 = on_touch_1
    service.on_touch_2 = on_touch_2
    logger.info("触摸事件处理器已设置")


@bp.route('/status', methods=['GET'])
def get_status():
    """获取眼睛显示服务状态"""
    service = get_eye_service()
    if not service:
        return jsonify({
            "success": False,
            "error": "服务未初始化"
        }), 500

    return jsonify({
        "success": True,
        "data": service.get_status()
    })


@bp.route('/expression', methods=['POST'])
def set_expression():
    """
    设置表情

    请求体:
        {
            "emotion": "happy"  // happy, sad, angry, surprised, neutral, thinking, listening
        }

    响应:
        {
            "success": true,
            "emotion": "happy"
        }
    """
    service = get_eye_service()
    if not service:
        return jsonify({
            "success": False,
            "error": "服务未初始化"
        }), 500

    data = request.get_json()
    if not data:
        return jsonify({
            "success": False,
            "error": "缺少请求体"
        }), 400

    emotion = data.get('emotion', 'neutral')
    logger.info(f"设置表情: {emotion}")

    if service.set_expression(emotion):
        return jsonify({
            "success": True,
            "expression": emotion
        })
    else:
        return jsonify({
            "success": False,
            "error": "设置失败"
        }), 500


@bp.route('/animation', methods=['POST'])
def play_animation():
    """
    播放动画

    请求体:
        {
            "animation": "blink"  // blink, talk, listen, think, idle
        }

    响应:
        {
            "success": true,
            "animation": "blink"
        }
    """
    service = get_eye_service()
    if not service:
        return jsonify({
            "success": False,
            "error": "服务未初始化"
        }), 500

    data = request.get_json()
    if not data:
        return jsonify({
            "success": False,
            "error": "缺少请求体"
        }), 400

    animation = data.get('animation', '')
    logger.info(f"播放动画: {animation}")

    if service.play_animation(animation):
        return jsonify({
            "success": True,
            "animation": animation
        })
    else:
        return jsonify({
            "success": False,
            "error": "播放失败"
        }), 500


@bp.route('/text', methods=['POST'])
def show_text():
    """
    显示文字

    请求体:
        {
            "text": "你好",
            "duration": 3  // 可选，显示时长（秒），默认3秒
        }

    响应:
        {
            "success": true
        }
    """
    service = get_eye_service()
    if not service:
        return jsonify({
            "success": False,
            "error": "服务未初始化"
        }), 500

    data = request.get_json()
    if not data:
        return jsonify({
            "success": False,
            "error": "缺少请求体"
        }), 400

    text = data.get('text', '')
    duration = data.get('duration', 3)

    if not text:
        return jsonify({
            "success": False,
            "error": "文字内容不能为空"
        }), 400

    logger.info(f"显示文字: {text} (持续{duration}秒)")

    if service.show_text(text, duration):
        return jsonify({
            "success": True,
            "text": text,
            "duration": duration
        })
    else:
        return jsonify({
            "success": False,
            "error": "显示失败"
        }), 500


@bp.route('/brightness', methods=['POST'])
def set_brightness():
    """
    设置屏幕亮度

    请求体:
        {
            "brightness": 80  // 0-100
        }

    响应:
        {
            "success": true,
            "brightness": 80
        }
    """
    service = get_eye_service()
    if not service:
        return jsonify({
            "success": False,
            "error": "服务未初始化"
        }), 500

    data = request.get_json()
    if not data:
        return jsonify({
            "success": False,
            "error": "缺少请求体"
        }), 400

    brightness = data.get('brightness', 100)

    if service.set_brightness(brightness):
        return jsonify({
            "success": True,
            "brightness": brightness
        })
    else:
        return jsonify({
            "success": False,
            "error": "设置失败"
        }), 500


@bp.route('/happy', methods=['POST'])
def happy():
    """快捷方法：设置开心表情"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.happy():
        return jsonify({"success": True, "expression": "happy"})
    return jsonify({"success": False, "error": "设置失败"}), 500


@bp.route('/sad', methods=['POST'])
def sad():
    """快捷方法：设置伤心表情"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.sad():
        return jsonify({"success": True, "expression": "sad"})
    return jsonify({"success": False, "error": "设置失败"}), 500


@bp.route('/angry', methods=['POST'])
def angry():
    """快捷方法：设置生气表情"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.angry():
        return jsonify({"success": True, "expression": "angry"})
    return jsonify({"success": False, "error": "设置失败"}), 500


@bp.route('/surprised', methods=['POST'])
def surprised():
    """快捷方法：设置惊讶表情"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.surprised():
        return jsonify({"success": True, "expression": "surprised"})
    return jsonify({"success": False, "error": "设置失败"}), 500


@bp.route('/neutral', methods=['POST'])
def neutral():
    """快捷方法：设置中性表情"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.neutral():
        return jsonify({"success": True, "expression": "neutral"})
    return jsonify({"success": False, "error": "设置失败"}), 500


@bp.route('/thinking', methods=['POST'])
def thinking():
    """快捷方法：设置思考表情"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.thinking():
        return jsonify({"success": True, "expression": "thinking"})
    return jsonify({"success": False, "error": "设置失败"}), 500


@bp.route('/listening', methods=['POST'])
def listening():
    """快捷方法：设置聆听表情"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.listening():
        return jsonify({"success": True, "expression": "listening"})
    return jsonify({"success": False, "error": "设置失败"}), 500


@bp.route('/blink', methods=['POST'])
def blink():
    """快捷方法：眨眼动画"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.blink():
        return jsonify({"success": True, "animation": "blink"})
    return jsonify({"success": False, "error": "播放失败"}), 500


@bp.route('/talk', methods=['POST'])
def talk():
    """快捷方法：说话动画"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.talk():
        return jsonify({"success": True, "animation": "talk"})
    return jsonify({"success": False, "error": "播放失败"}), 500


@bp.route('/idle', methods=['POST'])
def idle():
    """快捷方法：空闲动画"""
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    if service.idle():
        return jsonify({"success": True, "animation": "idle"})
    return jsonify({"success": False, "error": "播放失败"}), 500


@bp.route('/test', methods=['POST'])
def test_all():
    """
    测试所有功能

    依次测试：所有表情、动画、文字显示
    """
    service = get_eye_service()
    if not service:
        return jsonify({"success": False, "error": "服务未初始化"}), 500

    results = []

    # 测试表情
    expressions = ["happy", "sad", "angry", "surprised", "neutral"]
    for expr in expressions:
        result = service.set_expression(expr)
        results.append({"type": "expression", "value": expr, "success": result})
        import time
        time.sleep(0.5)

    # 测试动画
    animations = ["blink", "idle"]
    for anim in animations:
        result = service.play_animation(anim)
        results.append({"type": "animation", "value": anim, "success": result})
        time.sleep(0.5)

    # 测试文字
    result = service.show_text("测试", 2)
    results.append({"type": "text", "value": "测试", "success": result})

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    return jsonify({
        "success": True,
        "results": results,
        "summary": f"测试完成: {success_count}/{total_count} 成功"
    })
