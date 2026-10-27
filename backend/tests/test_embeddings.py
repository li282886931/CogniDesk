import pytest

from app.embeddings import DeterministicEmbeddingProvider


def test_deterministic_embedding_is_stable_and_normalized():
    provider = DeterministicEmbeddingProvider(dimension=8)

    first = provider.embed("订单物流服务规范")
    second = provider.embed("订单物流服务规范")

    assert first == second
    assert len(first) == 8
    assert pytest.approx(sum(value * value for value in first), abs=1e-6) == 1.0


def test_embedding_rejects_blank_text():
    provider = DeterministicEmbeddingProvider(dimension=8)

    with pytest.raises(ValueError, match="text must not be blank"):
        provider.embed("  ")
