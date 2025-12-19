![Logo](logo.png)

# SRT 字幕批量翻译工具

一个基于 DeepL API 的高效 SRT 字幕批量翻译工具，支持智能缓存、配额管理和批量处理。

---

## ✨ 主要特性

- 🚀 **批量翻译优化**：采用智能分块策略，最大化 API 利用率
- 💾 **智能缓存系统**：自动缓存已翻译内容，避免重复翻译
- 📊 **配额监控**：实时监控 DeepL API 使用量，自动预警
- 🔧 **自动依赖管理**：首次运行自动检查并安装依赖
- 🌐 **编码自动检测**：支持多种文件编码格式
- 📈 **友好进度显示**：实时显示翻译进度和彩色状态提示
- 🛡️ **完善错误处理**：针对常见 API 错误提供清晰的诊断信息

## 📋 系统要求

- Python 3.7+
- DeepL API Key（免费或付费账户）
- 互联网连接

## 🔧 安装配置

### 1. 克隆或下载项目

```bash
git clone <your-repo-url>
cd subtitle-translate
```

### 2. 配置 DeepL API

复制配置文件模板并编辑：

```bash
cp config.ini.sample config.ini
```

编辑 `config.ini`，填入你的 DeepL API Key：

```ini
[deepl]
; 你的 DeepL API Key（注意：不要用引号包裹）
api_key = YOUR_DEEPL_API_KEY_HERE

; DeepL 翻译 API 地址
; 免费账户使用：https://api-free.deepl.com/v2/translate
; 付费账户使用：https://api.deepl.com/v2/translate
translate_url = https://api-free.deepl.com/v2/translate

; DeepL 用量查询 API 地址
; 免费账户使用：https://api-free.deepl.com/v2/usage
; 付费账户使用：https://api.deepl.com/v2/usage
usage_url = https://api-free.deepl.com/v2/usage

[settings]
; 每次 API 调用后的休眠时间（秒），避免触发限速
sleep_time = 0.5

; 配额阈值（0-1）。当使用量达到此百分比时程序将退出
; 例如：0.95 表示使用量达到 95% 时停止
quota_threshold = 0.95

; 单次 API 请求的最大字符数（DeepL 限制为 50000）
; 建议设置为 45000 以留有安全余量
max_batch_chars = 45000
```

### 3. 获取 DeepL API Key

1. 访问 [DeepL API 官网](https://www.deepl.com/pro-api)
2. 注册免费账户（每月 500,000 字符免费额度）
3. 在账户设置中生成 API Key

## 🚀 使用方法

### 基本用法

1. 将需要翻译的 SRT 文件放入项目目录
2. 运行翻译脚本：

```bash
# Linux/macOS
chmod +x subtitle.sh
./subtitle.sh

# 或直接运行 Python 脚本
python3 main.py
```

3. 翻译完成后，输出文件将保存为 `原文件名.zh.srt`

### ASS 字幕转换（可选）

如果你有 ASS 格式字幕需要转换为 SRT：

```bash
# 需要先安装 ffmpeg
chmod +x ass2srt.sh
./ass2srt.sh
```

## 📁 项目结构

```
subtitle-translate/
├── main.py              # 主程序
├── config.ini.sample    # 配置文件模板
├── config.ini          # 实际配置文件（需自行创建，已在 .gitignore）
├── cache.json          # 翻译缓存（自动生成）
├── subtitle.sh         # Linux/macOS 启动脚本
├── ass2srt.sh          # ASS 转 SRT 工具脚本
├── local_git.sh        # Git 部署脚本
├── .gitignore          # Git 忽略规则
└── README.md           # 本文档
```

## ⚙️ 工作原理

### 批量翻译策略

程序采用智能分块（Chunk-Based）翻译策略：

1. **文本预处理**：解析 SRT 文件，提取所有需翻译的文本
2. **缓存检查**：查询本地缓存，跳过已翻译内容
3. **智能分块**：将待翻译文本合并成批次（每批最多 45,000 字符）
4. **批量翻译**：使用特殊分隔符 `<DEEPL_SPLIT_TOKEN>` 合并多段文本
5. **结果分割**：根据分隔符拆分翻译结果，匹配原文
6. **缓存更新**：保存新翻译结果到缓存
7. **文件输出**：生成双语字幕文件（原文 + 译文）

### 配额管理

- 启动时检查 DeepL API 使用量
- 当使用量超过配置阈值（默认 95%）时自动停止
- 显示配额重置日期（付费账户）或提示查看账户信息（免费账户）

## 🛠️ 依赖项

程序会自动检查并安装以下依赖：

- `requests` - HTTP 请求库
- `chardet` - 字符编码检测
- `configparser` - 配置文件解析

## 📊 输出格式

翻译后的 SRT 文件格式示例：

```
1
00:00:01,000 --> 00:00:03,000
Hello, world!
你好，世界！

2
00:00:04,000 --> 00:00:06,000
This is a subtitle.
这是一条字幕。
```

每个字幕块包含：
- 序号
- 时间轴
- 原文（可能多行）
- 译文（单行）

## ⚠️ 常见问题

### 1. 403 Forbidden 错误

**原因**：API Key 无效、格式错误或被吊销

**解决方案**：
- 检查 `config.ini` 中 `api_key` 的值
- 确保 API Key 没有被引号包裹
- 确认使用的是正确的 API 端点（免费/付费账户不同）
- 在 DeepL 账户中重新生成 API Key

### 2. 配额不足

**解决方案**：
- 等待配额重置（免费账户每月重置）
- 升级到付费账户
- 调整 `quota_threshold` 参数

### 3. 翻译结果为空

**可能原因**：
- 网络连接问题
- API 限速
- 文本格式问题

**解决方案**：
- 检查网络连接
- 增加 `sleep_time` 参数值
- 检查原始 SRT 文件格式

### 4. 编码错误

**解决方案**：
程序会自动检测文件编码，如果仍有问题：
- 使用文本编辑器将文件转换为 UTF-8 编码
- 确保文件不包含特殊控制字符

## 🔒 安全性

- ✅ API Key 通过 `.gitignore` 排除，不会被提交到版本控制
- ✅ 配置文件使用本地存储，不上传到远程仓库
- ✅ 所有 API 请求使用 HTTPS 加密传输

## 📝 注意事项

1. **API 限制**：DeepL 免费账户每月 500,000 字符限额
2. **文件命名**：已翻译文件（`.zh.srt`）会被自动跳过
3. **缓存管理**：`cache.json` 会持续增长，可定期清理
4. **网络要求**：需要稳定的互联网连接访问 DeepL API

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证。

## 🙏 致谢

- [DeepL](https://www.deepl.com/) - 提供高质量翻译 API
- 所有贡献者和用户

## 📮 联系方式

如有问题或建议，请通过 GitHub Issues 联系。

---

**⭐ 如果这个项目对你有帮助，欢迎 Star！**
