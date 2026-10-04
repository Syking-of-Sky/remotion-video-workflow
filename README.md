# Remotion 视频工作流

可安装的 Codex Skill：歌词 MV、科普图解、统一角色表情、精确循环，以及从源工程到 MP4 的验证。工作流不绑定配色、片长或角色。

仓库仅有通用说明、工具与原创数学图解示例，不含实际作品的歌曲、歌词、照片、角色图片或成片。

## 安装与使用

```sh
git clone https://github.com/Syking-of-Sky/remotion-video-workflow.git
mkdir -p ~/.codex/skills
cp -R remotion-video-workflow/skills/remotion-video-workflow ~/.codex/skills/
```

目录已存在时先比较再合并，避免覆盖本地修改。使用示例：

```text
使用 $remotion-video-workflow，把我的歌曲做成歌词 MV，时间由你对齐。
使用 $remotion-video-workflow，制作带发展史和原理图解的科普视频。
使用 $remotion-video-workflow，验证这段短片首尾像素是否完全相同。
```

入口：[SKILL.md](skills/remotion-video-workflow/SKILL.md)。各分支按需读取，不一次加载全部规则。

也可以在支持 Skill 安装的 Codex 对话里直接说：

```text
从 https://github.com/Syking-of-Sky/remotion-video-workflow 安装 skills/remotion-video-workflow 技能。
```

## 工具

| 资源 | 用途 |
|---|---|
| `timeline.py` | 连续场景、字幕/逐字边界、原文比对、SRT/LRC |
| `analyze_audio.py` | RMS、候选起音、显式 BPM 网格 |
| `font_subset.py` | 字形与字体子集 |
| `verify_video.py` | 元数据、完整解码、可选首尾比较 |
| `preview_server.py` | 支持 Range 的本地预览 |
| `assets/remotion-starter` | 公式和图形同源的确定性动画示例 |

Python 3.10+，音视频工具需 FFmpeg/FFprobe。字体子集需 fonttools，源 PNG 比较需 Pillow：`python3 -m pip install fonttools Pillow`。示例工程需要 Node.js 20+ 和固定依赖。

生图、TTS、ASR 使用当前环境合适的工具；本仓库不会自动下载模型或上传媒体。

## 运行原创示例

在克隆后的仓库根目录执行：

```sh
cd skills/remotion-video-workflow/assets/remotion-starter
npm ci
npm run check
npm run stills -- --frames 0,89,179
npm run render
```

输出为示例目录下的 `renders/example.mp4`，6 秒、1280×720、30 fps。画面中的损失曲线、移动标记与数值来自同一个计算模型；示例无配乐，也不是循环片。

需要指定已安装的 Chrome 时，将路径设置到 `REMOTION_BROWSER_EXECUTABLE` 环境变量，再运行以上命令。完整制作与交付说明见 [production.md](skills/remotion-video-workflow/references/production.md)。

## 验证

运行 `python3 -m unittest discover -s tests -v`。测试合成临时音视频，不访问用户素材或付费 API。实际执行记录见 [VALIDATION.md](VALIDATION.md)。原创代码与说明使用 MIT；后来加入的媒体各自遵循其授权。
