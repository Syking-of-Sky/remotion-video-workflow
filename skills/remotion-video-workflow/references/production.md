# 工程、验证与交付

检查已有 lockfile、Remotion/React 版本和浏览器。新工程可复制 `assets/remotion-starter` 后运行 `npm ci`、`npm run check`、`npm run stills -- --frames 0,89,179`、`npm run render`。

示例固定 Remotion 4.0.532，是可复现测试基线，不表示最新版。旧工程沿用匹配依赖。系统 Chrome 路径通过 `REMOTION_BROWSER_EXECUTABLE` 或 `--browser-executable` 传入，不写死某台机器路径。

中文使用可分发字体并附许可证，先查实际文本字形。子集加载用 `delayRender/continueRender` 等待所需字重和 `document.fonts.ready`，失败要明确报错。不能用本机安装字体掩盖交付缺字。

## 渲染

每类布局、最长字幕、密集公式与重要转场都抽帧；新多幕作品应覆盖每幕。动态图形检查多个时刻，静帧不能证明运动对应公式。

先做相关类型/算例/时间检查，再渲染。H.264/yuv420p 与 faststart 常用于普通 MP4；尺寸、帧率、质量按任务选。不要用 `-shortest` 掩盖本应修正的时长差。

```sh
ffmpeg -i picture.mp4 -i song.wav -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a aac -b:a 256k -movflags +faststart final.mp4
python3 "$SKILL_DIR/scripts/verify_video.py" final.mp4 \
  --timeline timeline.json --audio required --report validation.json
```

声音比画面长时先按用户意图延长画面或选择片段，不盲套命令。音轨重编码与原文件逐字节复制不是同一件事。

## 本地预览

运行 `preview_server.py --root outputs`；根目录仅放要展示的文件。默认回环地址，支持单字节范围，不用于公网部署。复制 `assets/preview.html`，修改标题、相对视频路径和章节即可。

加载证据是媒体状态、尺寸、时长与错误字段；播放和跳转分别检查。Range 请求应返回 206 和正确 Content-Range，seekable 应覆盖目标时间。

不能播时先查 MP4 元数据与完整解码，再排查 URL、MIME、Range、浏览器策略。区分自己触发的动作与观察到的状态；用户正在点播/拖动时停止抢控。无法自动验证时如实区分文件验证与播放器验证。

## 打包

交付要求的成片、无声版、字幕、来源/署名、最终素材和工程。包含 lockfile、渲染命令、字体许可证；排除依赖目录、ASR 缓存、临时音频、弃用素材及未获发布授权的媒体。

GitHub 技能仓库只放通用方法、脚本和可分享原创示例。真实作品需另行授权，不把整个工作目录直接加入 Git。公开记录不含 token、私人数据或用户绝对路径。
