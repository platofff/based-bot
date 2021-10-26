import re


class TagsFormatter:
    @classmethod
    def _get(cls, match: re.Match) -> str:
        return re.sub(r'\[.*\|', '', match.group(0))[:-1]

    @classmethod
    def format(cls, msg: str, for_vk=False) -> str:
        res = re.sub(r'\[.*?\|.*?]', cls._get, msg)
        if for_vk:
            return re.sub(r'^[@|*]', '', res)
        else:
            return res
