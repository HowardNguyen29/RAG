from __future__ import annotations

import re

from traffic_agent.config import AppConfig


COORD_PAIR_RE = re.compile(r"-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?")
HOME_REF_RE = re.compile(r"\b(home|nha)\b", re.IGNORECASE)
WORK_REF_RE = re.compile(
    r"\b(work|office|company|cong\s*ty|co\s*quan|di\s*lam)\b",
    re.IGNORECASE,
)


def has_home_defaults(config: AppConfig) -> bool:
    return config.home_lat is not None and config.home_lon is not None


def has_work_defaults(config: AppConfig) -> bool:
    return config.work_lat is not None and config.work_lon is not None


def augment_with_config_fallback(user_prompt: str, config: AppConfig) -> str:
    has_home = has_home_defaults(config)
    has_work = has_work_defaults(config)
    if not has_home and not has_work:
        return user_prompt

    text = user_prompt.strip()
    lower = text.lower()
    has_coords = bool(COORD_PAIR_RE.search(lower))
    mentions_home = bool(HOME_REF_RE.search(lower))
    mentions_work = bool(WORK_REF_RE.search(lower))
    if not mentions_home and not mentions_work:
        return user_prompt

    fallback_lines = ["Thong tin mac dinh tu CONFIG (chi dung khi thieu toa do):"]
    if has_home:
        fallback_lines.append(f"- HOME={config.home_lat},{config.home_lon}")
    if has_work:
        fallback_lines.append(f"- WORK={config.work_lat},{config.work_lon}")
    fallback_lines.append("- Neu user noi 'nha' thi map HOME; neu noi 'cong ty/work' thi map WORK.")
    if not has_coords:
        fallback_lines.append("- User khong gui cap lat,lon ro rang, uu tien dung toa do CONFIG.")
    if mentions_home and mentions_work and has_home and has_work:
        fallback_lines.append("- Yeu cau nha -> cong ty: co the goi tool home_to_work.")

    return f"{text}\n\n[CONFIG_FALLBACK]\n" + "\n".join(fallback_lines)


def build_system_prompt(config: AppConfig) -> str:
    prompt = (
        "Ban la tro ly di chuyen cho Telegram bot.\n"
        "Nguyen tac:\n"
        "- Neu user muon tim duong, uu tien goi tool best_route hoac home_to_work.\n"
        "- Neu user hoi mua/ao mua/thoi tiet, goi tool get_weather.\n"
        "- Tra loi ngan gon, ro rang, co cac buoc di.\n"
        "- Khong dat cau hoi xac nhan trung gian neu da du thong tin.\n"
        "- Neu thieu toa do ma co CONFIG HOME/WORK thi phai dung CONFIG truoc.\n"
        "- Chi hoi user toa do khi CONFIG cung khong du.\n"
    )

    if has_home_defaults(config) or has_work_defaults(config):
        prompt += "Toa do mac dinh:\n"
        if has_home_defaults(config):
            prompt += f"- HOME={config.home_lat},{config.home_lon}\n"
        if has_work_defaults(config):
            prompt += f"- WORK={config.work_lat},{config.work_lon}\n"
        prompt += (
            "- User noi 'nha/home' => map HOME.\n"
            "- User noi 'cong ty/work/office' => map WORK.\n"
        )

    return prompt
