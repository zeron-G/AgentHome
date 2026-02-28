"""叙事事件配置。

定义叙事阶段触发条件、线索关键词、结局触发条件、角色关系权重。
本文件是叙事推进规则的唯一真相来源。

设计基础：narrative-design.md (2026-02-26)
- 11角色塔罗体系（22张大阿尔卡纳完整分配）
- 6结局 + 4层世界结构
- 季节驱动叙事（每季28天，4季=112天）
- per-NPC 信任度（每个NPC独立0-100）
"""

# ── NPC 分级 ─────────────────────────────────────────────────────────────────

CORE_NPC_IDS = ["npc_he", "npc_sui", "npc_shan", "npc_tang"]
DAILY_NPC_IDS = ["npc_kuang", "npc_mu", "npc_lan", "npc_shi"]
SPECIAL_NPC_IDS = ["npc_shangren"]
ALL_NPC_IDS = CORE_NPC_IDS + DAILY_NPC_IDS + SPECIAL_NPC_IDS

# NPC 中文名映射
NPC_NAMES = {
    "npc_he": "禾",       # III 皇后 - 母亲
    "npc_sui": "穗",      # XIX 太阳 - 女儿
    "npc_shan": "山",     # IX 隐者 - 老村长
    "npc_tang": "棠",     # XII 倒吊人 - 玩伴
    "npc_kuang": "旷",    # VIII 力量 - 小男孩
    "npc_mu": "木",       # V 教皇 - 老工匠
    "npc_lan": "岚婆",    # II 女祭司 - 神婆
    "npc_shi": "石",      # VI 恋人 - 猎人儿子
    "npc_shangren": "商人",  # XV 恶魔 - 商人/恶魔
}

# NPC 思考频率配置（秒）
NPC_FREQUENCY = {
    # 核心NPC：视野内5-10s，视野外30s
    "npc_he":   {"in_view": 7,  "out_of_view": 30},
    "npc_sui":  {"in_view": 7,  "out_of_view": 30},
    "npc_shan": {"in_view": 10, "out_of_view": 30},
    "npc_tang": {"in_view": 5,  "out_of_view": 30},
    # 日常NPC：视野内15-30s，视野外90s
    "npc_kuang": {"in_view": 15, "out_of_view": 90},
    "npc_mu":    {"in_view": 20, "out_of_view": 90},
    "npc_lan":   {"in_view": 20, "out_of_view": 90},
    "npc_shi":   {"in_view": 25, "out_of_view": 90},
    # 特殊NPC：商人白天正常，夜晚不同提示词
    "npc_shangren": {"in_view": 15, "out_of_view": 60},
}

# 日常NPC的think_interval倍率（向后兼容）
DAILY_NPC_CONFIG = {
    npc_id: {"is_daily": True, "think_interval_multiplier": 3.0}
    for npc_id in DAILY_NPC_IDS
}


# ── 季节系统 ─────────────────────────────────────────────────────────────────

DAYS_PER_SEASON = 28

SEASON_CONFIG = {
    "spring": {
        "name": "春·播种",
        "day_range": (1, 28),
        "secret_stage": 0,
        "atmosphere": "温馨、充满希望、新的开始",
        "god_tone": "平淡自然观察，像一个慈祥的旁白者",
    },
    "summer": {
        "name": "夏·异变",
        "day_range": (29, 56),
        "secret_stage": 1,
        "atmosphere": "日常中出现微妙的不安，像夏天午后远处的闷雷",
        "god_tone": "流露紧张和保护欲，偶尔出现失言",
    },
    "autumn": {
        "name": "秋·碎裂",
        "day_range": (57, 84),
        "secret_stage": 2,
        "atmosphere": "信任建立后真相碎片浮现，像秋天的落叶",
        "god_tone": "矛盾情感浮现，守护者的内心挣扎外溢",
    },
    "winter": {
        "name": "冬·抉择",
        "day_range": (85, 112),
        "secret_stage": 3,
        "atmosphere": "寒冷、沉重、不可回避。天灾迫在眉睫",
        "god_tone": "坦诚面对，守护者放下伪装",
    },
}


# ── 叙事阶段 ─────────────────────────────────────────────────────────────────

NARRATIVE_STAGES = [
    {
        "id": 0,
        "name": "春·播种",
        "description": "温馨的日常生活，玩家熟悉世界规则和NPC",
        "trigger_conditions": {},
        "events": [
            {"event_id": "welcome", "description": "NPC热情欢迎玩家",
             "condition": {"type": "first_talk"}},
            {"event_id": "sui_intro", "description": "穗第一次出场——你就是回来的人吗？",
             "condition": {"min_day": 2}},
            {"event_id": "tang_reunion", "description": "棠热情迎接——你终于回来了！",
             "condition": {"min_day": 5}},
            {"event_id": "shangren_first", "description": "商人第一次出现在村口",
             "condition": {"min_day": 8}},
            {"event_id": "shan_hint", "description": "山说了一句没说完的话——回来就好，这次希望你能……",
             "condition": {"min_day": 14}},
            {"event_id": "lan_fortune", "description": "岚婆看手相——你的命运线很奇怪",
             "condition": {"min_day": 21}},
            {"event_id": "sui_question", "description": "穗第一次问出奇怪的问题——为什么没有人来我们村子玩？",
             "condition": {"min_day": 25}},
            {"event_id": "topic_avoidance", "description": "NPC回避某些话题",
             "condition": {"type": "forbidden_topic_touched"}},
        ],
    },
    {
        "id": 1,
        "name": "夏·异变",
        "description": "微妙的不安感，小异常开始出现",
        "trigger_conditions": {"min_day": 29, "any_of": [{"min_day": 29}, {"any_npc_trust": 15}]},
        "events": [
            {"event_id": "tang_isolation_hint", "description": "棠提到——我们好像很久没看到外面的人了",
             "condition": {"min_day": 30}},
            {"event_id": "nightmares", "description": "NPC偶尔提到奇怪的梦——被关在什么里面",
             "condition": {"min_day": 35}},
            {"event_id": "shangren_night", "description": "商人深夜出现在仪式地点",
             "condition": {"min_day": 40, "time_phase": "night"}},
            {"event_id": "old_photo", "description": "爷爷小屋里发现老照片",
             "condition": {"min_day": 42}},
            {"event_id": "well_sounds", "description": "老井夜里传来低语",
             "condition": {"min_day": 36, "time_phase": "night"}},
            {"event_id": "lan_possession", "description": "岚婆通灵表演时说出——别再往深处看了",
             "condition": {"min_day": 47}},
            {"event_id": "mu_warm_metal", "description": "木修缮的老物件好像在颤抖",
             "condition": {"min_day": 52}},
            {"event_id": "red_dusk", "description": "第一次红色黄昏——天灾前兆初现",
             "condition": {"min_day": 55}},
            {"event_id": "tang_restless", "description": "棠开始变得焦躁",
             "condition": {"min_day": 50}},
            {"event_id": "sui_drawing_eyes", "description": "穗画了天上有眼睛在看我们",
             "condition": {"min_day": 50}},
        ],
    },
    {
        "id": 2,
        "name": "秋·碎裂",
        "description": "信任建立后NPC透露碎片信息",
        "trigger_conditions": {"min_day": 57, "any_npc_trust": 30},
        "events": [
            {"event_id": "mention_grandpa", "description": "NPC偶然提起爷爷",
             "condition": {"any_npc_trust": 30}},
            {"event_id": "shan_parable", "description": "山主动讲古——有个人为了保护爱的人把自己变成了一面墙",
             "condition": {"helped_npcs_count": 3}},
            {"event_id": "tang_confession", "description": "棠告白——那个商人不是普通人",
             "condition": {"npc_trust_tang": 60}},
            {"event_id": "he_ritual", "description": "禾提到仪式——我也不知道为什么",
             "condition": {"npc_trust_he": 50}},
            {"event_id": "lan_dream_name", "description": "穗说岚婆做梦喊了爷爷的名字",
             "condition": {"visited_lan_count": 3}},
            {"event_id": "mu_runes", "description": "木发现符文工具和修缮物件一致",
             "condition": {"npc_trust_mu": 50, "helped_mu": True}},
            {"event_id": "sui_drawing_elder", "description": "穗画了被光包围的老人站在村子上方",
             "condition": {"min_day": 70}},
            {"event_id": "tang_stalking", "description": "棠深夜独自前往仪式地点找商人",
             "condition": {"min_day": 65}},
            {"event_id": "shi_forest_find", "description": "石在山林中发现异常——结界的物理痕迹",
             "condition": {"npc_trust_shi": 40}},
        ],
    },
    {
        "id": 3,
        "name": "冬·抉择",
        "description": "抉择与揭示，天灾前兆全面爆发",
        "trigger_conditions": {"min_day": 85, "any_npc_trust": 70, "min_clues_revealed": 3},
        "events": [
            {"event_id": "red_snow", "description": "红雪大规模降临",
             "condition": {"min_day": 85}},
            {"event_id": "shan_truth", "description": "山揭示爷爷的身份和结界本质",
             "condition": {"npc_trust_shan": 80, "grandpa_clue_found": True}},
            {"event_id": "boundary_revealed", "description": "村子边界——看不见的墙壁",
             "condition": {"player_explored_boundary": True}},
            {"event_id": "tang_sacrifice", "description": "棠被倒悬于结界裂缝——恶魔身份暴露",
             "condition": {"tang_traded_with_demon": True, "min_clues_revealed": 5}},
            {"event_id": "final_choice", "description": "最终抉择——结局分支点",
             "condition": {"all_core_clues_revealed": True}},
        ],
    },
]


# ── 线索关键词定义 ─────────────────────────────────────────────────────────

CLUE_DEFINITIONS = {
    "barrier": {
        "clue_id": "barrier", "display_name": "结界存在",
        "keywords": ["结界", "边界", "看不见的墙"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {20: "subtle", 50: "cryptic", 70: "near_direct"},
        "correct_player_action": "走到地图边缘发现无法离开",
        "related_npc": ["npc_shan", "npc_tang"],
    },
    "pact": {
        "clue_id": "pact", "display_name": "恶魔契约",
        "keywords": ["契约", "约定", "承诺", "交易"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {50: "cryptic", 80: "near_direct"},
        "correct_player_action": "找到契约内容，理解爷爷的选择",
        "related_npc": ["npc_shan", "npc_tang", "npc_shangren"],
    },
    "isolation": {
        "clue_id": "isolation", "display_name": "村子的桎梏",
        "keywords": ["离开", "外面", "城市", "外界"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {20: "subtle", 50: "cryptic", 70: "near_direct"},
        "correct_player_action": "意识到村子与外界隔绝",
        "related_npc": ["npc_tang", "npc_shi"],
    },
    "grandpa": {
        "clue_id": "grandpa", "display_name": "爷爷的身份",
        "keywords": ["爷爷", "老人", "消失"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic", 80: "near_direct"},
        "correct_player_action": "从山口中得知爷爷=God的真相",
        "related_npc": ["npc_shan", "npc_sui", "npc_mu"],
    },
    "omen": {
        "clue_id": "omen", "display_name": "天灾前兆",
        "keywords": ["红雪", "天灾", "前兆"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {60: "cryptic", 80: "near_direct"},
        "correct_player_action": "意识到天灾即将来临",
        "related_npc": ["npc_shan"],
    },
    "ritual": {
        "clue_id": "ritual", "display_name": "守护仪式",
        "keywords": ["仪式", "传统", "食物消失"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {40: "subtle", 60: "cryptic"},
        "correct_player_action": "观察禾的仪式，发现与契约的关联",
        "related_npc": ["npc_he", "npc_shan"],
    },
    "runes": {
        "clue_id": "runes", "display_name": "法阵组件",
        "keywords": ["符文", "老物件", "修缮"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic"},
        "correct_player_action": "调查木修缮的老物件上的符文",
        "related_npc": ["npc_mu", "npc_shan"],
    },
    "guardian_sight": {
        "clue_id": "guardian_sight", "display_name": "守护者的存在",
        "keywords": ["梦", "夜里", "天上", "眼睛"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic"},
        "correct_player_action": "留意穗和岚婆关于梦境的描述",
        "related_npc": ["npc_sui", "npc_lan"],
    },
    "clairvoyance": {
        "clue_id": "clairvoyance", "display_name": "真假通灵",
        "keywords": ["通灵", "手相", "预言"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic"},
        "correct_player_action": "发现岚婆的通灵是真实的",
        "related_npc": ["npc_lan"],
    },
    "demon_identity": {
        "clue_id": "demon_identity", "display_name": "恶魔身份",
        "keywords": ["商人", "夜晚", "仪式地点"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {60: "cryptic", 80: "near_direct"},
        "correct_player_action": "揭露商人=恶魔的真实身份",
        "related_npc": ["npc_tang", "npc_shangren"],
    },
    "reincarnation": {
        "clue_id": "reincarnation", "display_name": "轮回暗示",
        "keywords": ["等待", "好久了", "上次", "又一次"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic"},
        "correct_player_action": "发现时间轮回的存在",
        "related_npc": ["npc_shan", "npc_tang"],
    },
    "wheel": {
        "clue_id": "wheel", "display_name": "命运之轮",
        "keywords": ["转动", "命运", "又来了"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {60: "cryptic", 80: "near_direct"},
        "correct_player_action": "发现山持有命运之轮，理解轮回机制",
        "related_npc": ["npc_shan"],
    },
}


# ── 信任度配置 ─────────────────────────────────────────────────────────────

# 信任度是per-NPC的（每个NPC独立0-100）
DEFAULT_NPC_TRUST = 0
MAX_NPC_TRUST = 100

TRUST_DELTAS = {
    "help_npc": 5,            # 帮助NPC完成任务
    "gift_item": 3,           # 送礼
    "positive_dialogue": 2,   # 友善对话
    "negative_dialogue": -3,  # 恶意对话
    "ignore_request": -2,     # 忽略NPC请求
    "explore_clue": 5,        # 探索相关线索
    "deep_conversation": 4,   # 深入对话
    "visit_npc": 2,           # 拜访NPC
}

# 叙事阶段进阶条件（基于最高单NPC信任度）
STAGE_ADVANCEMENT = {
    1: {"min_day": 29, "any_npc_trust": 0},
    2: {"min_day": 57, "any_npc_trust": 30},
    3: {"min_day": 85, "any_npc_trust": 70, "min_clues": 3},
}


# ── 结局触发条件 ──────────────────────────────────────────────────────────

ENDING_CONDITIONS = {
    "failure": {
        "name": "结局1·失败——愚者的坠落",
        "description": "天灾到来时未发现爷爷=God的真相",
        "tarot": "0 愚者坠落",
        "conditions": {
            "min_day": 112,
            "secret_stage_below": 3,
        },
        "unlock_requirement": None,
    },
    "reinforce": {
        "name": "结局2·巩固——皇帝的秩序",
        "description": "帮助爷爷加固结界",
        "tarot": "IV 皇帝的秩序",
        "conditions": {
            "secret_stage": 3,
            "any_npc_trust": 50,
            "has_core_materials": True,
            "choice": "reinforce",
        },
        "unlock_requirement": None,
    },
    "overthrow": {
        "name": "结局3·推翻——走过皇帝",
        "description": "拒绝结界，寻找另一条路",
        "tarot": "超越IV皇帝",
        "conditions": {
            "secret_stage": 3,
            "any_npc_trust": 70,
            "choice": "overthrow",
        },
        "unlock_requirement": None,
    },
    "trade_replace": {
        "name": "结局4A·替代——新的守护者",
        "description": "与恶魔签约，成为新的God",
        "tarot": "XV 恶魔的锁链",
        "conditions": {
            "secret_stage": 3,
            "demon_revealed": True,
            "tang_sacrificed": True,
            "choice": "trade_replace",
        },
        "unlock_requirement": ["reinforce", "overthrow"],
    },
    "trade_twisted": {
        "name": "结局4B·扭曲的自由——恶魔的公平",
        "description": "借恶魔之力解放所有人，代价扭曲了自由",
        "tarot": "XV 恶魔的公平",
        "conditions": {
            "secret_stage": 3,
            "demon_revealed": True,
            "tang_sacrificed": True,
            "choice": "trade_freedom",
        },
        "unlock_requirement": ["reinforce", "overthrow"],
    },
    "awakening": {
        "name": "结局5·觉醒——命运之轮",
        "description": "意识到轮回，获得存档意识",
        "tarot": "X 命运之轮",
        "conditions": {
            "reincarnation_clues": True,
            "npc_trust_shan": 90,
            "deja_vu_triggered": True,
        },
        "unlock_requirement": None,  # 独立于爷爷线和恶魔线
    },
    "world": {
        "name": "真结局·世界——打破所有墙",
        "description": "走完愚者之旅全部22张牌",
        "tarot": "XXI 世界",
        "conditions": {
            "all_endings_achieved": True,
            "all_achievements": True,
            "awakening_active": True,
            "fools_journey_complete": True,
        },
        "unlock_requirement": ["failure", "reinforce", "overthrow",
                               "trade_replace", "trade_twisted", "awakening"],
    },
}


# ── 角色关系权重 ──────────────────────────────────────────────────────────

# 影响NPC之间的互动频率：weight 0-10
RELATIONSHIP_WEIGHTS = {
    # 核心关系
    ("npc_he", "npc_sui"):    {"weight": 10, "type": "family"},        # 母女
    ("npc_lan", "npc_shi"):   {"weight": 9,  "type": "family"},        # 母子
    ("npc_shan", "npc_mu"):   {"weight": 7,  "type": "guide"},         # 山指导木维护法阵
    ("npc_shan", "npc_tang"):  {"weight": 6,  "type": "observe"},       # 山观察棠的交易后果
    ("npc_tang", "npc_shangren"): {"weight": 5, "type": "tension"},     # 棠与商人的紧张关系
    # 情感关系
    ("npc_shi", "npc_he"):    {"weight": 8,  "type": "unrequited"},    # 石暗恋禾
    ("npc_he", "npc_shan"):   {"weight": 5,  "type": "respect"},       # 禾尊重山
    ("npc_he", "npc_mu"):     {"weight": 5,  "type": "neighbor"},      # 邻居
    # 感知者网络
    ("npc_sui", "npc_lan"):   {"weight": 7,  "type": "resonance"},     # 双重感知者
    ("npc_sui", "npc_tang"):  {"weight": 5,  "type": "friend"},        # 穗喜欢棠
    ("npc_sui", "npc_kuang"): {"weight": 8,  "type": "playmate"},      # 孩子们一起玩
    # 日常关系
    ("npc_kuang", "npc_mu"):  {"weight": 6,  "type": "apprentice"},    # 旷好奇木的工具
    ("npc_kuang", "npc_shi"): {"weight": 5,  "type": "admire"},        # 旷崇拜猎人
    ("npc_mu", "npc_shan"):   {"weight": 7,  "type": "task"},          # 木为山修缮
    ("npc_lan", "npc_he"):    {"weight": 5,  "type": "neighbor"},      # 邻居
    ("npc_lan", "npc_shan"):  {"weight": 4,  "type": "respect"},       # 尊重
    ("npc_shi", "npc_tang"):  {"weight": 4,  "type": "acquaintance"},  # 同龄相识
    ("npc_shi", "npc_kuang"): {"weight": 4,  "type": "friend"},        # 带旷打猎
    ("npc_he", "npc_tang"):   {"weight": 5,  "type": "concern"},       # 禾关心棠
    ("npc_mu", "npc_lan"):    {"weight": 3,  "type": "neighbor"},      # 邻居
    ("npc_mu", "npc_shi"):    {"weight": 3,  "type": "business"},      # 工具修理
    # 商人与村民
    ("npc_shangren", "npc_he"):  {"weight": 3, "type": "business"},    # 正常交易
    ("npc_shangren", "npc_mu"):  {"weight": 3, "type": "business"},    # 正常交易
    ("npc_shangren", "npc_shan"): {"weight": 2, "type": "wary"},       # 山警惕商人
}


# ── 核心线索列表 ──────────────────────────────────────────────────────────

# 核心线索（触发主线结局所需）
CORE_CLUES = ["barrier", "pact", "isolation", "grandpa", "ritual", "runes"]

# 深层线索（触发隐藏结局/更深层真相所需）
DEEP_CLUES = ["guardian_sight", "clairvoyance", "demon_identity"]

# 轮回线索（触发结局5所需）
REINCARNATION_CLUES = ["reincarnation", "wheel"]

# 所有线索
ALL_CLUES = CORE_CLUES + DEEP_CLUES + REINCARNATION_CLUES


# ── 愚者之旅追踪 ──────────────────────────────────────────────────────────

FOOLS_JOURNEY_STATIONS = {
    0:  {"name": "愚者", "character": "主角", "understanding": "开始旅程"},
    1:  {"name": "魔术师", "character": "石·道具", "understanding": "万能的借用"},
    2:  {"name": "女祭司", "character": "岚婆", "understanding": "帷幕两侧"},
    3:  {"name": "皇后", "character": "禾", "understanding": "爱的温暖与控制"},
    4:  {"name": "皇帝", "character": "爷爷", "understanding": "秩序即禁锢"},
    5:  {"name": "教皇", "character": "木", "understanding": "传统的不自知"},
    6:  {"name": "恋人", "character": "石", "understanding": "选择的勇气"},
    7:  {"name": "战车", "character": "旷·道具", "understanding": "意志的冲击"},
    8:  {"name": "力量", "character": "旷", "understanding": "天真的无畏"},
    9:  {"name": "隐者", "character": "山", "understanding": "沉默的全知"},
    10: {"name": "命运之轮", "character": "山·道具", "understanding": "轮回觉醒"},
    11: {"name": "正义", "character": "商人·道具", "understanding": "公平的陷阱"},
    12: {"name": "倒吊人", "character": "棠", "understanding": "牺牲与视角"},
    13: {"name": "死神", "character": "爷爷·道具", "understanding": "终结与转化"},
    14: {"name": "节制", "character": "木·道具", "understanding": "平衡打破"},
    15: {"name": "恶魔", "character": "商人", "understanding": "交易与锁链"},
    16: {"name": "塔", "character": "棠·道具", "understanding": "结构崩塌"},
    17: {"name": "星星", "character": "禾·道具", "understanding": "废墟中的希望"},
    18: {"name": "月亮", "character": "岚婆·道具", "understanding": "幻觉与真相"},
    19: {"name": "太阳", "character": "穗", "understanding": "纯粹之光"},
    20: {"name": "审判", "character": "穗·道具", "understanding": "终极审视"},
    21: {"name": "世界", "character": "主角·道具", "understanding": "打破一切墙"},
}


# ── 感知层级 ──────────────────────────────────────────────────────────────

PERCEPTION_LEVELS = {
    "god":          {"level": "omniscient",  "description": "秘密的制造者"},
    "npc_shan":     {"level": "omniscient",  "description": "轮回的见证者"},
    "npc_shangren": {"level": "transcendent", "description": "不受结界/轮回约束"},
    "npc_sui":      {"level": "strongest",   "description": "无屏障，直觉穿透一切"},
    "npc_lan":      {"level": "strong",      "description": "真感知以骗术形式流出"},
    "npc_tang":     {"level": "medium_strong", "description": "交易后屏障部分破碎"},
    "npc_kuang":    {"level": "medium",      "description": "儿童天然抵抗，无法理解"},
    "player":       {"level": "weak",        "description": "刚回来，渐染中"},
    "npc_shi":      {"level": "weak",        "description": "自以为有，实无"},
    "npc_he":       {"level": "blocked",     "description": "强屏障，从未质疑"},
    "npc_mu":       {"level": "blocked",     "description": "强屏障，从未质疑"},
}
