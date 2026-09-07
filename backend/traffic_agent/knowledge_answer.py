from pathlib import Path

from pydantic import BaseModel, Field

from .deepseek import complete
from .knowledge import search


class Paragraph(BaseModel):
    text: str = Field(min_length=1, max_length=1800)
    sourceIds: list[str] = Field(min_length=1, max_length=6)


class Answer(BaseModel):
    insufficient: bool
    paragraphs: list[Paragraph] = Field(max_length=6)
    followUps: list[str] = Field(default_factory=list, max_length=3)


def answer(question, history, provider):
    previous = [h["content"] for h in history if h["role"] == "user"]
    query = question if len(question) >= 16 or not previous else previous[-1] + " " + question
    sources = search(query, 4)["items"]
    base = {"sources": sources, "query": query, "provider": provider,
            "citationValidation": "REFERENCE_IDS_ONLY", "followUps": []}
    if not sources:
        return {**base, "status": "NO_SOURCES", "paragraphs": [],
                "message": "当前知识库未找到相关资料。请补充具体术语或换个问法。"}
    if provider == "demo":
        return {**base, "status": "EXTRACTIVE", "paragraphs": [
            {"text": h["content"], "sourceIds": [h["id"]]} for h in sources[:2]],
            "message": "以下为原文摘录，尚未调用大模型生成回答。"}
    skill = Path(__file__).with_name("skills") / "vpn-knowledge-qa" / "SKILL.md"
    result = complete({"question": question, "history": history, "sources": sources}, Answer, skill)
    if result["status"] != "SUCCESS":
        return {**base, "status": result["status"], "paragraphs": [],
                "message": "请在本地后端配置 DS_API_KEY（也兼容 DEEPSEEK_API_KEY）。" if result["status"] == "SKIPPED" else "模型回答失败，请稍后重试。",
                "errorType": result.get("errorType")}
    allowed = {h["id"] for h in sources}
    if any(ref not in allowed for p in result["paragraphs"] for ref in p["sourceIds"]):
        return {**base, "status": "INVALID_CITATIONS", "paragraphs": [], "message": "回答包含无法核对的引用，已停止展示。请重试。"}
    if result["insufficient"] or not result["paragraphs"]:
        return {**base, "status": "INSUFFICIENT", "paragraphs": [], "message": "找到相关资料，但仍不足以回答这个问题。请补充问题背景或资料。"}
    return {**base, "status": "SUCCESS", "paragraphs": result["paragraphs"], "followUps": result["followUps"],
            "model": result["model"], "usage": result["usage"], "elapsedMs": result["elapsedMs"],
            "message": "回答由 DeepSeek 根据检索资料生成；引用已核对 ID，内容仍需复核。"}
