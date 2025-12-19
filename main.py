import sys
import os
import re
import time
import json
import configparser
import requests
import importlib.util
import chardet
import subprocess
from pathlib import Path
from typing import Tuple, Dict
from datetime import datetime, timezone 

# --- 常量 ---
CACHE_FILE = Path("cache.json")
CONFIG_FILE = Path("config.ini")
REQUIRED_LIBRARIES = ["requests", "chardet", "configparser"]

# --- 实用功能：环境检查与编码检测 ---

def check_and_install_dependencies():
    """检查并安装依赖库"""
    missing = [lib for lib in REQUIRED_LIBRARIES if not importlib.util.find_spec(lib)]
    
    if missing:
        print(f"❌ 缺少依赖库: {', '.join(missing)}")
        for pkg in missing:
            print(f"正在安装 {pkg}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"✅ {pkg} 安装成功")
            except Exception:
                print(f"❌ 无法安装 {pkg}。请手动安装:")
                print(f"   {sys.executable} -m pip install {pkg}")
                sys.exit(1)

def detect_file_encoding(file_path: Path) -> str:
    """检测文件编码"""
    try:
        with file_path.open("rb") as f:
            result = chardet.detect(f.read(1024))
            if result["encoding"] and result["confidence"] > 0.5:
                return result["encoding"]
    except Exception:
        pass
    return "iso-8859-1"

# --- 配置加载 (整合所有配置) ---

def load_config_settings(config_file: Path) -> dict:
    """从 config.ini 中加载所有配置，包括 API Key 和通用设置。"""
    config = configparser.ConfigParser()
    if not config_file.exists():
        raise EnvironmentError(f"配置文件 {config_file} 未找到。请根据 config.ini.sample 创建。")

    config.read(config_file, encoding='utf-8')
    
    settings = {}
    try:
        # DeepL Section
        settings['api_key'] = config.get("deepl", "api_key").strip()
        settings['translate_url'] = config.get("deepl", "translate_url").strip()
        settings['usage_url'] = config.get("deepl", "usage_url").strip()
        
        # Settings Section
        settings['sleep_time'] = config.getfloat("settings", "sleep_time")
        settings['quota_threshold'] = config.getfloat("settings", "quota_threshold")
        settings['max_batch_chars'] = config.getint("settings", "max_batch_chars")

        if not settings['api_key']:
             raise EnvironmentError(f"配置文件 {config_file} 中 [deepl] 部分的 api_key 不能为空。")

    except configparser.Error as e:
        raise EnvironmentError(f"配置文件 {config_file} 读取错误：缺少必要的配置项。请参考 config.ini.sample。详细错误: {e}")
    except ValueError as e:
        raise EnvironmentError(f"配置文件 {config_file} 中配置值类型错误（如 sleep_time 或 quota_threshold 应为数字）：{e}")
    
    return settings

# --- DeepL API 交互 ---

class DeepLAPI:
    """DeepL API 交互类"""
    def __init__(self, api_key: str, settings: dict):
        self.api_key = api_key
        self.settings = settings

    def _handle_error(self, response: requests.Response, endpoint_name: str):
        """通用错误处理，特别是针对 403 错误立即退出。"""
        if response.status_code == 403:
            print(f"\n🔴 DeepL API 致命错误 (403 Forbidden) 在 {endpoint_name} 请求中。")
            print("原因通常是 API Key 无效、格式错误（例如被引号包裹）或已被吊销。")
            print(f"请检查 config.ini 中 [deepl] -> api_key 的值。")
            print(f"DeepL 错误响应: {response.text[:150]}...")
            sys.exit(1)
        
        response.raise_for_status()


    def translate(self, text: str) -> str:
        """翻译文本"""
        if not text.strip():
            return ""

        data = {
            "auth_key": self.api_key,
            "text": text,
            "target_lang": "ZH"
        }

        try:
            response = requests.post(self.settings['translate_url'], data=data, timeout=10)
            self._handle_error(response, "翻译")
            translated = response.json()["translations"][0]["text"]
            time.sleep(self.settings['sleep_time'])
            return translated
        except requests.exceptions.RequestException as e:
            print(f"\n❌ 翻译请求失败: {e}")
            return ""


    def get_usage(self) -> Tuple[int, int, float, str]:
        """获取 API 使用量信息 (用于配额检查)"""
        response = requests.get(self.settings['usage_url'], params={"auth_key": self.api_key}, timeout=5)
        self._handle_error(response, "用量查询")
        
        data = response.json()
        used = data.get("character_count", 0)
        limit = data.get("character_limit", 500000)
        percentage = (used / limit) if limit else 0
        
        # --- 提取并格式化重置日期 ---
        # 尝试获取 period_end_time (新字段) 或 end_time (旧字段/Pro字段)
        end_time_data = data.get("period_end_time") or data.get("end_time") 
        
        reset_date_str = "未知"
        if end_time_data:
            try:
                if isinstance(end_time_data, (int, float)):
                    # 时间戳格式（秒）
                    dt_obj = datetime.fromtimestamp(end_time_data, tz=timezone.utc)
                elif isinstance(end_time_data, str):
                    # ISO 8601 字符串格式 (e.g., "2025-05-13T09:18:42Z")
                    dt_obj = datetime.fromisoformat(end_time_data.replace('Z', '+00:00'))
                else:
                    raise ValueError("Unsupported date format.")
                
                reset_date_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (TypeError, ValueError, AttributeError):
                # 如果解析失败，则保持 "未知"
                pass
            
        return used, limit, percentage, reset_date_str
            
# --- 缓存管理 ---

class TranslationCache:
    """翻译缓存管理类"""
    def __init__(self):
        self.cache: Dict[str, str] = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        if CACHE_FILE.exists():
            try:
                with CACHE_FILE.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save(self):
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get(self, text: str) -> str | None:
        return self.cache.get(text)

    def set(self, text: str, translation: str):
        self.cache[text] = translation
        self.save()

# --- SRT 文件处理 ---

def process_srt_file(file_path: Path, api: DeepLAPI, cache: TranslationCache, settings: dict):
    """处理单个SRT文件，采用批量（Chunk-Based）翻译"""
    print(f"\n🎬 正在处理文件: {file_path.name}")
    
    SPLIT_TOKEN = "<DEEPL_SPLIT_TOKEN>" 
    MAX_CHARS = settings.get('max_batch_chars', 45000)
    
    try:
        encoding = detect_file_encoding(file_path)
        content = file_path.read_text(encoding=encoding)
        
        blocks = re.split(r"(\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n)", content.strip()) 
        blocks = blocks[1:]
        
        indexed_blocks = [blocks[i] + blocks[i+1] for i in range(0, len(blocks), 2)]
        total = len(indexed_blocks)
        
        batches = []
        current_batch_text = ""
        current_batch_indices = []
        
        all_translations = {} 

        for idx, block in enumerate(indexed_blocks):
            lines = block.split("\n")
            if len(lines) < 2:
                continue

            index, timestamp, *text_lines = lines
            english_text = re.sub(r"\[.*?\]|\{.*?\}", "", " ".join(text_lines)).strip()
            
            cached_translation = cache.get(english_text)
            if cached_translation is not None:
                all_translations[english_text] = cached_translation
                continue
            
            text_to_add = english_text + SPLIT_TOKEN
            
            if len(current_batch_text) + len(text_to_add) > MAX_CHARS and current_batch_text:
                batches.append((current_batch_text, current_batch_indices))
                current_batch_text = ""
                current_batch_indices = []
            
            current_batch_text += text_to_add
            current_batch_indices.append(english_text)

        if current_batch_text:
            batches.append((current_batch_text, current_batch_indices))

        
        print(f"📦 翻译批次总数: {len(batches)}")
        
        for batch_idx, (batch_text, original_texts) in enumerate(batches):
            sys.stdout.write(f"\r⚙️ 正在翻译批次 {batch_idx + 1}/{len(batches)}...")
            sys.stdout.flush()

            translated_batch_text = api.translate(batch_text)

            if translated_batch_text:
                translated_segments = translated_batch_text.split(SPLIT_TOKEN)
                
                for i, original_text in enumerate(original_texts):
                    if i < len(translated_segments) and translated_segments[i].strip():
                        translation = translated_segments[i].strip()
                        all_translations[original_text] = translation
                        cache.set(original_text, translation)
            
            else:
                print(f"\n❌ 批次 {batch_idx + 1} 翻译失败或返回空结果。")

        new_blocks = []
        for idx, block in enumerate(indexed_blocks):
            lines = block.split("\n")
            if len(lines) < 2:
                new_blocks.append(block)
                continue

            index, timestamp, *text_lines = lines
            english_text = re.sub(r"\[.*?\]|\{.*?\}", "", " ".join(text_lines)).strip()
            
            translated = all_translations.get(english_text)
            
            if not translated:
                translated = cache.get(english_text) or "【翻译失败或原文为空】"

            original_lines = [l for l in text_lines if l.strip()]
            new_block = [index, timestamp, *original_lines, translated]
            new_blocks.append("\n".join(new_block))
            
            progress_bar = f"[{'#' * int((idx + 1) / total * 20):20}]"
            sys.stdout.write(f"\r✅ 进度: {progress_bar} {((idx + 1) / total)*100:.1f}% ({idx + 1}/{total})")
            sys.stdout.flush()


        output_file = file_path.with_suffix(".zh.srt")
        output_file.write_text("\n\n".join(new_blocks) + "\n\n", encoding="utf-8")
        print(f"\n🎉 翻译完成! 输出文件: {output_file.name}")

    except Exception as e:
        print(f"\n❌ 处理 {file_path.name} 失败: {e}")

# --- 主函数 ---
def main():
    print("✨ SRT 批量翻译工具 ✨")
    
    # 1. 环境检查
    try:
        check_and_install_dependencies()
        settings = load_config_settings(CONFIG_FILE)
    except Exception as e:
        print(f"🔴 启动失败: {e}")
        sys.exit(1)
        
    # 2. 初始化 API 和检查配额
    try:
        api = DeepLAPI(settings['api_key'], settings)
        
        used, limit, percentage, reset_date_str = api.get_usage()
        
        quota_threshold = settings['quota_threshold']
        
        # --- 优化输出逻辑 ---
        
        if reset_date_str == "未知":
            # 免费套餐不提供重置日期，提供清晰提示
            reset_output = "DeepL API 免费套餐不提供确切重置日期。请登录 DeepL 账户门户查看。"
        else:
            reset_output = f"配额重置日期: {reset_date_str}."

        usage_info = f"   已使用字符数: {used:,} / 限制: {limit:,} ({percentage*100:.2f}%)."
        
        if percentage > quota_threshold:
            print(f"\n🔴 DeepL API 配额即将耗尽！")
            print(usage_info)
            print(f"   {reset_output}")
            print("程序已退出。")
            sys.exit(1)
        elif percentage > quota_threshold - 0.15: 
            print(f"\n⚠️ DeepL API 配额使用警告！")
            print(usage_info)
            print(f"   {reset_output}")
        else:
             print(f"\n🟢 DeepL API 配额检查通过。")
             print(usage_info)
             print(f"   {reset_output}")

    except requests.exceptions.RequestException as e:
        # 捕获所有在初始化 API 或检查用量时发生的网络/HTTP 错误
        print(f"\n🔴 启动失败：无法连接 DeepL API 或服务器返回错误。")
        print(f"   详细错误: {e}")
        print("请检查您的网络连接、DeepL API Key 是否有效，以及 API 端点是否正确。")
        sys.exit(1)
    except EnvironmentError as e:
        print(f"🔴 DeepL 配置错误: {e}")
        sys.exit(1)
        
    # 3. 查找文件并处理
    cache = TranslationCache()
    srt_files = [f for f in Path.cwd().glob("*.srt") if not f.name.endswith(".zh.srt")]

    if not srt_files:
        print("\n⚠️ 在当前目录下未找到待翻译的 SRT 文件 (*.srt，跳过 *.zh.srt)。")
        print("请将 SRT 文件放入程序所在目录后重试。")
        return

    print(f"找到 {len(srt_files)} 个 SRT 文件，开始翻译...")
    
    for file in srt_files:
        process_srt_file(file, api, cache, settings)

    print("\n🎉 所有文件处理完毕。")

if __name__ == "__main__":
    main()
