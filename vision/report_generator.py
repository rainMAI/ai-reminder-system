"""
面相分析报告生成器 - 参考传统古籍和 Grok 风格
生成详细、生动、专业的面相分析报告
支持LLM（Qwen）生成更具情绪价值的报告
"""

from typing import Dict, List, Optional
from datetime import datetime
import json


class FaceReportGenerator:
    """面相分析报告生成器"""

    # 传统术语映射
    TRADITIONAL_TERMS = {
        "forehead": {
            "names": ["天庭", "天庭饱满", "天中", "司空"],
            "meaning": "早年运势、智慧、祖荫",
            "age_range": "早年运势（0-15岁阶段）",
            "palace": "命宫"
        },
        "eyebrows": {
            "names": ["司空", "眉毛", "兄弟宫"],
            "meaning": "性格、兄弟缘、人际",
            "age_range": "青年运势（15-30岁阶段）",
            "palace": "兄弟宫"
        },
        "eyes": {
            "names": ["中阳", "太阳", "眼睛", "夫妻宫"],
            "meaning": "智慧、情感、异性缘",
            "age_range": "壮年运势（30-40岁阶段）",
            "palace": "夫妻宫"
        },
        "nose": {
            "names": ["财帛", "中岳", "鼻子", "财帛宫"],
            "meaning": "财运、事业、意志",
            "age_range": "中年运势（35-50岁阶段）",
            "palace": "财帛宫"
        },
        "mouth": {
            "names": ["下停", "水星", "嘴巴", "子女宫"],
            "meaning": "表达、子女、晚运",
            "age_range": "晚年前期（45-60岁阶段）",
            "palace": "子女宫"
        },
        "chin": {
            "names": ["地阁", "下庭", "下巴", "奴仆宫"],
            "meaning": "晚运、下属、不动产",
            "age_range": "晚年运势（50岁以后阶段）",
            "palace": "奴仆宫"
        }
    }

    # 格局判断模板
    PATTERNS = {
        "excellent": {
            "name": "天生的富贵格",
            "description": "五岳三停匀称，五官端正，先天福气极厚",
            "ancient": "五岳朝归，官职显荣；三停平等，富贵终生"
        },
        "good": {
            "name": "兴旺格",
            "description": "五官端正，骨骼清秀，未来可期",
            "ancient": "五官端正，福寿双全；骨骼清秀，富贵可期"
        },
        "normal": {
            "name": "平稳格",
            "description": "中规中矩，平平淡淡才是真",
            "ancient": "相貌平平，勤俭持家，知足常乐"
        }
    }

    def __init__(self, use_llm: bool = True):
        """
        初始化报告生成器

        Args:
            use_llm: 是否使用LLM生成报告（默认True）
        """
        self.ancient_quotes = self._load_ancient_quotes()
        self.use_llm = use_llm

        # 延迟导入LLM客户端（只在需要时）
        self.llm_client = None
        if use_llm:
            try:
                from vision.llm_client import get_llm_client
                self.llm_client = get_llm_client()
                if self.llm_client.is_available():
                    print("✅ LLM已启用，将生成更有温度的报告")
                else:
                    print("⚠️  LLM未配置，将使用模板生成报告")
                    self.llm_client = None
            except Exception as e:
                print(f"⚠️  LLM加载失败: {e}，将使用模板生成报告")
                self.llm_client = None

    def _load_ancient_quotes(self) -> Dict:
        """加载古籍名言"""
        return {
            "child": {
                # 综合类
                "excellent_overall": "幼童额阔眼有神，鼻准圆隆福禄真；若得此相生富家，读书必中做高官。",
                "good_overall": "头圆额广，聪明伶俐；五官端正，福寿双全。",
                "normal_overall": "相貌虽平，勤能补拙；教养得法，亦可成材。",

                # 额头（天庭）
                "forehead_excellent": "天庭饱满，早年得志；发际整齐，聪明睿智。",
                "forehead_good": "额宽而广，聪明伶俐；额高而饱满，学业有成。",
                "forehind_promising": "幼童额阔，祖上有德；早年读书，必是高材。",

                # 眼睛
                "eyes_excellent": "眼有神而聪明，眼明亮而智慧；目大而光者，富贵之相。",
                "eyes_good": "眼如点漆，聪慧过人；眼神清亮，读书极好。",
                "eyes_promising": "眼睛明亮有神，智慧过人；眼神清澈，前程似锦。",

                # 眉毛
                "eyebrows_good": "眉清目秀，聪慧过人；眉尾上扬，贵人相助。",
                "eyebrows_gentle": "眉毛清秀，性格温和；眉形整齐，懂事有礼。",

                # 鼻子
                "nose_excellent": "鼻如悬胆，必家财万贯；鼻准丰隆，富贵双全。",
                "nose_good": "鼻如截筒，衣食不缺；鼻梁挺直，意志坚定。",
                "nose_promising": "鼻头圆润有肉，财帛宫旺；鼻梁挺直，性格稳重。",

                # 嘴巴
                "mouth_good": "唇红齿白，口才极佳；嘴角上扬，性格乐观。",
                "mouth_lucky": "口如含丹，能言善辩；嘴型端正，待人诚恳。",

                # 下巴
                "chin_good": "地阁方圆，晚景优游；下巴有肉，富足无忧。",
                "chin_promising": "下巴圆厚，晚年有福；地阁饱满，子女孝顺。",

                # 耳朵
                "ears_good": "耳白于面，聪明异常；耳垂饱满，福气深厚。",

                # 气色
                "complexion_good": "面如冠玉，富贵之相；皮肤白嫩，先天福气。",
                "qi_good": "气色红润，身体健康；神采奕奕，活力四射。"
            },
            "general": {
                "forehead_good": "天庭饱满，早年得志",
                "forehead_bad": "天庭狭窄，早年艰辛",
                "nose_good": "鼻如悬胆，必家财万贯",
                "eyes_good": "眼如点漆，聪慧过人"
            }
        }

    def generate_report(self, detection_result: Dict, gender: str = "female",
                       use_llm: Optional[bool] = None) -> str:
        """
        生成面相分析报告

        Args:
            detection_result: 检测结果
            gender: 性别
            use_llm: 是否使用LLM（None则使用初始化时的设置）

        Returns:
            格式化的报告文本
        """
        features = detection_result.get("features", {})
        measurements = detection_result.get("measurements", {})
        match_results = detection_result.get("match", {})

        # 判断是否使用LLM
        should_use_llm = use_llm if use_llm is not None else self.use_llm

        # 如果LLM可用且启用，使用LLM生成报告
        if should_use_llm and self.llm_client:
            is_child = self._is_child_face(measurements)
            llm_report = self.llm_client.generate_face_report(
                detection_result, match_results, gender, is_child
            )
            if llm_report:
                # LLM生成成功，添加标题并返回
                return self._format_llm_report(llm_report, is_child)

        # 否则使用模板生成报告
        is_child = self._is_child_face(measurements)
        if is_child:
            return self._generate_child_report(features, measurements, match_results, gender)
        else:
            return self._generate_adult_report(features, measurements, match_results, gender)

    def generate_report_streaming(self, detection_result: Dict, gender: str = "female",
                                   use_llm: Optional[bool] = None):
        """
        生成面相分析报告（流式输出）

        Args:
            detection_result: 检测结果
            gender: 性别
            use_llm: 是否使用LLM（None则使用初始化时的设置）

        Yields:
            报告的文本片段
        """
        features = detection_result.get("features", {})
        measurements = detection_result.get("measurements", {})
        match_results = detection_result.get("match", {})

        # 判断是否使用LLM
        should_use_llm = use_llm if use_llm is not None else self.use_llm

        # 先发送报告标题
        is_child = self._is_child_face(measurements)
        lines = []
        if is_child:
            lines.append("# 🌟 儿童面相分析报告")
        else:
            lines.append("# 🌟 面相分析报告")
        lines.append("")
        lines.append(f"> 分析时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        yield "\n".join(lines)

        # 如果LLM可用且启用，使用LLM生成报告
        if should_use_llm and self.llm_client:
            # 构建提示词
            is_child = self._is_child_face(measurements)
            user_prompt = self._build_prompt(detection_result, match_results, gender, is_child)

            # 使用流式生成
            system_prompt = self.llm_client._get_child_system_prompt() if is_child else self.llm_client._get_adult_system_prompt()

            for chunk in self.llm_client.generate_streaming(user_prompt, system_prompt):
                yield chunk
        else:
            # 使用模板生成（一次性返回）
            if is_child:
                report = self._generate_child_report(features, measurements, match_results, gender)
            else:
                report = self._generate_adult_report(features, measurements, match_results, gender)
            yield report

    def _format_llm_report(self, llm_report: str, is_child: bool) -> str:
        """格式化LLM生成的报告"""
        lines = []
        if is_child:
            lines.append("# 🌟 儿童面相分析报告")
        else:
            lines.append("# 🌟 面相分析报告")
        lines.append("")
        lines.append(f"> 分析时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(llm_report)
        return "\n".join(lines)

    def _is_child_face(self, measurements: Dict) -> bool:
        """判断是否是儿童面相

        判断依据：
        1. 额头比例较大（儿童额头占面部比例约35-40%）
        2. 面部整体较小
        3. 下巴较圆（儿童下巴未发育完全）
        """
        # 检查额头比例（儿童额头通常占35%以上）
        forehead_ratio = measurements.get("forehead", {}).get("ratio", 0.3)

        # 检查脸型比例
        face_ratio = measurements.get("face", {}).get("shape_ratio", 1.3)

        # 儿童特征：
        # 1. 额头比例大（>=0.32）
        # 2. 脸型偏圆（face_ratio较小，<1.35）
        is_forehead_large = forehead_ratio >= 0.32
        is_face_round = face_ratio < 1.35

        # 综合判断
        if is_forehead_large and is_face_round:
            return True

        # 如果额头比例特别大，也判断为儿童
        if forehead_ratio >= 0.35:
            return True

        return False

    def _generate_child_report(self, features: Dict, measurements: Dict,
                               match_results: Dict, gender: str) -> str:
        """生成儿童面相报告"""
        report_parts = []

        # 标题
        report_parts.append("=" * 70)
        report_parts.append("【儿童面相分析报告】")
        report_parts.append("=" * 70)
        report_parts.append("")

        # 一、整体格局
        report_parts.append("一、整体格局判断")
        report_parts.append("-" * 70)
        pattern = self._judge_pattern(features)
        report_parts.append(f"**格局类型**: {pattern['name']}")
        report_parts.append(f"**特征描述**: {pattern['description']}")
        report_parts.append(f"**古籍引用**: 「{pattern['ancient']}」")
        report_parts.append("")

        # 二、各部位详解
        report_parts.append("二、各部位详解")
        report_parts.append("-" * 70)

        # 1. 天庭（额头）
        forehead = features.get("forehead", "")
        if forehead:
            report_parts.extend(self._analyze_forehead_child(forehead))

        # 2. 眉毛（需要从图像检测）
        report_parts.extend(self._analyze_eyebrows_child())

        # 3. 眼睛
        eyes = features.get("eyes", "")
        if eyes:
            report_parts.extend(self._analyze_eyes_child(eyes))

        # 4. 鼻子
        nose = features.get("nose", "")
        if nose:
            report_parts.extend(self._analyze_nose_child(nose))

        # 5. 下巴
        face_shape = features.get("face_shape", "")
        report_parts.extend(self._analyze_chin_child(face_shape))

        # 三、综合结论
        report_parts.append("")
        report_parts.append("三、综合结论与建议")
        report_parts.append("-" * 70)
        report_parts.extend(self._generate_child_conclusion(features, match_results))

        return "\n".join(report_parts)

    def _generate_adult_report(self, features: Dict, measurements: Dict,
                               match_results: Dict, gender: str) -> str:
        """生成成人面相报告"""
        report_parts = []

        # 标题
        report_parts.append("=" * 70)
        report_parts.append("【面相分析报告】")
        report_parts.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_parts.append("=" * 70)
        report_parts.append("")

        # 一、整体格局
        report_parts.append("一、整体格局")
        report_parts.append("-" * 70)
        pattern = self._judge_pattern(features)
        report_parts.append(f"**整体格局**: {pattern['name']}")
        report_parts.append(f"**详细说明**: {pattern['description']}")
        report_parts.append(f"**古籍原文**: 「{pattern['ancient']}」")
        report_parts.append("")

        # 二、各部位详解（五宫分析）
        report_parts.append("二、五官详解（十二宫位分析）")
        report_parts.append("-" * 70)

        # 1. 天庭（额头）- 命宫
        forehead = features.get("forehead", "")
        if forehead:
            report_parts.extend(self._analyze_forehead(forehead, match_results))

        # 2. 眉毛 - 兄弟宫
        report_parts.extend(self._analyze_eyebrows(match_results))

        # 3. 眼睛 - 夫妻宫/监察官
        eyes = features.get("eyes", "")
        if eyes:
            report_parts.extend(self._analyze_eyes(eyes, match_results))

        # 4. 鼻子 - 财帛宫
        nose = features.get("nose", "")
        if nose:
            report_parts.extend(self._analyze_nose(nose, match_results))

        # 5. 嘴巴和下巴 - 子女宫/奴仆宫
        mouth = features.get("mouth", "")
        face_shape = features.get("face_shape", "")
        report_parts.extend(self._analyze_mouth_chin(mouth, face_shape, match_results))

        # 三、性格与运势
        report_parts.append("")
        report_parts.append("三、性格与运势分析")
        report_parts.append("-" * 70)
        report_parts.extend(self._analyze_personality_fortune(features, match_results))

        # 四、古籍引用
        report_parts.append("")
        report_parts.append("四、古籍引用与解读")
        report_parts.append("-" * 70)
        report_parts.extend(self._generate_ancient_references(match_results))

        # 五、综合建议
        report_parts.append("")
        report_parts.append("五、综合建议")
        report_parts.append("-" * 70)
        report_parts.extend(self._generate_suggestions(features, match_results))

        return "\n".join(report_parts)

    def _judge_pattern(self, features: Dict) -> Dict:
        """判断格局"""
        # 简化版判断
        excellent_count = 0
        good_count = 0

        if features.get("forehead") == "饱满":
            excellent_count += 1
        if features.get("eyes") in ["大眼", "明亮"]:
            excellent_count += 1
        if features.get("nose") in ["高挺", "适中"]:
            excellent_count += 1

        if excellent_count >= 2:
            return self.PATTERNS["excellent"]
        elif excellent_count >= 1:
            return self.PATTERNS["good"]
        else:
            return self.PATTERNS["normal"]

    def _analyze_forehead(self, forehead: str, match_results: Dict) -> List[str]:
        """分析额头（天庭）"""
        parts = []
        terms = self.TRADITIONAL_TERMS["forehead"]

        parts.append(f"**1. 天庭（额头）- 命宫**")
        parts.append(f"- 传统术语：{', '.join(terms['names'])}")
        parts.append(f"- 所主：{terms['meaning']}")
        parts.append(f"- 年龄段：{terms['age_range']}")
        parts.append("")

        # 检测结果
        if forehead == "饱满":
            parts.append(f"✨ **检测结果**: 额头{forehead}")
            parts.append("")
            parts.append("→ **先天优势**:")
            parts.append("  - 您的额头饱满宽阔，这是很好的面相特征")
            parts.append("  - 祖上荫庇深厚，父母应该是有能力或有地位的人")
            parts.append("  - 早年运势特别好，读书运好，上学那会儿基本顺风顺水")
            parts.append("  - 天生聪明，记性好，学东西比一般人快")
            parts.append("")
            parts.append("→ **古籍解读**: 「天庭饱满，早年得志；发际整齐，聪明睿智」")
        elif forehead == "狭窄":
            parts.append(f"⚠️  **检测结果**: 额头{forehead}")
            parts.append("")
            parts.append("→ **需要注意**:")
            parts.append("  - 早年运势可能稍微平淡一些，不过没关系")
            parts.append("  - 成长路上可能需要比别人多努力一点")
            parts.append("  - 建议先积累经验和人脉，不要急着创业")
            parts.append("  - 虽然起步慢点，但只要坚持，中年之后运势就会上来")
            parts.append("")
            parts.append("→ **古籍解读**: 「天庭狭窄，早年艰辛；勤能补拙，晚景必丰」")

        parts.append("")
        return parts

    def _analyze_eyebrows(self, match_results: Dict) -> List[str]:
        """分析眉毛"""
        parts = []
        terms = self.TRADITIONAL_TERMS["eyebrows"]

        parts.append(f"**2. 司空（眉毛）- 兄弟宫**")
        parts.append(f"- 传统术语：{', '.join(terms['names'])}")
        parts.append(f"- 所主：{terms['meaning']}")
        parts.append("")

        # 如果图像识别中有眉毛数据
        parts.append("→ **性格特点**: 眉形清秀、性格温和、人际关系和谐")
        parts.append("→ **人际运势**: 兄弟姐妹缘好，容易被长辈和老师喜欢")
        parts.append("")
        parts.append("→ **古籍解读**: 「眉清目秀，聪慧过人；眉尾上扬，贵人相助」")
        parts.append("")
        return parts

    def _analyze_eyes(self, eyes: str, match_results: Dict) -> List[str]:
        """分析眼睛"""
        parts = []
        terms = self.TRADITIONAL_TERMS["eyes"]

        parts.append(f"**3. 中阳（眼睛）- 夫妻宫**")
        parts.append(f"- 传统术语：{', '.join(terms['names'])}")
        parts.append(f"- 所主：{terms['meaning']}")
        parts.append("")

        if eyes == "大眼":
            parts.append(f"✨ **检测结果**: {eyes}")
            parts.append("")
            parts.append("→ **先天优势**:")
            parts.append("  - 您这双眼睛俗称'贵人眼''聪明眼'，是很好的特征")
            parts.append("  - 智商和情商都比较高，反应快，看问题准")
            parts.append("  - 记忆力好，学东西快，小时候读书应该不错")
            parts.append("  - 异性缘特别好，容易遇到优秀的另一半")
            parts.append("")
            parts.append("→ **古籍解读**: 「眼有神而聪明，眼明亮而智慧；目大而光者，富贵之相」")

        parts.append("")
        return parts

    def _analyze_nose(self, nose: str, match_results: Dict) -> List[str]:
        """分析鼻子"""
        parts = []
        terms = self.TRADITIONAL_TERMS["nose"]

        parts.append(f"**4. 财帛（鼻子）- 财帛宫**")
        parts.append(f"- 传统术语：{', '.join(terms['names'])}")
        parts.append(f"- 所主：{terms['meaning']}")
        parts.append("")

        if nose in ["高挺", "适中"]:
            parts.append(f"✨ **检测结果**: 鼻子{nose}")
            parts.append("")
            parts.append("→ **财运优势**:")
            parts.append("  - 您的鼻子长得不错，财帛宫旺盛")
            parts.append("  - 整体财运很好，赚钱能力比较强")
            parts.append("  - 30到50岁这二十年是您积累财富的黄金期")
            parts.append("  - 很会理财管钱，适合经商或者做投资")
            parts.append("")
            parts.append("→ **性格特点**: 性格比较稳重，做事有主见，意志坚定")
            parts.append("")
            parts.append("→ **古籍解读**: 「鼻如悬胆，必家财万贯；鼻准丰隆，富贵双全」")

        parts.append("")
        return parts

    def _analyze_mouth_chin(self, mouth: str, face_shape: str, match_results: Dict) -> List[str]:
        """分析嘴巴和下巴"""
        parts = []

        parts.append(f"**5. 地阁（下巴）- 奴仆宫**")
        parts.append(f"- 传统术语：地阁、下庭、下巴")
        parts.append(f"- 所主：晚年运、子女、不动产")
        parts.append("")

        if face_shape == "圆脸":
            parts.append(f"✨ **检测结果**: {face_shape}")
            parts.append("")
            parts.append("→ **晚年运势**:")
            parts.append("  - 您的下巴长得好，地阁圆厚")
            parts.append("  - 晚年运势特别好，50岁以后越过越顺")
            parts.append("  - 老了以后有房有产，社会地位也不错")
            parts.append("  - 子女孝顺，家庭和睦，享受天伦之乐")
            parts.append("")
            parts.append("→ **性格特点**: 为人随和，人缘好，心胸宽广不计较")

        parts.append("")
        parts.append("→ **古籍解读**: 「地阁方圆，晚景优游；下巴有肉，富足无忧」")
        parts.append("")
        return parts

    def _analyze_forehead_child(self, forehead: str) -> List[str]:
        """分析儿童额头"""
        parts = []
        parts.append(f"**1. 天庭（额头）- 早年运、智慧**")
        parts.append("")

        if forehead == "饱满":
            parts.append("✨ **检测结果**: 额头宽阔饱满、光洁圆润")
            parts.append("")
            parts.append("→ **先天优势**:")
            parts.append("  - 祖上荫庇极厚，父母有能力或地位")
            parts.append("  - 早年（0-15岁）顺风顺水，读书运极佳")
            parts.append("  - 天生聪明，记忆力强，考名校概率高")
            parts.append("")
            parts.append("→ **古籍引用**: 「幼童额阔眼有神，鼻准圆隆福禄真」")
        elif forehead == "狭窄":
            parts.append("⚠️  **检测结果**: 额头较窄")
            parts.append("")
            parts.append("→ **需要注意**:")
            parts.append("  - 早年需要更多努力，不宜太早定目标")
            parts.append("  - 但天庭虽窄，只要读书勤奋，也能成材")
            parts.append("")
            parts.append("→ **建议**: 后天努力可以改变命运")

        parts.append("")
        return parts

    def _analyze_eyebrows_child(self) -> List[str]:
        """分析儿童眉毛"""
        parts = []
        parts.append(f"**2. 司空（眉毛）- 性格、人际**")
        parts.append("")
        parts.append("→ **性格特点**: 温和懂事、有教养、不爱争斗")
        parts.append("→ **人际优势**: 人缘极佳，从小讨老师和长辈喜欢")
        parts.append("→ **兄弟姐妹**: 兄弟姐妹缘好，家庭和睦")
        parts.append("")
        return parts

    def _analyze_eyes_child(self, eyes: str) -> List[str]:
        """分析儿童眼睛"""
        parts = []
        parts.append(f"**3. 中阳（眼睛）- 智慧、情感**")
        parts.append("")

        if eyes == "大眼":
            parts.append("✨ **检测结果**: 眼睛偏大、黑仁明亮、眼神干净有神")
            parts.append("")
            parts.append("→ **先天优势**:")
            parts.append("  - 典型的'贵人眼''聪明眼'")
            parts.append("  - 智慧高、情商高、反应快")
            parts.append("  - 长大后异性缘极好，容易遇到优秀对象")
            parts.append("")
            parts.append("→ **古籍引用**: 「眼有神而聪明，眼明亮而智慧」")

        parts.append("")
        return parts

    def _analyze_nose_child(self, nose: str) -> List[str]:
        """分析儿童鼻子"""
        parts = []
        parts.append(f"**4. 财帛（鼻子）- 财运、事业**")
        parts.append("")

        if nose in ["高挺", "适中"]:
            parts.append("✨ **检测结果**: 鼻梁挺直、鼻头圆润有肉")
            parts.append("")
            parts.append("→ **财运预示**:")
            parts.append("  - 财帛宫极旺，家里条件只会越来越好")
            parts.append("  - 自己30-50岁财运最旺")
            parts.append("  - 性格稳重、有主见、很会管钱")
            parts.append("")
            parts.append("→ **古籍引用**: 「鼻如截筒，衣食不缺」")

        parts.append("")
        return parts

    def _analyze_chin_child(self, face_shape: str) -> List[str]:
        """分析儿童下巴"""
        parts = []
        parts.append(f"**5. 地阁（下巴）- 晚年运、子女**")
        parts.append("")

        if face_shape == "圆脸":
            parts.append("✨ **检测结果**: 下巴圆厚、双腮饱满")
            parts.append("")
            parts.append("→ **晚年运预示**:")
            parts.append("  - 晚年运极佳，50岁后有房有产")
            parts.append("  - 社会地位高，受人尊敬")
            parts.append("  - 身体健康，寿命长")
            parts.append("")
            parts.append("→ **古籍引用**: 「地阁方圆，晚景优游」")

        parts.append("")
        return parts

    def _analyze_personality_fortune(self, features: Dict, match_results: Dict) -> List[str]:
        """分析性格与运势"""
        parts = []

        # 性格特点
        parts.append("**性格特点**")
        if features.get("eyes") == "大眼":
            parts.append("- 您是个聪明人，反应快，看问题比较准")
            parts.append("- 记忆力不错，学东西快，适应能力强")
        if features.get("nose") in ["高挺", "适中"]:
            parts.append("- 性格比较稳重，做事有主见不摇摆")
            parts.append("- 意志坚定，认准了的事就会坚持到底")
        if features.get("face_shape") == "圆脸":
            parts.append("- 为人随和好相处，人缘不错")
            parts.append("- 心胸宽广，不爱斤斤计较，看得开")
        parts.append("")

        # 事业运势
        parts.append("**事业运势**")
        parts.append("- 35到50岁这十几年是您事业发展的黄金期")
        parts.append("- 人际关系比较和谐，身边会有一些贵人帮衬")
        parts.append("- 适合往管理方向发展，或者自己创业")
        parts.append("")

        # 财富运势
        parts.append("**财富运势**")
        parts.append("- 整体财运不错，赚钱能力比较强")
        parts.append("- 很会管钱理财，适合做些投资")
        parts.append("- 建议多积累财富，为晚年做准备")
        parts.append("")

        return parts

    def _generate_ancient_references(self, match_results: Dict) -> List[str]:
        """生成古籍引用"""
        parts = []

        matched = match_results.get("matched_features", [])
        if matched:
            for i, match in enumerate(matched[:3], 1):
                parts.append(f"**引用 {i}: 《{match['古籍']}》- {match['部位']}**")
                parts.append(f"- 古籍原文: 「{match['原文']}」")
                parts.append(f"- 白话解读: {match['现代解释']}")
                parts.append("")

        return parts

    def _generate_suggestions(self, features: Dict, match_results: Dict) -> List[str]:
        """生成综合建议"""
        parts = []

        # 判断整体格局
        pattern = self._judge_pattern(features)

        if pattern == self.PATTERNS["excellent"]:
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("✨ **整体评价**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("总的来说，您的面相真的很好！😊")
            parts.append("从传统面相学的角度看，您属于'富贵格'，先天底子厚，")
            parts.append("后天运势也不错。不管做什么事情，只要用心，都能有所成就。")
            parts.append("")
            parts.append("**发挥优势**:")
            parts.append("- 您很聪明，学东西快，可以多学习提升自己")
            parts.append("- 中年（35-50岁）是您最旺的时候，把握机会")
            parts.append("- 财运不错，可以适当做些投资理财")
            parts.append("- 人缘好，多结交有价值的朋友")
            parts.append("")

            parts.append("**温馨提示**:")
            parts.append("- 运势好也要努力，不能只靠运气")
            parts.append("- 注意身体健康，身体是本钱")
            parts.append("- 多关心家人，家庭和睦最重要")
            parts.append("")

            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🌟 **祝福语**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("祝您：一生平安，事业有成，家庭幸福，财源广进！✨")
            parts.append("")

        elif pattern == self.PATTERNS["good"]:
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🌱 **整体评价**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("您的面相整体不错，属于'兴旺格'。😊")
            parts.append("虽然不是大富大贵的那种，但踏踏实实走下去，未来一定不会差。")
            parts.append("")
            parts.append("**发挥优势**:")
            parts.append("- 您性格稳重，做事踏实，这是很大的优点")
            parts.append("- 中年之后运势会越来越好，要有耐心")
            parts.append("- 建议先积累经验，再寻求突破")
            parts.append("- 保持好心态，心态决定一切")
            parts.append("")

            parts.append("**温馨提示**:")
            summary = match_results.get("summary", {})
            if summary.get("禁忌"):
                parts.append("- 需要注意的地方:")
                for taboo in summary["禁忌"][:3]:
                    parts.append(f"  • {taboo}")
            parts.append("- 坚持努力，不要轻言放弃")
            parts.append("- 多学习提升自己，机会留给有准备的人")
            parts.append("")

            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("💪 **祝福语**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("祝您：稳步前进，越来越好，心想事成！💪")
            parts.append("")

        else:  # normal pattern
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🌿 **整体评价**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("您的面相整体中规中矩，这其实也很正常。😊")
            parts.append("面相只是参考，后天的努力和选择才是最关键的。")
            parts.append("很多人凭着自己的努力，一样取得了很好的成就。")
            parts.append("")
            parts.append("**发展建议**:")
            parts.append("- 建议走专业技术路线，学一门过硬的手艺")
            parts.append("- 性格可塑性强，多培养自己的优点")
            parts.append("- 保持积极心态，心态好什么都好")
            parts.append("- 小富即安也是一种福气，知足常乐")
            parts.append("")

            parts.append("**温馨提示**:")
            parts.append("- 不要和别人比，和自己比就好")
            parts.append("- 努力提升自己，机会总会有的")
            parts.append("- 健康平安最重要，其他都是浮云")
            parts.append("")

            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🙏 **祝福语**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("祝您：平平安安，健健康康，知足常乐！❤️")
            parts.append("")

        return parts

    def _generate_child_conclusion(self, features: Dict, match_results: Dict) -> List[str]:
        """生成儿童综合结论"""
        parts = []

        pattern = self._judge_pattern(features)

        # 根据格局生成不同风格的结论
        if pattern == self.PATTERNS["excellent"]:
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("💫 **给家长的话**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("看到这张照片，第一感觉就是：这孩子真有福气！😊")
            parts.append("")
            parts.append("从传统面相学的角度看，这孩子天生底子就很好，属于那种")
            parts.append("'从小到老都让人羡慕'的小贵人相。怎么说呢...")
            parts.append("")
            parts.append("📚 **读书学习这块儿**")
            parts.append("孩子特别聪明，记性好，学东西快。读书这条路上基本")
            parts.append("不用太操心，稍微用点心就能上好学校。您做家长的，")
            parts.append("主要是给他/她创造个好环境，别让孩子压力太大。")
            parts.append("")
            parts.append("🌟 **性格方面**")
            parts.append("这孩子性格好，懂事、阳光、讨人喜欢。从小就能看出来，")
            parts.append("老师、长辈都会特别喜欢。以后长大了，人缘也差不了。")
            parts.append("")
            parts.append("💰 **财运事业**")
            parts.append("家里条件不错，孩子自己长大后也有财运。30到50岁是他/她")
            parts.append("最旺的时候，不管从商还是从政，都能有一番成就。")
            parts.append("")
            parts.append("💕 **感情婚姻**")
            parts.append("长大后容易找到门当户对、又漂亮/帅气又贤惠/体贴的伴侣，")
            parts.append("感情生活会很幸福。")
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🎊 **一句话总结**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("恭喜您！这孩子是天生的'兴家格'，是能给家族带来荣耀的。")
            parts.append("")
            parts.append("未来路很多，随便选：")
            parts.append("• 读书 → 名校毕业，高管或科学家")
            parts.append("• 经商 → 自己当老板，事业有成")
            parts.append("• 继承家业 → 富三代起步，越做越大")
            parts.append("")
            parts.append("反正这孩子这辈子，跟'穷'字基本无关～ 😄")
            parts.append("")
            parts.append("好好培养就行，记住：轻松一点，快乐成长！")
            parts.append("")

        elif pattern == self.PATTERNS["good"]:
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🌱 **给家长的话**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("这孩子整体来说底子不错，未来可期！😊")
            parts.append("")
            parts.append("📚 **读书学习**")
            parts.append("孩子聪明程度中等偏上，读书需要一点努力，但只要用功，")
            parts.append("成绩不会差。建议从小培养好的学习习惯。")
            parts.append("")
            parts.append("🌟 **性格发展**")
            parts.append("性格总体温和，人际关系应该不错。多鼓励孩子参加集体活动，")
            parts.append("锻炼社交能力。")
            parts.append("")
            parts.append("💰 **未来前景**")
            parts.append("中年后运势会起来，35-50岁是黄金期。前期多积累经验人脉，")
            parts.append("后期会有不错的成就。")
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("💪 **一句话总结**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("这孩子属于'稳中向好'的类型，虽然不是大富大贵的那种，")
            parts.append("但踏踏实实走下去，未来一定不会差！")
            parts.append("")
            parts.append("建议：多关注教育，培养良好的习惯，孩子会有出息的！💪")
            parts.append("")

        else:  # normal pattern
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🌿 **给家长的话**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("每个孩子都是独一无二的宝贝，这张照片显示孩子整体中规中矩，")
            parts.append("但这不代表未来就不好！😊")
            parts.append("")
            parts.append("📚 **读书学习**")
            parts.append("可能需要比别人多努力一点，但'勤能补拙'是千古真理。")
            parts.append("很多成功人士小时候都不是最聪明的，但都是最努力的。")
            parts.append("")
            parts.append("🌟 **性格培养**")
            parts.append("性格方面可塑性强，家长多引导、多鼓励，培养孩子的自信心，")
            parts.append("这比什么都重要。")
            parts.append("")
            parts.append("💰 **未来建议**")
            parts.append("建议走专业技术路线，学一门过硬的手艺或专业。")
            parts.append("虽然大富大难，但小富即安，平平安安也是一种福气。")
            parts.append("")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("🙏 **一句话总结**")
            parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            parts.append("")
            parts.append("记住：面相只是参考，后天的努力和教育才是最关键的！")
            parts.append("")
            parts.append("好好爱孩子，多鼓励、多陪伴，健康快乐成长比什么都重要！❤️")
            parts.append("")

        return parts


def generate_enhanced_report(detection_result: Dict, gender: str = "female",
                           is_child: bool = False, use_llm: bool = True) -> str:
    """
    生成增强的面相分析报告

    Args:
        detection_result: 检测结果
        gender: 性别
        is_child: 是否是儿童
        use_llm: 是否使用LLM生成报告（默认True，更有人情味）

    Returns:
        格式化的报告文本
    """
    generator = FaceReportGenerator(use_llm=use_llm)
    return generator.generate_report(detection_result, gender)
