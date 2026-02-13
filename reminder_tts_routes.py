#!/usr/bin/env python3
"""
提醒 TTS 路由 - 将文本转换为 xiaozhi 兼容的 Opus 音频格式
"""

import os
import tempfile
import struct
import asyncio
import subprocess
from flask import request, jsonify, Response
import traceback

# xiaozhi 音频参数
XIAOZHI_SAMPLE_RATE = 16000  # 采样率 16kHz
XIAOZHI_CHANNELS = 1          # 单声道
XIAOZHI_FRAME_DURATION = 60   # 帧时长 60ms


def register_reminder_routes(app):
    """注册提醒 TTS 相关的路由"""

    @app.route('/api/text_to_opus', methods=['POST'])
    def text_to_opus():
        """
        将文本转换为 xiaozhi 兼容的 Opus 音频格式
        返回 BinaryProtocol2 格式的二进制数据
        """
        try:
            # 获取请求数据
            data = request.get_json()
            if not data:
                return jsonify({
                    "success": False,
                    "error": "未找到请求数据"
                }), 400

            text = data.get('text', '')
            if not text:
                return jsonify({
                    "success": False,
                    "error": "text 参数不能为空"
                }), 400

            print(f"\n{'='*60}")
            print(f"收到 text_to_opus 请求: {text}")
            print(f"{'='*60}\n")

            # 1. 使用 edge-tts 生成 MP3 音频
            mp3_data = generate_edge_tts_mp3(text)
            if not mp3_data:
                return jsonify({
                    "success": False,
                    "error": "TTS 生成 MP3 失败"
                }), 500

            # 2. 将 MP3 转换为 WAV (16kHz, mono)
            wav_data = convert_mp3_to_wav(mp3_data)
            if not wav_data:
                return jsonify({
                    "success": False,
                    "error": "MP3 转 WAV 失败"
                }), 500

            # 3. 将 WAV 编码为 Opus (60ms 帧)
            opus_data = encode_wav_to_opus(wav_data)
            if not opus_data:
                return jsonify({
                    "success": False,
                    "error": "WAV 编码为 Opus 失败"
                }), 500

            # 4. 封装为 BinaryProtocol2 格式
            binary_packet = wrap_binary_protocol_v2(opus_data)

            print(f"✅ Opus 音频生成成功: {len(binary_packet)} 字节")

            # 返回二进制数据
            return Response(
                binary_packet,
                mimetype='application/octet-stream',
                headers={
                    'Content-Length': str(len(binary_packet)),
                    'Content-Disposition': 'attachment; filename=reminder.opus'
                }
            )

        except Exception as e:
            print(f"❌ 处理 text_to_opus 失败: {e}")
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/text_to_pcm', methods=['POST'])
    def text_to_pcm():
        """将文本转换为 16kHz Mono 16bit PCM (优先edge-tts，fallback到espeak)"""
        try:
            # 强制解析 JSON，即使 Content-Type 不完全匹配
            data = request.get_json(force=True, silent=True) or {}
            text = data.get('text', '')

            if not text:
                return jsonify({"success": False, "error": "Missing 'text' parameter"}), 400

            print(f"✅ [TTS] 收到 text_to_pcm 请求: {text}")

            # 策略1: 优先使用edge-tts（高质量语音）
            print(f"🎯 [TTS] 尝试使用 edge-tts...")
            mp3_data = generate_edge_tts_mp3_with_retry(text, max_retries=2)

            if mp3_data:
                # 转换MP3到WAV
                wav_data = convert_mp3_to_wav(mp3_data)
                if wav_data and len(wav_data) > 44:
                    pcm_data = wav_data[44:]  # 跳过WAV头
                    print(f"✅ [TTS] edge-tts + ffmpeg PCM生成成功: {len(pcm_data)} 字节")
                    return Response(
                        pcm_data,
                        mimetype='application/octet-stream',
                        headers={'Content-Length': str(len(pcm_data))}
                    )

            # 策略2: edge-tts失败，fallback到espeak（离线TTS）
            print(f"⚠️ [TTS] edge-tts不可用，fallback到espeak...")
            pcm_data = generate_espeak_pcm(text)

            if pcm_data:
                print(f"✅ [TTS] espeak PCM生成成功: {len(pcm_data)} 字节")
                return Response(
                    pcm_data,
                    mimetype='application/octet-stream',
                    headers={'Content-Length': str(len(pcm_data))}
                )
            else:
                print(f"❌ [TTS] 所有TTS方法都失败")
                return jsonify({"success": False, "error": "PCM 生成失败"}), 500

        except Exception as e:
            print(f"❌ [TTS] 异常: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500


def generate_espeak_pcm(text):
    """使用espeak生成 16kHz Mono 16bit PCM音频（优化中文发音）"""
    try:
        import subprocess

        # 创建临时WAV文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            wav_path = tmp_file.name

        # 优化发音清晰度的参数
        # -v zh+f3: 使用中文女声，f3/f4/f5有不同音色
        # -s 140: 稍慢的语速（更清晰）
        # -p 45: 稍低的音调（更稳重）
        # -a 150: 音量放大（更清晰）
        # -g 10: 字间停顿（更清晰）
        cmd = [
            'espeak',
            text,
            '-v', 'zh+f3',  # 使用f3女声，发音更清晰
            '-s', '140',     # 稍慢语速
            '-p', '45',      # 稍低音调
            '-a', '150',     # 音量放大
            '-g', '10',      # 字间停顿
            '-w', wav_path
        ]

        print(f"✅ [TTS] 执行espeak命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, timeout=10)

        if result.returncode != 0:
            print(f"❌ [TTS] espeak执行失败: {result.stderr.decode()}")
            return None

        # 读取WAV文件
        with open(wav_path, 'rb') as f:
            wav_data = f.read()

        # 删除临时文件
        os.unlink(wav_path)

        # 跳过WAV头(44字节)，返回纯PCM数据
        if len(wav_data) > 44:
            pcm_data = wav_data[44:]
            print(f"✅ [TTS] espeak生成PCM: {len(pcm_data)} 字节")
            return pcm_data
        else:
            print(f"❌ [TTS] WAV文件太小: {len(wav_data)} 字节")
            return None

    except Exception as e:
        print(f"❌ [TTS] espeak生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_edge_tts_mp3_with_retry(text, max_retries=3):
    """使用 edge-tts 生成 MP3 音频（带重试机制）"""
    for attempt in range(max_retries):
        try:
            import edge_tts

            # 尝试不同的中文voice - 优先使用正式语音
            voices = [
                "zh-CN-XiaoyanNeural",        # 女声，专业播音（正式）⭐
                "zh-CN-YunxiNeural",          # 男声，成熟稳重
                "zh-CN-YunyangNeural",        # 男声，新闻报道风格
                "zh-CN-XiaoxiaoNeural",       # 女声，温柔（备用）
            ]

            voice = voices[attempt % len(voices)]
            print(f"✅ [TTS] 尝试 edge-tts (第{attempt+1}次), 使用voice: {voice}")

            # 生成音频到临时文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # 异步生成音频
            async def _generate():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(tmp_path)

            # 运行异步任务（设置超时）
            try:
                asyncio.run(asyncio.wait_for(_generate(), timeout=30))
            except asyncio.TimeoutError:
                print(f"⚠️ [TTS] edge-tts 超时 (第{attempt+1}次)")
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if attempt < max_retries - 1:
                    continue
                else:
                    return None

            # 读取音频文件
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()

            # 删除临时文件
            os.unlink(tmp_path)

            print(f"✅ [TTS] edge-tts 生成 MP3 成功: {len(audio_data)} 字节")
            return audio_data

        except ImportError:
            print("❌ edge-tts 未安装，请运行: pip install edge-tts")
            return None
        except Exception as e:
            print(f"⚠️ [TTS] edge-tts 生成失败 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                print(f"⏳ [TTS] 等待2秒后重试...")
                import time
                time.sleep(2)
            else:
                print(f"❌ [TTS] edge-tts 重试{max_retries}次后仍失败，将fallback到espeak")
                return None

    return None


def generate_edge_tts_mp3(text):
    """使用 edge-tts 生成 MP3 音频（旧版，保留兼容）"""
    return generate_edge_tts_mp3_with_retry(text, max_retries=1)


def convert_mp3_to_wav(mp3_data):
    """将 MP3 转换为 WAV (16kHz, mono, 16bit)"""
    try:
        # 检查 ffmpeg 是否可用
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            print("❌ ffmpeg 未安装或不可用")
            return None

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
            mp3_path = mp3_file.name
            mp3_file.write(mp3_data)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = wav_file.name

        # 使用 ffmpeg 转换: 16kHz, mono, 16bit PCM
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-i', mp3_path,
            '-ar', str(XIAOZHI_SAMPLE_RATE),  # 采样率 16kHz
            '-ac', str(XIAOZHI_CHANNELS),      # 单声道
            '-acodec', 'pcm_s16le',            # 16bit PCM little-endian
            wav_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        # 删除 MP3 临时文件
        os.unlink(mp3_path)

        if result.returncode != 0:
            print(f"❌ ffmpeg 转换失败: {result.stderr.decode()}")
            return None

        # 读取 WAV 文件
        with open(wav_path, 'rb') as f:
            wav_data = f.read()

        # 删除 WAV 临时文件
        os.unlink(wav_path)

        print(f"MP3 转 WAV 成功: {len(wav_data)} 字节")
        return wav_data

    except FileNotFoundError:
        print("❌ ffmpeg 未找到，请安装 ffmpeg")
        return None
    except Exception as e:
        print(f"❌ MP3 转 WAV 失败: {e}")
        return None


def encode_wav_to_opus(wav_data):
    """将 WAV 编码为 Opus 格式 (60ms 帧)"""
    try:
        # 检查 opusenc 是否可用
        result = subprocess.run(['opusenc', '--version'],
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            print("❌ opusenc 未安装或不可用")
            return None

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = wav_file.name
            wav_file.write(wav_data)

        with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as opus_file:
            opus_path = opus_file.name

        # 使用 opusenc 编码: 16kHz, mono, 60ms 帧
        cmd = [
            'opusenc',
            '--raw',          # 输入是原始 PCM（跳过 WAV header）
            '--raw-rate', str(XIAOZHI_SAMPLE_RATE),
            '--raw-chan', str(XIAOZHI_CHANNELS),
            '--raw-bits', '16',
            '--frame-size', str(XIAOZHI_FRAME_DURATION),
            '--bitrate', '24000',
            '--downmix-mono',  # 强制单声道
            '--quiet',         # 减少输出
            wav_path,
            opus_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        # 删除 WAV 临时文件
        os.unlink(wav_path)

        if result.returncode != 0:
            print(f"❌ opusenc 编码失败: {result.stderr.decode()}")
            return None

        # 读取 Opus 文件
        with open(opus_path, 'rb') as f:
            opus_with_header = f.read()

        # 删除 Opus 临时文件
        os.unlink(opus_path)

        print(f"WAV 编码为 Opus 成功: {len(opus_with_header)} 字节")
        return opus_with_header

    except FileNotFoundError:
        print("❌ opusenc 未找到，请安装 opus-tools")
        print("安装命令: apt-get install opus-tools")
        return None
    except Exception as e:
        print(f"❌ WAV 编码为 Opus 失败: {e}")
        return None


def wrap_binary_protocol_v2(opus_payload):
    """
    将 Opus 数据封装为 BinaryProtocol2 格式
    struct BinaryProtocol2 {
        uint16_t version;      // 版本号 (2)
        uint16_t type;         // 类型 (0 = OPUS)
        uint32_t reserved;     // 保留字段
        uint32_t timestamp;    // 时间戳 (毫秒)
        uint32_t payload_size; // 负载大小
        uint8_t payload[];     // Opus 数据
    }
    """
    try:
        version = 2
        msg_type = 0  # 0 = OPUS 音频
        reserved = 0
        timestamp = 0  # 可以设置为当前时间戳
        payload_size = len(opus_payload)

        # 构造包头（网络字节序，大端）
        header = struct.pack(
            '!HHIII',
            version,        # uint16_t
            msg_type,       # uint16_t
            reserved,       # uint32_t
            timestamp,      # uint32_t
            payload_size    # uint32_t
        )

        # 拼接包头和负载数据
        binary_packet = header + opus_payload

        print(f"封装 BinaryProtocol2 成功: 总大小 {len(binary_packet)} 字节 "
              f"(包头 16 字节 + 负载 {payload_size} 字节)")

        return binary_packet

    except Exception as e:
        print(f"❌ 封装 BinaryProtocol2 失败: {e}")
        return None
