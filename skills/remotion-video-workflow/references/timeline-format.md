# 时间轴格式

从已有项目导出这个小型 JSON 即可，不必重写项目数据模型。

```json
{
  "fps": 30, "durationInFrames": 180,
  "scenes": [
    {"id":"intro","startFrame":0,"durationInFrames":60},
    {"id":"update","startFrame":60,"durationInFrames":120}
  ],
  "lines": [
    {"start":0.2,"end":2.0,"text":"先看一个简单例子"},
    {"start":2.2,"end":5.8,"text":"沿着梯度更新参数"}
  ]
}
```

`fps` 为正数或有理数字符串，如 `"30000/1001"`；总帧数为正整数。`scenes` 可省略，提供时须从零连续覆盖全片、ID 唯一。

`lines` 可省略，时间单位秒、有限非负、正时长、有序无重叠、不超全片；允许间奏空白。可选 `words` 数组使用同样的 `start/end/text`，须在句内有序且文字拼回原句。字或词粒度都可。

可选 `audioDuration` 为正秒数，不超过画面时长，帮助发现整曲任务的错误取整。允许其他工程字段；校验器只解释上述字段。

```sh
python3 scripts/timeline.py timeline.json --expected-text lyrics.txt --srt captions.srt --lrc lyrics.lrc
```

原文文件每个非空行一句，不含署名，顺序和重复次数严格比较。工具只导出已有时间，不做 ASR/推断。默认不覆盖文件；明确替换用 `--force`。
