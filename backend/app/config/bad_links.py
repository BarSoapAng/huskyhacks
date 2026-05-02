from dataclasses import dataclass


@dataclass(frozen=True)
class BadLinkRule:
    platform: str
    matches: tuple[str, ...]
    reason: str


BAD_LINK_RULES: tuple[BadLinkRule, ...] = (
    BadLinkRule(
        platform="youtube",
        matches=("youtube.com/shorts", "m.youtube.com/shorts"),
        reason="YouTube Shorts",
    ),
    BadLinkRule(
        platform="instagram",
        matches=("instagram.com/reels", "instagram.com/explore"),
        reason="Instagram Reels or Explore",
    ),
    BadLinkRule(
        platform="tiktok",
        matches=("tiktok.com",),
        reason="TikTok",
    ),
    BadLinkRule(
        platform="reddit",
        matches=("reddit.com/r/all", "reddit.com/r/popular"),
        reason="Reddit discovery feed",
    ),
)
