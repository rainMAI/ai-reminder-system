"""
LLM客户端 - 支持调用Deepseek等大模型生成面相分析报告
提供情绪价值和正能量
"""

import os
import json
from typing import Optional, Dict, Any
from openai import OpenAI


class LLMClient:
    """LLM客户端,支持调用Deepseek等大模型"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        """
        初始化LLM客户端

        Args:
            api_key: API密钥（默认从环境变量读取）
            base_url: API地址（默认从环境变量读取）
            model: 模型名称（默认从环境变量读取）
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")

        # 初始化OpenAI客户端
        self.client = None

        # 检查配置
        if not self.api_key:
            print("⚠️  警告: 未配置LLM_API_KEY,LLM功能将不可用")
        else:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                print(f"✅ LLM客户端初始化成功 (model: {self.model})")
            except Exception as e:
                print(f"⚠️  LLM客户端初始化失败: {e}")

    def is_available(self) -> bool:
        """检查LLM是否可用"""
        return self.client is not None

    def generate(self, prompt: str, system_prompt: str = None,
                 temperature: float = 0.7, max_tokens: int = 3500) -> Optional[str]:
        """
        调用LLM生成文本

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数（0-1,越高越随机）
            max_tokens: 最大token数

        Returns:
            生成的文本,失败返回None
        """
        if not self.is_available():
            print("⚠️  LLM客户端未初始化")
            return None

        try:
            # 构建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # 【DEBUG】打印prompt到控制台和文件
            print("=" * 70)
            print("【DEBUG】发送给LLM的System Prompt:")
            print("=" * 70)
            print(system_prompt if system_prompt else "(无)")
            print()
            print("=" * 70)
            print("【DEBUG】发送给LLM的User Prompt:")
            print("=" * 70)
            print(prompt)
            print("=" * 70)
            print()

            # 保存到文件方便调试
            with open("d:/code/test/mcp-fortune/llm_debug_log.txt", "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 70 + "\n")
                f.write(f"Temperature: {temperature}\n")
                f.write(f"Max Tokens: {max_tokens}\n")
                f.write("-" * 70 + "\n")
                f.write("SYSTEM PROMPT:\n")
                f.write(system_prompt if system_prompt else "(无)\n")
                f.write("-" * 70 + "\n")
                f.write("USER PROMPT:\n")
                f.write(prompt + "\n")
                f.write("=" * 70 + "\n\n")

            # 调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            # 返回结果
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                print("⚠️  LLM返回结果为空")
                return None

        except Exception as e:
            print(f"⚠️  LLM调用出错: {e}")
            return None

    def generate_streaming(self, prompt: str, system_prompt: str = None,
                          temperature: float = 0.7, max_tokens: int = 1500):
        """
        调用LLM生成文本（流式输出）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数（0-1,越高越随机）
            max_tokens: 最大token数

        Yields:
            生成的文本片段
        """
        if not self.is_available():
            print("⚠️  LLM客户端未初始化")
            return

        try:
            # 构建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # 调用API（流式）
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True  # 启用流式
            )

            # 实时yield每个chunk
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content

        except Exception as e:
            print(f"⚠️  LLM流式调用出错: {e}")
            yield f"\n\n[错误:生成失败 - {str(e)}]"

    def generate_face_report(self, detection_result: Dict, knowledge_matches: Dict,
                            gender: str, is_child: bool = False) -> Optional[str]:
        """
        使用LLM生成面相分析报告

        Args:
            detection_result: 检测结果（features, measurements）
            knowledge_matches: 知识库匹配结果
            gender: 性别
            is_child: 是否是儿童

        Returns:
            生成的报告文本
        """
        # 构建系统提示词 - 强调情绪价值和正能量
        if is_child:
            system_prompt = self._get_child_system_prompt()
            user_prompt = self._build_child_prompt(detection_result, knowledge_matches, gender)
        else:
            system_prompt = self._get_adult_system_prompt()
            user_prompt = self._build_adult_prompt(detection_result, knowledge_matches, gender)

        # 【重要修改】提高temperature到0.95,让输出更随机、更有个性
        return self.generate(user_prompt, system_prompt, temperature=0.95, max_tokens=3500)

    def generate_face_report_streaming(self, detection_result: Dict, knowledge_matches: Dict,
                                      gender: str, is_child: bool = False):
        """
        使用LLM生成面相分析报告（流式输出）

        Args:
            detection_result: 检测结果（features, measurements）
            knowledge_matches: 知识库匹配结果
            gender: 性别
            is_child: 是否是儿童

        Yields:
            报告的文本片段
        """
        # 构建系统提示词 - 强调情绪价值和正能量
        if is_child:
            system_prompt = self._get_child_system_prompt()
            user_prompt = self._build_child_prompt(detection_result, knowledge_matches, gender)
        else:
            system_prompt = self._get_adult_system_prompt()
            user_prompt = self._build_adult_prompt(detection_result, knowledge_matches, gender)

        # 流式生成报告（使用更高的temperature）
        for chunk in self.generate_streaming(user_prompt, system_prompt, temperature=0.95, max_tokens=3500):
            yield chunk

    def _get_child_system_prompt(self) -> str:
        """儿童面相分析的系统提示词 - 极简版"""
        return """你是一位充满爱心,经验丰富的面相师,专门分析儿童面相。

【最重要的原则】
1. **每份报告都必须独一无二!**
2. **语言要生动具体,避免套话**
   - 禁止说:"相貌端正"、"气质沉稳"、"五官端正"、"踏踏实实"
   - 要说具体描述,结合测量数据
3. **必须引用测量数据**

【报告结构】(自由发挥,不要照搬模板)
1. 开场白:第一印象+最显著特征+格局判断
2. 按部位分析:选择2-4个显著特征
3. 结论:总结+建议+祝福语(要个性化!)

记住:您是在为**具体的这个孩子**写报告,不是在填模板!"""

    def _get_adult_system_prompt(self) -> str:
        """成人面相分析的系统提示词 - 极简版"""
        return """你是一位专业,温暖,有智慧的面相师,擅长分析成人面相。

【最重要的原则】
1. **每份报告都必须独一无二!**
2. **语言要生动具体,避免套话**
   - 禁止说:"相貌端正"、"气质沉稳"、"五官端正"、"踏踏实实"
   - 要说具体描述,结合测量数据
3. **必须引用测量数据**

【报告结构】(自由发挥,不要照搬模板)
1. 开场白:第一印象+最显著特征+格局判断
2. 按部位分析:选择2-4个显著特征
3. 结论:总结+建议+祝福语(要个性化!)

记住:您是在为**具体的这个人**写报告,不是在填模板!"""

    def _build_child_prompt(self, detection_result: Dict, knowledge_matches: Dict,
                           gender: str) -> str:
        """构建儿童面相分析提示词 - 极简版"""
        features = detection_result.get("features", {})
        measurements = detection_result.get("measurements", {})

        gender_text = "小男孩" if gender == 'male' else "小女孩"

        # 转换测量数据为cm
        forehead_ratio = measurements.get("forehead", {}).get("ratio", 0.3)
        face_ratio = measurements.get("face", {}).get("shape_ratio", 1.3)

        # 根据额头比例判断年龄段
        if forehead_ratio >= 0.38:
            age_estimate = "3~6岁"
            face_width_cm = 9.5
        elif forehead_ratio >= 0.35:
            age_estimate = "7~10岁"
            face_width_cm = 10.5
        elif forehead_ratio >= 0.32:
            age_estimate = "11~14岁"
            face_width_cm = 11.5
        else:
            age_estimate = "15~18岁"
            face_width_cm = 12.5

        face_height_cm = face_width_cm * face_ratio

        # 三停高度
        middle_ratio = measurements.get("middle", {}).get("ratio", 0.35)
        lower_ratio = measurements.get("lower", {}).get("ratio", 0.35)

        forehead_cm = face_height_cm * forehead_ratio
        middle_cm = face_height_cm * middle_ratio
        lower_cm = face_height_cm * lower_ratio

        # 眼睛,鼻子,嘴巴的数据
        eyes_ratio = measurements.get("eyes", {}).get("left_ratio", 0.25)
        eye_width_cm = face_width_cm * eyes_ratio

        nose_ratio = measurements.get("nose", {}).get("ratio", 1.7)
        nose_length_cm = face_height_cm * 0.25
        nose_width_cm = nose_length_cm / nose_ratio if nose_ratio > 0 else 2.5

        mouth_ratio = measurements.get("mouth", {}).get("ratio", 0.35)
        mouth_width_cm = face_width_cm * mouth_ratio

        # 判断脸型
        if face_ratio < 1.2:
            face_type = "圆脸"
        elif face_ratio < 1.35:
            face_type = "椭圆脸"
        elif face_ratio < 1.5:
            face_type = "鹅蛋脸"
        else:
            face_type = "长脸"

        # 极简prompt - 只提供数据,不给格式
        prompt = f"""请为这位{gender_text}生成面相分析报告。

【检测数据】
年龄:{age_estimate} | 脸型:{face_type}
三停:上{forehead_ratio*100:.0f}% 中{middle_ratio*100:.0f}% 下{lower_ratio*100:.0f}%
五官:眼{eye_width_cm:.1f}cm 鼻{nose_length_cm:.1f}x{nose_width_cm:.1f}cm 嘴{mouth_width_cm:.1f}cm

特征:额头{features.get('forehead','')} 眼睛{features.get('eyes','')} 鼻子{features.get('nose','')}"""

        # 添加知识库匹配结果
        matched = knowledge_matches.get("matched_features", [])
        if matched:
            prompt += "\n\n【古籍参考】\n"
            # 按部位分组,避免重复
            parts_map = {}
            for match in matched[:8]:  # 最多取8条匹配
                part = match.get("部位", "")
                if part and part not in parts_map:
                    parts_map[part] = match

            for part, match in parts_map.items():
                source = match.get("古籍", "")
                original = match.get("原文", "")
                explanation = match.get("现代解释", "")
                if original and explanation:
                    prompt += f"• {part}:《{source}》「{original}」\n"
                    prompt += f"  解读: {explanation}\n"

            # 添加综合总结(如果有)
            summary = knowledge_matches.get("summary", {})
            if summary:
                pattern = summary.get("整体格局", "")
                if pattern:
                    prompt += f"\n整体格局: {pattern}\n"

        prompt += """
【要求】
开场白:根据数据特点创作,禁止用"相貌端正""气质沉稳""五官端正"
正文:按部位分析,引用数据,引用古籍原文,多用比喻
结论:格局判断+个性化祝福

每份报告都要独一无二!"""

        return prompt

    def _build_adult_prompt(self, detection_result: Dict, knowledge_matches: Dict,
                           gender: str) -> str:
        """构建成人面相分析提示词 - 极简版,让LLM自由发挥"""
        features = detection_result.get("features", {})
        measurements = detection_result.get("measurements", {})

        gender_text = "先生" if gender == 'male' else "女士"

        # 转换测量数据为cm（假设成年平均脸宽15cm）
        face_width_cm = 15.0
        face_ratio = measurements.get("face", {}).get("shape_ratio", 1.3)
        face_height_cm = face_width_cm * face_ratio

        # 三停高度（cm）
        forehead_ratio = measurements.get("forehead", {}).get("ratio", 0.3)
        middle_ratio = measurements.get("middle", {}).get("ratio", 0.35)
        lower_ratio = measurements.get("lower", {}).get("ratio", 0.35)

        forehead_cm = face_height_cm * forehead_ratio
        middle_cm = face_height_cm * middle_ratio
        lower_cm = face_height_cm * lower_ratio

        # 眼睛,鼻子,嘴巴的数据
        eyes_ratio = measurements.get("eyes", {}).get("left_ratio", 0.25)
        eye_width_cm = face_width_cm * eyes_ratio

        nose_ratio = measurements.get("nose", {}).get("ratio", 1.7)
        nose_length_cm = face_height_cm * 0.25
        nose_width_cm = nose_length_cm / nose_ratio if nose_ratio > 0 else 3.0

        mouth_ratio = measurements.get("mouth", {}).get("ratio", 0.35)
        mouth_width_cm = face_width_cm * mouth_ratio

        # 判断脸型
        if face_ratio < 1.2:
            face_type = "圆脸"
        elif face_ratio < 1.35:
            face_type = "椭圆脸"
        elif face_ratio < 1.5:
            face_type = "鹅蛋脸"
        else:
            face_type = "长脸"

        # 极简prompt - 只提供数据,不给格式
        prompt = f"""请为这位{gender_text}生成面相分析报告。

【检测数据】
脸型:{face_type} 三停:上{forehead_ratio*100:.0f}% 中{middle_ratio*100:.0f}% 下{lower_ratio*100:.0f}%
五官:额{features.get('forehead','')} 眼{features.get('eyes','')} 鼻{features.get('nose','')}

尺寸:额头{forehead_cm:.1f}cm 眼{eye_width_cm:.1f}cm 鼻{nose_length_cm:.1f}x{nose_width_cm:.1f}cm 嘴{mouth_width_cm:.1f}cm"""

        # 添加知识库匹配结果
        matched = knowledge_matches.get("matched_features", [])
        if matched:
            prompt += "\n\n【古籍参考】\n"
            # 按部位分组,避免重复
            parts_map = {}
            for match in matched[:8]:  # 最多取8条匹配
                part = match.get("部位", "")
                if part and part not in parts_map:
                    parts_map[part] = match

            for part, match in parts_map.items():
                source = match.get("古籍", "")
                original = match.get("原文", "")
                explanation = match.get("现代解释", "")
                if original and explanation:
                    prompt += f"• {part}:《{source}》「{original}」\n"
                    prompt += f"  解读: {explanation}\n"

            # 添加综合总结(如果有)
            summary = knowledge_matches.get("summary", {})
            if summary:
                pattern = summary.get("整体格局", "")
                if pattern:
                    prompt += f"\n整体格局: {pattern}\n"

        prompt += """
【要求】
开场白:根据数据特点创作,禁止用"相貌端正""气质沉稳""五官端正"
正文:按部位分析,引用数据,引用古籍原文,多用比喻
结论:格局判断+个性化祝福

每份报告都要独一无二!"""

        return prompt


# 创建全局LLM客户端实例
_llm_client = None


def get_llm_client() -> LLMClient:
    """获取LLM客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
