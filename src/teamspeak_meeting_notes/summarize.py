from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime

from openai import OpenAI

from teamspeak_meeting_notes.models import TimelineUtterance

OLLAMA_BASE_URL = "http://192.168.10.60:11434/v1"
OLLAMA_MODEL = "glm-4.7-flash:q4_K_M"


def _timeline_to_text(utterances: list[TimelineUtterance]) -> str:
    lines = []
    for row in utterances:
        stamp = row.start_at.strftime("%H:%M:%S")
        lines.append(f"[{stamp}] {row.speaker_name}: {row.text}")
    return "\n".join(lines)


def summarize_with_openai(utterances: list[TimelineUtterance], meeting_title: str | None) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
    model = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)
    api_key = os.getenv("OLLAMA_API_KEY", "ollama")

    transcript_text = _timeline_to_text(utterances)
    system_prompt = (
        "你是会议分析助手。请输出‘会议助手+时间戳+分析段落’风格纪要。"
        "语气客观、简洁，重点指出：是否偏题、沟通是否顺畅、是否出现结论或行动项。"
        "严格使用以下格式，不要使用Markdown标题："
        "会议助手HH:MM <分析段落>\n"
        "会议助手HH:MM <分析段落>\n"
        "综合观察 <总评段落>"
        "每个分析段落2-4句，允许写‘待确认’，禁止编造。"
    )
    title = meeting_title or "TeamSpeak 会议"
    user_prompt = (
        f"会议主题：{title}\n"
        "请按照示例风格输出，突出阶段性观察，不要做逐句转写。\n\n"
        f"Transcript:\n{transcript_text}"
    )

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.output_text.strip()


def summarize_heuristic(utterances: list[TimelineUtterance], meeting_title: str | None) -> str:
    title = meeting_title or "TeamSpeak 会议"
    if not utterances:
        return (
            "会议助手00:00 当前没有可分析的发言数据。\n综合观察 暂无会议内容，待确认录音是否有效。"
        )

    action_pattern = re.compile(
        r"\b(todo|action|follow up|deadline|需要|请|安排|下周)\b", re.IGNORECASE
    )
    off_topic_pattern = re.compile(
        r"\b(电视剧|解说|吐槽|玩笑|哈哈|外观|皮肤|游戏|装备|冲锋枪|弹匣|收割机|涡轮机)\b",
        re.IGNORECASE,
    )

    start = utterances[0].start_at

    def window_key(ts: datetime) -> int:
        delta = ts - start
        return int(delta.total_seconds() // 180)

    buckets: dict[int, list[TimelineUtterance]] = {}
    for row in utterances:
        key = window_key(row.start_at)
        buckets.setdefault(key, []).append(row)

    top_windows = sorted(buckets.items(), key=lambda item: len(item[1]), reverse=True)[:2]
    top_windows.sort(key=lambda item: item[0])

    lines: list[str] = []
    for _, rows in top_windows:
        stamp = rows[0].start_at.strftime("%H:%M")
        speaker_counter = Counter(item.speaker_name for item in rows)
        speakers = "和".join(name for name, _ in speaker_counter.most_common(2))

        off_topic_hits = sum(1 for item in rows if off_topic_pattern.search(item.text))
        action_hits = sum(1 for item in rows if action_pattern.search(item.text))

        if off_topic_hits >= max(2, len(rows) // 4):
            topic_desc = "讨论明显偏离主题，夹杂较多无关内容"
        else:
            topic_desc = "讨论基本围绕同一议题推进"

        if action_hits > 0:
            action_desc = "出现了可执行导向的表达，但需要进一步明确负责人和截止时间"
        else:
            action_desc = "未形成明确行动项，更多停留在观点交换"

        lines.append(
            f"会议助手{stamp} {speakers or '参会者'}在该时段发言较为集中，{topic_desc}。"
            f"{action_desc}。"
        )

    all_speakers = Counter(item.speaker_name for item in utterances)
    active = "、".join(name for name, _ in all_speakers.most_common(3))
    all_actions = sum(1 for item in utterances if action_pattern.search(item.text))
    all_offtopic = sum(1 for item in utterances if off_topic_pattern.search(item.text))

    if all_offtopic >= max(3, len(utterances) // 5):
        discipline = "整体注意力存在分散迹象，会议纪律偏松散"
    else:
        discipline = "整体讨论相对聚焦，偏题现象可控"

    if all_actions == 0:
        closure = "目前未检出高置信度结论与行动项（待确认）。"
    else:
        closure = "已出现部分行动导向信息，建议会后补齐责任人和时间节点。"

    lines.append(
        f"综合观察 会议主题《{title}》中，活跃参与者主要为{active or '待确认'}。"
        f"{discipline}。{closure}"
    )
    return "\n".join(lines)
