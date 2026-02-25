"""Narrative events configuration.

Defines trigger conditions for each narrative stage, clue keywords with
their hint levels, ending trigger conditions, and character relationship
weights. This file is the single source of truth for narrative progression rules.

设计决策：
- 所有叙事规则集中在这一个文件里，方便调整和测试
- 结局触发条件独立配置，支持多周目解锁
- 角色关系权重影响NPC互动频率（数值越高越容易互动）
"""

# ── Narrative stages ────────────────────────────────────────────────────────

NARRATIVE_STAGES = [
    {
        "id": 0,
        "name": "正常村居",
        "description": "温馨的日常生活，玩家熟悉世界规则和NPC",
        "trigger_conditions": {},
        "events": [
            {"event_id": "welcome", "description": "NPC热情欢迎玩家", "condition": {"type": "first_talk"}},
            {"event_id": "lily_intro", "description": "Lily第一次出场", "condition": {"min_day": 2}},
            {"event_id": "marco_greeting", "description": "Marco热情搭话", "condition": {"type": "player_near_marco"}},
            {"event_id": "topic_avoidance", "description": "NPC回避某些话题", "condition": {"type": "forbidden_topic_touched"}},
        ],
    },
    {
        "id": 1,
        "name": "异常浮现",
        "description": "微妙的不安感，小异常开始出现",
        "trigger_conditions": {"min_day": 6, "any_of": [{"min_day": 6}, {"min_trust": 15}]},
        "events": [
            {"event_id": "forbidden_land", "description": "西边废弃农庄区域异常", "condition": {"min_day": 6}},
            {"event_id": "nightmares", "description": "NPC偶尔提到奇怪的梦", "condition": {"min_day": 8}},
            {"event_id": "well_sounds", "description": "老井夜里传来低语", "condition": {"min_day": 10, "time_phase": "night"}},
            {"event_id": "old_photo", "description": "老照片里有看不清脸的人", "condition": {"player_explored_house": True}},
            {"event_id": "night_light", "description": "夜里短暂光源", "condition": {"min_day": 10}},
            {"event_id": "lily_strange_words", "description": "Lily说奇怪的话", "condition": {"min_day": 7}},
            {"event_id": "chen_weaving_pause", "description": "陈婆编织时停下", "condition": {"min_day": 9, "player_visited_chen": True}},
            {"event_id": "erik_warm_metal", "description": "Erik提到老物件有温度", "condition": {"min_day": 12, "player_visited_erik": True}},
        ],
    },
    {
        "id": 2,
        "name": "碎片期",
        "description": "信任建立后NPC透露碎片信息",
        "trigger_conditions": {"min_day": 16, "min_trust": 30},
        "events": [
            {"event_id": "mention_grandpa", "description": "NPC偶然提起爷爷", "condition": {"min_trust": 30, "any_npc_affinity_above": 30}},
            {"event_id": "dave_stories", "description": "Dave主动讲古老的故事", "condition": {"helped_npcs_count": 3}},
            {"event_id": "bob_warning", "description": "Bob警告不要去废弃农庄", "condition": {"player_explored_west": True}},
            {"event_id": "alice_map", "description": "Alice拿出地图碎片", "condition": {"min_trust": 60}},
            {"event_id": "carol_ritual", "description": "Carol无意间提到仪式", "condition": {"min_trust": 50}},
            {"event_id": "marco_time_paradox", "description": "Marco的时间矛盾", "condition": {"min_trust": 40, "player_deep_talk_marco": True}},
            {"event_id": "erik_box_notes", "description": "Erik发现锻造笔记", "condition": {"min_trust": 50, "player_helped_erik": True}},
            {"event_id": "chen_dream_name", "description": "陈婆梦中喊出爷爷名字", "condition": {"min_trust": 40, "player_visited_chen_count": 3}},
            {"event_id": "lily_drawing", "description": "Lily画了被光包围的老人", "condition": {"min_day": 20}},
        ],
    },
    {
        "id": 3,
        "name": "真相",
        "description": "抉择与揭示，天灾前兆出现",
        "trigger_conditions": {"min_day": 30, "min_trust": 70, "min_clues_revealed": 3},
        "events": [
            {"event_id": "red_snow", "description": "天灾前兆——红雪", "condition": {"min_day": 30, "min_trust": 70}},
            {"event_id": "dave_full_truth", "description": "Dave揭示全部真相", "condition": {"min_trust": 80}},
            {"event_id": "boundary_revealed", "description": "村子边界秘密显现", "condition": {"player_explored_boundary": True}},
            {"event_id": "erik_array_truth", "description": "Erik理解老物件真相", "condition": {"min_trust": 70, "erik_seen_notes": True}},
            {"event_id": "chen_memory_restore", "description": "陈婆记忆恢复", "condition": {"min_trust": 80}},
            {"event_id": "final_choice", "description": "最终抉择", "condition": {"all_core_clues_revealed": True}},
        ],
    },
]


# ── Clue keyword definitions ───────────────────────────────────────────────

CLUE_DEFINITIONS = {
    "mine": {
        "clue_id": "mine", "display_name": "废弃矿山",
        "keywords": ["矿山", "矿区", "废弃"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic", 80: "near_direct"},
        "correct_player_action": "探索西边废弃矿山，调查关闭原因",
        "related_npc": "npc_bob",
    },
    "pact": {
        "clue_id": "pact", "display_name": "恶魔契约",
        "keywords": ["老协议", "约定", "承诺", "契约"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {50: "cryptic", 80: "near_direct"},
        "correct_player_action": "找到契约内容，理解爷爷的选择",
        "related_npc": "npc_dave",
    },
    "isolation": {
        "clue_id": "isolation", "display_name": "村子的桎梏",
        "keywords": ["离开", "外面", "城市", "外界"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {20: "subtle", 50: "cryptic", 70: "near_direct"},
        "correct_player_action": "走到地图边缘发现无法离开",
        "related_npc": None,
    },
    "grandpa": {
        "clue_id": "grandpa", "display_name": "爷爷的身份",
        "keywords": ["爷爷", "老人", "消失"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic", 80: "near_direct"},
        "correct_player_action": "收集爷爷线索，从Dave口中得知真相",
        "related_npc": "npc_dave",
    },
    "omen": {
        "clue_id": "omen", "display_name": "天灾前兆",
        "keywords": ["红雪"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {60: "cryptic", 80: "near_direct"},
        "correct_player_action": "意识到天灾即将来临",
        "related_npc": None,
    },
    "west": {
        "clue_id": "west", "display_name": "西边的秘密",
        "keywords": ["西边", "废弃农庄"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {20: "subtle", 50: "cryptic"},
        "correct_player_action": "探索西边区域找到隐藏线索",
        "related_npc": "npc_alice",
    },
    "ritual": {
        "clue_id": "ritual", "display_name": "守护仪式",
        "keywords": ["仪式", "传统", "食物消失"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {40: "subtle", 60: "cryptic"},
        "correct_player_action": "观察Carol的仪式，发现与契约的关联",
        "related_npc": "npc_carol",
    },
    "map": {
        "clue_id": "map", "display_name": "法阵地图",
        "keywords": ["地图", "手册", "碎片"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {40: "subtle", 60: "cryptic"},
        "correct_player_action": "获得地图碎片找到法阵核心",
        "related_npc": "npc_alice",
    },
    # ── 新增线索（适配新角色）──
    "forge": {
        "clue_id": "forge", "display_name": "法阵组件",
        "keywords": ["锻造", "老物件", "修缮"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic"},
        "correct_player_action": "调查Erik修缮的老物件",
        "related_npc": "npc_erik",
    },
    "forge_notes": {
        "clue_id": "forge_notes", "display_name": "锻造笔记",
        "keywords": ["箱子", "笔记", "图纸"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {50: "cryptic", 80: "near_direct"},
        "correct_player_action": "找到爷爷的锻造笔记",
        "related_npc": "npc_erik",
    },
    "guardian_sight": {
        "clue_id": "guardian_sight", "display_name": "守护者的存在",
        "keywords": ["梦", "夜里", "天上", "眼睛"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic"},
        "correct_player_action": "留意Lily和陈婆关于梦境的描述",
        "related_npc": "npc_lily",
    },
    "time_warp": {
        "clue_id": "time_warp", "display_name": "时间扭曲",
        "keywords": ["明天走", "旅行", "多久了"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {30: "subtle", 60: "cryptic"},
        "correct_player_action": "发现Marco被困了十几年",
        "related_npc": "npc_marco",
    },
    "weaving": {
        "clue_id": "weaving", "display_name": "法阵图案",
        "keywords": ["编织", "绳子", "图案"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {40: "cryptic", 70: "near_direct"},
        "correct_player_action": "发现编织图案与法阵组件的一致性",
        "related_npc": "npc_chen",
    },
    "demon": {
        "clue_id": "demon", "display_name": "恶魔与代价",
        "keywords": ["恶魔", "力量", "代价"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {60: "cryptic", 80: "near_direct"},
        "correct_player_action": "深入了解恶魔契约的本质",
        "related_npc": "npc_dave",
    },
}


# ── Trust level thresholds ──────────────────────────────────────────────────

TRUST_DELTAS = {
    "help_npc": 5, "gift_item": 3, "positive_dialogue": 2,
    "negative_dialogue": -3, "ignore_request": -2, "explore_clue": 5,
    "talk_to_minor_npc": 2, "visit_chen": 3, "play_with_lily": 2,
}

STAGE_ADVANCEMENT = {
    1: {"min_day": 6, "min_trust": 0},
    2: {"min_day": 16, "min_trust": 30},
    3: {"min_day": 30, "min_trust": 70, "min_clues": 3},
}


# ── 结局触发条件 ──────────────────────────────────────────────────────────

ENDING_CONDITIONS = {
    "normal": {
        "name": "正常结局", "description": "顺从引导，加固契约和法阵",
        "conditions": {"secret_stage": 3, "min_trust": 50, "has_materials": True, "choice": "reinforce"},
        "unlock_requirement": None,
    },
    "hidden_1": {
        "name": "隐藏结局1", "description": "寻找另一条路——与恶魔做新交易",
        "conditions": {"secret_stage": 3, "min_trust": 90, "all_clues": True, "erik_notes_found": True, "choice": "new_path"},
        "unlock_requirement": "normal",
    },
    "hidden_2": {
        "name": "隐藏结局2", "description": "终结一切——杀死恶魔",
        "conditions": {"secret_stage": 3, "min_trust": 100, "all_clues": True, "demon_weakness_found": True, "choice": "end_all"},
        "unlock_requirement": "hidden_1",
    },
}


# ── 角色关系权重 ──────────────────────────────────────────────────────────

# 影响NPC之间的互动频率：weight 0-10
RELATIONSHIP_WEIGHTS = {
    ("npc_bob", "npc_erik"): {"weight": 9, "type": "friend"},
    ("npc_carol", "npc_lily"): {"weight": 10, "type": "family"},
    ("npc_dave", "npc_erik"): {"weight": 7, "type": "guide"},
    ("npc_dave", "npc_lily"): {"weight": 8, "type": "family"},
    ("npc_alice", "npc_carol"): {"weight": 7, "type": "friend"},
    ("npc_alice", "npc_lily"): {"weight": 6, "type": "friend"},
    ("npc_carol", "npc_dave"): {"weight": 6, "type": "guide"},
    ("npc_bob", "npc_dave"): {"weight": 5, "type": "observe"},
    ("npc_dave", "npc_chen"): {"weight": 7, "type": "friend"},
    ("npc_chen", "npc_lily"): {"weight": 6, "type": "family"},
    ("npc_erik", "npc_lily"): {"weight": 5, "type": "friend"},
    ("npc_alice", "npc_bob"): {"weight": 4, "type": "friend"},
    ("npc_bob", "npc_carol"): {"weight": 4, "type": "business"},
    ("npc_carol", "npc_erik"): {"weight": 4, "type": "business"},
    ("npc_carol", "npc_marco"): {"weight": 3, "type": "business"},
    ("npc_alice", "npc_marco"): {"weight": 4, "type": "friend"},
    ("npc_dave", "npc_marco"): {"weight": 4, "type": "observe"},
    ("npc_lily", "npc_marco"): {"weight": 5, "type": "friend"},
    ("npc_alice", "npc_chen"): {"weight": 3, "type": "friend"},
    ("npc_bob", "npc_marco"): {"weight": 2, "type": "observe"},
    ("npc_bob", "npc_chen"): {"weight": 3, "type": "observe"},
    ("npc_erik", "npc_marco"): {"weight": 2, "type": "business"},
    ("npc_erik", "npc_chen"): {"weight": 2, "type": "friend"},
    ("npc_marco", "npc_chen"): {"weight": 1, "type": "observe"},
    ("npc_carol", "npc_chen"): {"weight": 4, "type": "friend"},
    ("npc_alice", "npc_erik"): {"weight": 3, "type": "friend"},
    ("npc_alice", "npc_dave"): {"weight": 3, "type": "observe"},
    ("npc_bob", "npc_lily"): {"weight": 4, "type": "friend"},
}


# ── 次要角色配置 ──────────────────────────────────────────────────────────

MINOR_NPC_IDS = {"npc_marco", "npc_chen"}

MINOR_NPC_CONFIG = {
    "npc_marco": {"is_minor": True, "think_interval_multiplier": 3.0},
    "npc_chen": {"is_minor": True, "think_interval_multiplier": 3.0},
}


# ── 核心线索列表 ──────────────────────────────────────────────────────────

CORE_CLUES = ["mine", "pact", "isolation", "grandpa", "ritual", "map", "forge"]
HIDDEN_ENDING_CLUES = ["forge_notes", "guardian_sight", "time_warp", "weaving", "demon"]
