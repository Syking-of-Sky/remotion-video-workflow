# 验证记录

执行日期：2026-10-05。使用合成测试媒体与仓库内原创示例，没有读取真实歌曲、歌词或人物素材。

环境：macOS、Python 3.11.9、Node.js 26.0.0、FFmpeg/FFprobe 8.1.2、已安装的 Chrome。示例固定 Remotion 4.0.532，版本见 lockfile。这是实际测试环境，不代表测试过所有操作系统和依赖版本。

## 通用工具

`python3 -m unittest discover -s tests -v`：15 项通过，无跳过。

| 范围 | 实际检查 |
|---|---|
| 时间轴 | 原文与重复段落、有理数帧率、毫秒/厘秒进位、场景连续覆盖、逐字范围、重叠/非有限时间、音频越界、字幕输出与覆盖保护 |
| 成片 | 合成 H.264 完整解码；相同首尾通过；运动首尾、错误帧数、缺音轨及损坏文件正确失败；源 PNG 单像素差异检出 |
| 音频 | 静音与正弦音的 RMS 区别；未提供 BPM 不生成伪拍点；显式 BPM 网格 |
| 字体 | 合成字体成功子集化，缺字时失败 |
| 预览服务 | HTTP Range、后缀范围、HEAD、416 与文件符号链接越界拒绝 |

Python 脚本通过编译检查；技能通过 Codex skill-creator 的 `quick_validate.py` 结构检查。

## Remotion 示例

从 `package-lock.json` 执行 `npm ci --ignore-scripts` 成功，`npm run check` 通过。实际运行 `npm run render -- --concurrency=3 --log=error`；浏览器路径通过环境变量传入。

对成片运行 `verify_video.py` 并指定时间轴、尺寸和无声要求：

```json
{
  "ok": true,
  "video": {
    "width": 1280,
    "height": 720,
    "fps": "30",
    "frames": 180,
    "codec": "h264",
    "pixel_format": "yuvj420p",
    "duration": "6.000000"
  },
  "audio": [],
  "full_decode": true
}
```

抽取第 0、89、179 帧检查构图、文字和标记位置。再按 179、0、89 的顺序独立抽帧，与第一次逐像素比较，三帧均完全相同，验证抽帧结果不依赖播放历史。

## 检查边界

工具测试不代替实际作品的听辨、科学资料查证或美术审核。未运行外部生图、TTS、ASR 服务，也没有把已有播放器中的用户操作算作自动测试。此示例不是首尾循环；精确循环的通过/失败行为由专门的合成测试验证。

成片、抽帧和依赖目录留在本地，被 `.gitignore` 排除；公开仓库保留可复现源码与测试。
