---
name: remotion-video-workflow
description: 用 Remotion 制作或修改中文歌词 MV、科普图解和循环短片，处理音频时间轴、公式驱动动画、统一角色表情、渲染与成片验证。适用于用户指定 Remotion 或已有 Remotion 工程的任务；不用于纯视频模型提示词，也不自动迁移其他视频框架。
---

# Remotion 视频工作流

把创意做成可播放、可复查、可编辑的成片。延续已有工程和用户最近确认的风格；新主题可以重新设计，不把上一个项目的配色、时长或循环结尾套到所有视频。

## 从项目状态继续

先检查入口、Composition、时间轴、素材、输出和制作说明。恢复用户当前选择：人物参考、认可/放弃的版本、是否循环、是否保留完整原曲。把这些事实写入项目 `design.md` 或同类文件。

只在缺失信息确实影响工作时提问，同时推进独立部分。用户已授权制作时先做出可检查的结果；本技能不增加逐步批准门槛，也不授予额外上传或发布权限。

## 按任务加载

| 条件 | 阅读 |
|---|---|
| 歌曲、歌词、卡点或文字 MV | [lyrics-and-rhythm.md](references/lyrics-and-rhythm.md) |
| 历史、科学原理、公式与粒子图形 | [explainers.md](references/explainers.md) |
| 人物大头贴、表情扩展、画风一致 | [character-assets.md](references/character-assets.md) |
| 明确要求循环或首尾一致 | [seamless-loop.md](references/seamless-loop.md) |
| 首次实现、导出、交付或播放排障 | [production.md](references/production.md) |

分支可以组合，只加载本次需要的文件。

## 共用制作约定

1. **声音与时间基准。** 读取真实音频时长，明确帧率与总帧数。歌词以用户原文为准，转录提供时间线索。“更快”优先调整镜头、信息出现和转场，不擅自加速歌曲。
2. **先做代表镜头。** 覆盖最密一屏、最长字幕、重要人物和特殊转场。文字、图形、物件共同表达含义；点名元素在分镜里有明确位置，再扩展全片。
3. **动画由帧计算。** 用 `useCurrentFrame()` 和确定性函数，不依赖墙上时钟、未固定种子的随机数或上一帧组件状态。公式、轨迹和数值共用计算。
4. **素材固定到项目。** 字体、歌曲、图片使用相对路径。角色变体沿用认可底稿、版本保存；输出引用不指向临时目录或另一项目的依赖。
5. **分层验证。** 时间轴/类型检查 → 代表帧与运动抽检 → 编码文件解码/元数据 → 必要的播放器检查。检查范围跟随实际改动，不重复扩大已通过的无关测试。

## 可执行工具

`SKILL_DIR` 指当前技能目录。输入格式见 [timeline-format.md](references/timeline-format.md)。

```sh
python3 "$SKILL_DIR/scripts/timeline.py" timeline.json --expected-text lyrics.txt --srt captions.srt
python3 "$SKILL_DIR/scripts/analyze_audio.py" song.wav --output audio-analysis.json
python3 "$SKILL_DIR/scripts/font_subset.py" --font source.ttf --text captions.txt --output public/captions.ttf
python3 "$SKILL_DIR/scripts/verify_video.py" final.mp4 --timeline timeline.json --audio required --report validation.json
python3 "$SKILL_DIR/scripts/preview_server.py" --root outputs --port 53310
```

- `timeline.py`：场景覆盖、字幕/逐字边界、原文一致与 SRT/LRC。
- `analyze_audio.py`：RMS 包络和候选起音；只有明确输入 BPM 才生成参考节拍网格。
- `font_subset.py`：检查字形后生成字体子集，保留变量字体信息。
- `verify_video.py`：元数据、完整解码；按需比较源图和编码首尾像素。
- `preview_server.py`：支持 HTTP Range 的本地预览，适用于拖动和章节跳转。

新工程可复制 [remotion-starter](assets/remotion-starter/)。原创梯度下降示例展示图形与公式同源，不规定成片画风；工程内 `tools/capture.mjs` 批量抽取指定帧。

## 完成的证据

- 最终文件已生成，元数据与设计相符，完整解码无错误。
- 字幕来源和时间估计方式可追溯，无漏段、切断音频或擅改原文。
- 代表画面无缺字、遮挡、越界、错误素材；必要时检查图形的真实变化。
- 精确循环分别报告源首尾与最终解码首尾结果，不能仅凭肉眼称通过。
- 播放器加载、播放、跳转分别记录。用户正在操作时停止抢控，不把用户点击或时间增长归功于自动测试。
- 成片、工程和需要的字幕/素材有明确路径；提示词与来源保留在项目记录。只发布本次已授权且具备相应使用权限的文件。
