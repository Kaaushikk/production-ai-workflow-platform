from platform_api.auth import generate_api_key, hash_api_key


def test_generated_api_key_has_expected_prefix_and_entropy() -> None:
    first = generate_api_key()
    second = generate_api_key()

    assert first.startswith("pai_")
    assert len(first) >= 40
    assert first != second


def test_api_key_hash_is_stable_without_storing_plaintext() -> None:
    digest = hash_api_key("pai_example_key")

    assert digest == hash_api_key("pai_example_key")
    assert "example" not in digest
    assert len(digest) == 64

