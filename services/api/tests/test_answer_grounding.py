from devflow_rag import knowledge


def test_rejects_command_not_present_in_cited_evidence(monkeypatch) -> None:
    monkeypatch.setattr(knowledge, "search", lambda *_args, **_kwargs: [
        {"product": "Docker", "filename": "docker.md", "excerpt": "docker ps lists running containers", "score": 0.8},
    ])
    monkeypatch.setattr(knowledge, "_ollama", lambda *_args, **_kwargs: {
        "message": {"content": "运行 docker images [1]"}
    })
    result = knowledge.answer(1, "Docker 如何列出镜像？")
    assert result["answerable"] is False
    assert result["citations"] == []


def test_answer_uses_explicit_product_evidence(monkeypatch) -> None:
    monkeypatch.setattr(knowledge, "search", lambda *_args, **_kwargs: [
        {"product": "Kubernetes", "filename": "kubectl.md", "excerpt": "kubectl get pods", "score": 0.9},
        {"product": "Docker", "filename": "docker.md", "excerpt": "docker images lists images", "score": 0.8},
    ])
    monkeypatch.setattr(knowledge, "_ollama", lambda *_args, **_kwargs: {
        "message": {"content": "运行 docker images [1]"}
    })
    result = knowledge.answer(1, "Docker 如何列出镜像？")
    assert result["answerable"] is True
    assert result["citations"][0]["filename"] == "docker.md"
