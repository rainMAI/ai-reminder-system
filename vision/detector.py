"""
图像识别模块 - 使用 MediaPipe 新 API (0.10.x+)
支持人脸和手掌特征提取，并匹配知识库
"""

import os
import json
import urllib.request
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

# OpenCV
import cv2
import numpy as np

# MediaPipe 新 API
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================================
# 模型下载器
# ============================================================================

class ModelDownloader:
    """自动下载 MediaPipe 模型文件"""

    # 模型文件映射 - 使用官方 Google 存储的链接（float16 版本，更小更快）
    MODELS = {
        "face_landmarker": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
        "face_landmarker_lite": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker_lite/float16/latest/face_landmarker_lite.task",
        "hand_landmarker": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        "hand_landmarker_lite": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker_lite/float16/latest/hand_landmarker_lite.task"
    }

    # GitHub releases 备用链接
    GITHUB_URLS = {
        "face_landmarker": "https://github.com/google-ai-edge/mediapipe/releases/download/v0.10.7/face_landmarker.task",
        "hand_landmarker": "https://github.com/google-ai-edge/mediapipe/releases/download/v0.10.7/hand_landmarker.task"
    }

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)

    def download_model(self, model_name: str) -> Optional[str]:
        """
        下载指定的模型文件

        Args:
            model_name: 模型名称 (face_landmarker 或 hand_landmarker)

        Returns:
            模型文件路径，如果下载失败返回 None
        """
        # 支持多个模型名称变体
        model_base = model_name.replace("_lite", "").replace(".task", "")

        if model_base not in ["face_landmarker", "hand_landmarker"]:
            print(f"❌ 未知模型: {model_name}")
            return None

        model_filename = f"{model_base}.task"
        model_path = self.models_dir / model_filename

        # 如果已存在，直接返回
        if model_path.exists():
            print(f"✅ 模型已存在: {model_path}")
            return str(model_path)

        # 尝试多个下载源
        urls_to_try = []

        # 1. 尝试 lite 版本（如果请求）
        if "_lite" in model_name:
            urls_to_try.append(self.MODELS.get(f"{model_base}_lite"))

        # 2. 尝试完整版本
        urls_to_try.append(self.MODELS.get(model_base))

        # 3. 尝试 GitHub releases
        if model_base in self.GITHUB_URLS:
            urls_to_try.append(self.GITHUB_URLS[model_base])

        # 过滤掉 None 值
        urls_to_try = [url for url in urls_to_try if url]

        for url in urls_to_try:
            print(f"正在下载 {model_name} 模型...")
            print(f"来源: {url}")

            try:
                urllib.request.urlretrieve(url, model_path)
                print(f"✅ 模型下载完成: {model_path}")
                return str(model_path)
            except Exception as e:
                print(f"⚠️  从 {url} 下载失败: {e}")
                continue

        print(f"❌ 所有下载源均失败，请手动下载:")
        print(f"   1. 访问: https://github.com/google-ai-edge/mediapipe/releases")
        print(f"   2. 下载 {model_filename}")
        print(f"   3. 放到: {self.models_dir}")
        return None

    def download_all_models(self) -> Dict[str, Optional[str]]:
        """下载所有必需的模型"""
        results = {}
        for model_name in self.MODELS.keys():
            results[model_name] = self.download_model(model_name)
        return results


# ============================================================================
# 人脸特征检测器
# ============================================================================

@dataclass
class FaceMeasurements:
    """人脸测量数据"""
    # 三停比例
    forehead_ratio: float  # 上停比例
    middle_ratio: float    # 中停比例
    lower_ratio: float     # 下停比例

    # 五官
    left_eye_ratio: float   # 左眼比例
    right_eye_ratio: float  # 右眼比例
    nose_ratio: float       # 鼻子比例
    mouth_ratio: float      # 嘴巴比例

    # 脸型
    face_width: float
    face_height: float
    face_shape_ratio: float


@dataclass
class FaceFeatures:
    """人脸特征判断"""
    forehead: str  # 饱满/狭窄/适中
    eyes: str      # 大眼/小眼/适中
    nose: str      # 高挺/塌鼻/适中
    mouth: str     # 大嘴/小嘴/适中
    face_shape: str # 圆脸/方脸/长脸/ oval


class FaceFeatureDetector:
    """人脸特征检测器 - 使用 MediaPipe FaceLandmarker"""

    # MediaPipe Face Landmark 索引
    # 参考: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
    LANDMARKS = {
        "forehead_top": 10,          # 头顶最高点
        "forehead_bottom": 9,        # 【修复】额头底部(眉心,中庭起点)
        "eyebrow_center": 9,         # 眉心位置
        "eye_left": 33,              # 左眼外角
        "eye_right": 263,            # 右眼外角
        "nose_tip": 1,               # 鼻尖
        "nose_bridge": 6,            # 鼻梁
        "nose_bottom": 164,          # 【新增】鼻子底部(中庭终点)
        "mouth_left": 61,            # 嘴巴左角
        "mouth_right": 291,          # 嘴巴右角
        "mouth_top": 13,             # 上唇
        "mouth_bottom": 14,          # 下唇
        "chin": 152,                 # 下巴最低点
        "face_left": 234,            # 左脸颊最宽处
        "face_right": 454,           # 右脸颊最宽处
    }

    def __init__(self):
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        """初始化检测器"""
        try:
            # 下载或获取模型
            downloader = ModelDownloader()
            model_path = downloader.download_model("face_landmarker")

            if model_path is None:
                raise RuntimeError("无法下载 face_landmarker 模型")

            # 创建 BaseOptions
            base_options = python.BaseOptions(model_asset_path=model_path)

            # 创建 FaceLandmarkerOptions
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )

            # 创建检测器
            self.detector = vision.FaceLandmarker.create_from_options(options)
            print("✅ FaceLandmarker 初始化成功")

        except Exception as e:
            print(f"❌ FaceLandmarker 初始化失败: {e}")
            self.detector = None

    def detect(self, image_input: Union[str, bytes, np.ndarray]) -> Optional[Dict]:
        """
        检测人脸特征

        Args:
            image_input: 图片路径、Base64编码的字符串、或numpy数组

        Returns:
            检测结果字典，如果失败返回 None
        """
        if self.detector is None:
            return {"error": "FaceLandmarker 未初始化"}

        try:
            # 根据输入类型读取图片
            image = None

            if isinstance(image_input, np.ndarray):
                # 已经是 numpy 数组
                image = image_input
            elif isinstance(image_input, bytes):
                # Base64 编码的 bytes
                img_data = base64.b64decode(image_input)
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            elif isinstance(image_input, str):
                if image_input.startswith('data:image'):
                    # Data URL 格式 (data:image/jpeg;base64,...)
                    # 提取 base64 部分
                    header, encoded = image_input.split(',', 1)
                    img_data = base64.b64decode(encoded)
                    img_array = np.frombuffer(img_data, dtype=np.uint8)
                    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                elif len(image_input) > 100 and not os.path.exists(image_input):
                    # 可能是纯 base64 编码的字符串（不存在该路径，且长度较长）
                    try:
                        img_data = base64.b64decode(image_input)
                        img_array = np.frombuffer(img_data, dtype=np.uint8)
                        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    except Exception:
                        # 如果 base64 解码失败，当作文件路径处理
                        image = cv2.imread(image_input)
                else:
                    # 当作文件路径处理
                    image = cv2.imread(image_input)
            else:
                return {"error": f"不支持的图片输入类型: {type(image_input)}"}

            if image is None:
                return {"error": "无法读取图片，请检查输入格式"}

            # 转换为 RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 转换为 MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

            # 检测
            detection_result = self.detector.detect(mp_image)

            if not detection_result.face_landmarks:
                return {"error": "未检测到人脸"}

            # 提取第一个脸的特征点
            landmarks = detection_result.face_landmarks[0]

            # 计算测量数据
            measurements = self._calculate_measurements(landmarks)

            # 判断特征
            features = self._judge_features(measurements)

            return {
                "measurements": measurements,
                "features": features
            }

        except Exception as e:
            return {"error": str(e)}

    def _calculate_measurements(self, landmarks) -> Dict:
        """计算人脸测量数据"""
        # 获取关键点坐标
        def get_point(index):
            lm = landmarks[index]
            return {'x': lm.x, 'y': lm.y}

        # 关键点
        forehead_top = get_point(self.LANDMARKS["forehead_top"])
        forehead_bottom = get_point(self.LANDMARKS["forehead_bottom"])
        eye_left = get_point(self.LANDMARKS["eye_left"])
        eye_right = get_point(self.LANDMARKS["eye_right"])
        nose_tip = get_point(self.LANDMARKS["nose_tip"])
        nose_bridge = get_point(self.LANDMARKS["nose_bridge"])
        nose_bottom = get_point(self.LANDMARKS["nose_bottom"])
        mouth_left = get_point(self.LANDMARKS["mouth_left"])
        mouth_right = get_point(self.LANDMARKS["mouth_right"])
        mouth_top = get_point(self.LANDMARKS["mouth_top"])
        mouth_bottom = get_point(self.LANDMARKS["mouth_bottom"])
        chin = get_point(self.LANDMARKS["chin"])
        face_left = get_point(self.LANDMARKS["face_left"])
        face_right = get_point(self.LANDMARKS["face_right"])

        # 计算面部高度（从额头到下巴）
        face_height = abs(chin['y'] - forehead_top['y'])

        # 【修复】三停 - 使用更准确的关键点
        # 上停(额头): 从发际线(10号点)到眉心(9号点)
        forehead_height = abs(forehead_bottom['y'] - forehead_top['y'])

        # 中停(眉到鼻): 从眉心(9号点)到鼻子底部(164号点)
        middle_height = abs(nose_bottom['y'] - forehead_bottom['y'])

        # 下停(鼻到下巴): 从鼻子底部(164号点)到下巴(152号点)
        lower_height = abs(chin['y'] - nose_bottom['y'])

        # 比例
        forehead_ratio = forehead_height / face_height if face_height > 0 else 0
        middle_ratio = middle_height / face_height if face_height > 0 else 0
        lower_ratio = lower_height / face_height if face_height > 0 else 0

        # 面部宽度
        face_width = abs(face_right['x'] - face_left['x'])

        # 眼睛宽度
        eye_width = abs(eye_right['x'] - eye_left['x'])
        left_eye_ratio = eye_width / face_width if face_width > 0 else 0
        right_eye_ratio = left_eye_ratio  # 简化

        # 鼻子长度和宽度
        nose_length = abs(nose_tip['y'] - nose_bridge['y'])
        nose_width = abs(mouth_left['x'] - mouth_right['x']) * 0.3  # 估算
        nose_ratio = nose_length / nose_width if nose_width > 0 else 0

        # 嘴巴
        mouth_width = abs(mouth_right['x'] - mouth_left['x'])
        mouth_height = abs(mouth_bottom['y'] - mouth_top['y'])
        mouth_ratio = mouth_width / face_width if face_width > 0 else 0

        # 脸型比例
        face_shape_ratio = face_height / face_width if face_width > 0 else 0

        return {
            "forehead": {"ratio": round(forehead_ratio, 3)},
            "middle": {"ratio": round(middle_ratio, 3)},
            "lower": {"ratio": round(lower_ratio, 3)},
            "eyes": {
                "left_ratio": round(left_eye_ratio, 3),
                "right_ratio": round(right_eye_ratio, 3)
            },
            "nose": {"ratio": round(nose_ratio, 3)},
            "mouth": {"ratio": round(mouth_ratio, 3)},
            "face": {
                "width": round(face_width, 3),
                "height": round(face_height, 3),
                "shape_ratio": round(face_shape_ratio, 3)
            }
        }

    def _judge_features(self, measurements: Dict) -> Dict:
        """根据测量数据判断特征"""
        # 额头
        forehead_ratio = measurements["forehead"]["ratio"]
        if forehead_ratio > 0.35:
            forehead = "饱满"
        elif forehead_ratio < 0.25:
            forehead = "狭窄"
        else:
            forehead = "适中"

        # 眼睛
        left_eye_ratio = measurements["eyes"]["left_ratio"]
        if left_eye_ratio > 0.28:
            eyes = "大眼"
        elif left_eye_ratio < 0.22:
            eyes = "小眼"
        else:
            eyes = "适中"

        # 鼻子
        nose_ratio = measurements["nose"]["ratio"]
        if nose_ratio > 2.0:
            nose = "高挺"
        elif nose_ratio < 1.5:
            nose = "塌鼻"
        else:
            nose = "适中"

        # 嘴巴
        mouth_ratio = measurements["mouth"]["ratio"]
        if mouth_ratio > 0.4:
            mouth = "大嘴"
        elif mouth_ratio < 0.3:
            mouth = "小嘴"
        else:
            mouth = "适中"

        # 脸型
        face_shape_ratio = measurements["face"]["shape_ratio"]
        if face_shape_ratio > 1.3:
            face_shape = "长脸"
        elif face_shape_ratio < 1.0:
            face_shape = "圆脸"
        elif 1.0 <= face_shape_ratio <= 1.15:
            face_shape = "方脸"
        else:
            face_shape = "oval"

        return {
            "forehead": forehead,
            "eyes": eyes,
            "nose": nose,
            "mouth": mouth,
            "face_shape": face_shape
        }


# ============================================================================
# 手掌特征检测器
# ============================================================================

class PalmFeatureDetector:
    """手掌特征检测器 - 使用 MediaPipe HandLandmarker"""

    def __init__(self):
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        """初始化检测器"""
        try:
            # 下载或获取模型
            downloader = ModelDownloader()
            model_path = downloader.download_model("hand_landmarker")

            if model_path is None:
                raise RuntimeError("无法下载 hand_landmarker 模型")

            # 创建 BaseOptions
            base_options = python.BaseOptions(model_asset_path=model_path)

            # 创建 HandLandmarkerOptions
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=1,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )

            # 创建检测器
            self.detector = vision.HandLandmarker.create_from_options(options)
            print("✅ HandLandmarker 初始化成功")

        except Exception as e:
            print(f"❌ HandLandmarker 初始化失败: {e}")
            self.detector = None

    def detect(self, image_path: str, hand: str = "right") -> Optional[Dict]:
        """
        检测手掌特征

        Args:
            image_path: 图片路径
            hand: left 或 right

        Returns:
            检测结果字典，如果失败返回 None
        """
        if self.detector is None:
            return {"error": "HandLandmarker 未初始化"}

        try:
            # 读取图片
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "无法读取图片"}

            # 转换为 RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 转换为 MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

            # 检测
            detection_result = self.detector.detect(mp_image)

            if not detection_result.hand_landmarks:
                return {"error": "未检测到手掌"}

            # 提取第一只手的特征点
            landmarks = detection_result.hand_landmarks[0]

            # 计算测量数据
            measurements = self._calculate_measurements(landmarks)

            # 判断手型
            hand_shape = self._judge_hand_shape(measurements)

            # 检测主线（简化版本）
            lines = self._detect_lines(landmarks)

            return {
                "measurements": measurements,
                "hand_shape": hand_shape,
                "lines": lines
            }

        except Exception as e:
            return {"error": str(e)}

    def _calculate_measurements(self, landmarks) -> Dict:
        """计算手掌测量数据"""
        # 获取关键点（简化版本）
        # MediaPipe 手部关键点: 0-20
        # 0: 手腕, 4: 拇指尖, 8: 食指尖, 12: 中指尖, 16: 无名指尖, 20: 小指尖

        def get_point(index):
            lm = landmarks[index]
            return {'x': lm.x, 'y': lm.y}

        wrist = get_point(0)
        thumb_tip = get_point(4)
        index_tip = get_point(8)
        middle_tip = get_point(12)
        ring_tip = get_point(16)
        pinky_tip = get_point(20)
        middle_mcp = get_point(9)  # 中指根部

        # 手掌长度（手腕到中指尖）
        palm_length = abs(middle_tip['y'] - wrist['y'])

        # 手掌宽度（拇指到小指）
        palm_width = abs(pinky_tip['x'] - thumb_tip['x'])

        # 手指长度
        thumb_length = abs(thumb_tip['y'] - wrist['y'])
        index_length = abs(index_tip['y'] - middle_mcp['y'])
        middle_length = abs(middle_tip['y'] - middle_mcp['y'])
        ring_length = abs(ring_tip['y'] - middle_mcp['y'])
        pinky_length = abs(pinky_tip['y'] - middle_mcp['y'])

        return {
            "palm": {
                "length": round(palm_length, 3),
                "width": round(palm_width, 3),
                "ratio": round(palm_length / palm_width if palm_width > 0 else 0, 3)
            },
            "fingers": {
                "thumb": round(thumb_length, 3),
                "index": round(index_length, 3),
                "middle": round(middle_length, 3),
                "ring": round(ring_length, 3),
                "pinky": round(pinky_length, 3)
            }
        }

    def _judge_hand_shape(self, measurements: Dict) -> str:
        """判断手型（金木水火土）"""
        palm_ratio = measurements["palm"]["ratio"]

        if palm_ratio > 1.2:
            return "木手"  # 长手
        elif palm_ratio < 0.8:
            return "水手"  # 短手
        elif 0.8 <= palm_ratio <= 1.0:
            return "火手"  # 方手
        elif 1.0 < palm_ratio <= 1.2:
            return "土手"  # 圆手
        else:
            return "金手"  # 适中

    def _detect_lines(self, landmarks) -> Dict:
        """检测手掌主线（简化版本，实际需要更复杂的算法）"""
        # 这里返回模拟数据，实际应该检测生命线、智慧线、感情线
        return {
            "life_line": {"length": "long", "clarity": "clear"},
            "head_line": {"length": "medium", "clarity": "clear"},
            "heart_line": {"length": "long", "clarity": "clear"}
        }


# ============================================================================
# 知识库匹配器
# ============================================================================

class KnowledgeBaseMatcher:
    """知识库匹配器 - 将检测到的特征与古籍知识库匹配"""

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_root = Path(knowledge_dir)
        self._load_all_knowledge()

    def _load_all_knowledge(self):
        """加载所有知识库文件"""
        self.knowledge = {}

        # 遍历所有 JSON 文件
        for json_file in self.knowledge_root.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    category = data.get('category', '')
                    source = data.get('source', '')
                    key = f"{category}/{source}"
                    self.knowledge[key] = data
            except Exception as e:
                print(f"⚠️  加载知识库失败 {json_file}: {e}")

        print(f"✅ 已加载 {len(self.knowledge)} 个知识库文件")

    def _list_knowledge_files(self) -> List[Dict]:
        """列出所有知识库文件"""
        files = []
        for key, data in self.knowledge.items():
            files.append({
                "category": data.get('category', ''),
                "source": data.get('source', ''),
                "feature_count": len(data.get('features', []))
            })
        return files

    def match_face_features(self, features: Dict, gender: str = "female") -> Dict:
        """
        匹配面相特征到知识库 - 详细版本

        Args:
            features: 检测到的特征
            gender: 性别

        Returns:
            详细的匹配结果
        """
        # 面相相关的分类
        face_categories = ['三停', '五官', '五岳', '十二宫', '骨法', '气色', '动态',
                          '儿童相', '女相', '流年', '痣相', '脸型', '面部']

        # 构建特征映射
        feature_map = {
            "forehead": features.get("forehead", ""),
            "eyes": features.get("eyes", ""),
            "nose": features.get("nose", ""),
            "mouth": features.get("mouth", ""),
            "face_shape": features.get("face_shape", "")
        }

        matched_results = []
        sources = set()

        # 遍历所有知识库，筛选出面相相关的
        for key, knowledge in self.knowledge.items():
            category = knowledge.get('category', '')

            # 检查是否是面相知识库
            is_face = any(cat in category for cat in face_categories)
            if not is_face:
                continue

            source = knowledge.get("source", "")

            # 遍历知识库中的特征
            for feature_item in knowledge.get("features", []):
                feature_name = feature_item.get("name", "")
                position = feature_item.get("position", "")

                # 特征名称映射到检测的特征
                detected_key = self._map_feature_name(feature_name)
                detected_value = feature_map.get(detected_key, "")

                if not detected_value:
                    continue

                # 遍历标准列表
                for standard in feature_item.get("standards", []):
                    standard_feature = standard.get("feature", "")

                    # 检查是否匹配（模糊匹配）
                    if self._is_feature_match(detected_value, standard_feature):
                        # 构建详细匹配结果
                        match_result = {
                            "部位": feature_name,
                            "位置": position,
                            "检测结果": detected_value,
                            "古籍": source,
                            "分类": category,
                            "原文": standard.get("original_text", ""),
                            "现代解释": standard.get("modern_explanation", ""),
                            "年龄范围": standard.get("age_range", ""),
                            "详细分析": {}
                        }

                        # 添加各方面分析
                        aspects = standard.get("aspects", {})
                        if aspects:
                            match_result["详细分析"] = aspects

                        # 添加性格分析（如果有）
                        if "personality" in standard:
                            match_result["性格分析"] = standard["personality"]

                        # 添加建议（如果有）
                        if "advice" in standard:
                            match_result["建议"] = standard["advice"]

                        # 添加禁忌（如果有）
                        if "taboos" in standard:
                            match_result["禁忌"] = standard["taboos"]

                        matched_results.append(match_result)
                        sources.add(source)

        # 生成综合分析
        summary = self._generate_face_summary(matched_results, feature_map, gender)

        return {
            "matched_features": matched_results,
            "sources": list(sources),
            "summary": summary,
            "total_matches": len(matched_results)
        }

    def match_palm_features(self, palm_data: Dict) -> Dict:
        """
        匹配手相特征到知识库

        Args:
            palm_data: 检测到的手掌数据

        Returns:
            匹配结果
        """
        matched_features = []
        sources = set()

        hand_shape = palm_data.get("hand_shape", "")
        lines = palm_data.get("lines", {})

        # 遍历知识库
        for key, knowledge in self.knowledge.items():
            if not key.startswith("palm/") and not key.startswith("koujue/"):
                continue

            for feature in knowledge.get("features", []):
                # 匹配手型
                if hand_shape and hand_shape in feature.get("name", ""):
                    matched_features.append({
                        "part": "手型",
                        "detected": hand_shape,
                        "description": feature.get("modern_explanation", ""),
                        "source": knowledge.get("source", "")
                    })
                    sources.add(knowledge.get("source", ""))

        return {
            "matched_features": matched_features,
            "sources": list(sources),
            "hand_shape": hand_shape
        }

    def _is_match(self, detected: Dict, knowledge_feature: Dict) -> bool:
        """检查检测到的特征是否与知识库特征匹配"""
        name = knowledge_feature.get("name", "").lower()

        # 简单匹配：检查特征名称是否在 detected 中
        for key in detected.keys():
            if name in key or key in name:
                return True

        return False

    def _map_feature_name(self, knowledge_name: str) -> Optional[str]:
        """
        将知识库中的特征名称映射到检测的特征键

        Args:
            knowledge_name: 知识库中的特征名称

        Returns:
            检测特征的键名
        """
        mapping = {
            "上停": "forehead",
            "额头": "forehead",
            "中停": "nose",
            "鼻子": "nose",
            "下停": "mouth",
            "嘴巴": "mouth",
            "眼睛": "eyes",
            "眼": "eyes",
            "脸型": "face_shape",
            "面部": "face_shape"
        }

        # 模糊匹配
        for k, v in mapping.items():
            if k in knowledge_name:
                return v

        return None

    def _is_feature_match(self, detected_value: str, standard_feature: str) -> bool:
        """
        检查检测到的值是否与知识库标准匹配

        Args:
            detected_value: 检测到的值（如"狭窄"、"饱满"）
            standard_feature: 知识库中的标准（如"上停尖削"）

        Returns:
            是否匹配
        """
        if not detected_value or not standard_feature:
            return False

        # 精确匹配关键词
        match_patterns = {
            "狭窄": ["尖削", "窄小", "低陷"],
            "饱满": ["饱满", "圆润", "丰厚"],
            "适中": ["匀称", "适中", "标准", "正常"],
            "大眼": ["大眼", "眼大"],
            "小眼": ["小眼", "眼小"],
            "高挺": ["高挺", "鼻高"],
            "塌鼻": ["塌鼻", "鼻塌"],
            "圆脸": ["圆脸", "面圆"],
            "方脸": ["方脸", "面方"],
            "长脸": ["长脸", "面长"]
        }

        # 直接关键词匹配
        patterns = match_patterns.get(detected_value, [])
        for pattern in patterns:
            if pattern in standard_feature:
                return True

        return False

    def _generate_face_summary(self, matched_results: List[Dict], feature_map: Dict, gender: str) -> Dict:
        """
        生成面相综合分析总结

        Args:
            matched_results: 匹配结果列表
            feature_map: 特征映射
            gender: 性别

        Returns:
            综合分析总结
        """
        summary = {
            "总体评价": "",
            "早年运势": {},
            "中年运势": {},
            "晚年运势": {},
            "性格特点": [],
            "建议": [],
            "禁忌": []
        }

        # 按年龄分组
        for match in matched_results:
            age_range = match.get("年龄范围", "")
            original_text = match.get("原文", "")
            explanation = match.get("现代解释", "")
            aspects = match.get("详细分析", {})

            if "0-35" in age_range or "早年" in age_range:
                summary["早年运势"]["原文"] = original_text
                summary["早年运势"]["解释"] = explanation
                if aspects:
                    summary["早年运势"]["各方面"] = aspects

            elif "35-50" in age_range or "中年" in age_range:
                summary["中年运势"]["原文"] = original_text
                summary["中年运势"]["解释"] = explanation
                if aspects:
                    summary["中年运势"]["各方面"] = aspects

            elif "50" in age_range or "晚年" in age_range:
                summary["晚年运势"]["原文"] = original_text
                summary["晚年运势"]["解释"] = explanation
                if aspects:
                    summary["晚年运势"]["各方面"] = aspects

            # 收集建议和禁忌
            if "建议" in match:
                summary["建议"].append(match["建议"])

            if "禁忌" in match:
                summary["禁忌"].extend(match["禁忌"])

            if "性格分析" in match:
                summary["性格特点"].append(match["性格分析"])

        # 生成总体评价
        total_matches = len(matched_results)
        if total_matches > 0:
            book_name = matched_results[0].get('古籍', '古籍')
            summary["总体评价"] = "根据《{}》等古籍分析，共有{}项特征匹配".format(book_name, total_matches)
        else:
            summary["总体评价"] = "知识库匹配不足，建议使用基础分析"

        # 去重
        summary["建议"] = list(set(summary["建议"]))
        summary["禁忌"] = list(set(summary["禁忌"]))

        return summary


# ============================================================================
# 便捷函数
# ============================================================================

def detect_face_features(image_input: str, gender: str = "female",
                        use_enhanced_report: bool = True, use_llm: bool = True) -> Dict:
    """
    检测人脸特征（便捷函数）

    Args:
        image_input: 图片输入，支持以下格式：
            - 文件路径（字符串）
            - Base64 编码的图片数据（字符串）
            - Data URL 格式（data:image/jpeg;base64,...）
        gender: 性别 (male/female)
        use_enhanced_report: 是否使用增强版报告生成器
        use_llm: 是否使用LLM生成报告（默认True，更有人情味）

    Returns:
        完整的检测结果
    """
    # 调试日志
    print(f"[DEBUG] detect_face_features 调用 - use_enhanced_report={use_enhanced_report}, use_llm={use_llm}")

    try:
        # 创建检测器
        detector = FaceFeatureDetector()

        # 检测
        result = detector.detect(image_input)

        if "error" in result:
            return result

        # 匹配知识库
        matcher = KnowledgeBaseMatcher()
        match = matcher.match_face_features(result["features"], gender)

        # 如果需要增强报告，生成详细文本报告
        if use_enhanced_report:
            from vision.report_generator import generate_enhanced_report
            enhanced_report = generate_enhanced_report({
                "features": result["features"],
                "measurements": result["measurements"],
                "match": match
            }, gender, use_llm=use_llm)

            return {
                "success": True,
                "detection": result,
                "match": match,
                "enhanced_report": enhanced_report
            }
        else:
            return {
                "success": True,
                "detection": result,
                "match": match
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def detect_palm_features(image_path: str, hand: str = "right") -> Dict:
    """
    检测手掌特征（便捷函数）

    Args:
        image_path: 图片路径
        hand: left 或 right

    Returns:
        完整的检测结果
    """
    try:
        # 创建检测器
        detector = PalmFeatureDetector()

        # 检测
        result = detector.detect(image_path, hand)

        if "error" in result:
            return result

        # 匹配知识库
        matcher = KnowledgeBaseMatcher()
        match = matcher.match_palm_features(result)

        return {
            "success": True,
            "detection": result,
            "match": match
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("图像识别模块 - MediaPipe 新 API")
    print("=" * 50)

    # 测试模型下载
    downloader = ModelDownloader()
    results = downloader.download_all_models()

    for model_name, path in results.items():
        if path:
            print(f"✅ {model_name}: {path}")
        else:
            print(f"❌ {model_name}: 下载失败")
