from app.schemas.check_url import CheckUrlRequest
from app.services.url_classifier import (
    build_learning_input,
    find_bad_link_rule,
    map_score_to_action,
)
from app.utils.normalize_url import normalize_url


def test_bad_link_rule_matches_normalized_youtube_shorts() -> None:
    normalized = normalize_url("https://m.youtube.com/shorts/abc?si=test")

    rule = find_bad_link_rule(normalized)

    assert rule is not None
    assert rule.reason == "YouTube Shorts"


def test_bad_link_rule_matches_reddit_subdomains() -> None:
    normalized = normalize_url("https://old.reddit.com/r/popular")

    rule = find_bad_link_rule(normalized)

    assert rule is not None
    assert rule.reason == "Reddit discovery feed"


def test_safe_url_has_no_bad_link_rule() -> None:
    normalized = normalize_url("https://docs.python.org/3/library/urllib.parse.html")

    assert find_bad_link_rule(normalized) is None


def test_build_learning_input_has_no_user_goal() -> None:
    normalized = normalize_url("https://youtube.com/watch?v=abc123")
    request = CheckUrlRequest(
        url="https://youtube.com/watch?v=abc123",
        pageTitle="PID Controller Explained",
    )

    learning_input = build_learning_input(request, normalized)

    assert learning_input.url == "https://youtube.com/watch?v=abc123"
    assert learning_input.platform == "youtube"
    assert learning_input.content_type == "video"
    assert learning_input.page_title == "PID Controller Explained"
    assert "userDeclaredGoal" not in learning_input.model_dump(by_alias=True)


def test_map_score_to_action_is_conservative() -> None:
    assert map_score_to_action(40, 0.95) == {"allowed": True, "action": "allow"}
    assert map_score_to_action(80, 0.95) == {
        "allowed": True,
        "action": "soft_alert",
    }
    assert map_score_to_action(90, 0.84) == {
        "allowed": True,
        "action": "soft_alert",
    }
    assert map_score_to_action(90, 0.85) == {
        "allowed": False,
        "action": "hard_block",
    }
