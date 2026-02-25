"""Narrative events configuration.

Defines trigger conditions for each narrative stage, clue keywords with
their hint levels, and the "correct player choices" for each clue.
This file is the single source of truth for narrative progression rules.
"""

# ── Narrative stages ────────────────────────────────────────────────────────

# Each stage is a dict with:
#   - "id": stage number (0-3)
#   - "name": human-readable name
#   - "description": what this stage represents
#   - "trigger_conditions": conditions that must be met to ENTER this stage
#   - "events": list of events that can occur during this stage

NARRATIVE_STAGES = [
    {
        "id": 0,
        "name": "正常村居",
        "description": "温馨的日常生活，玩家熟悉世界规则和NPC",
        "trigger_conditions": {
            # Stage 0 is the starting state, no trigger needed
        },
        "events": [
            {
                "event_id": "welcome",
                "description": "NPC热情欢迎玩家",
                "condition": {"type": "first_talk"},
            },
            {
                "event_id": "topic_avoidance",
                "description": "NPC回避某些话题",
                "condition": {"type": "forbidden_topic_touched"},
            },
        ],
    },
    {
        "id": 1,
        "name": "异常浮现",
        "description": "微妙的不安感，小异常开始出现",
        "trigger_conditions": {
            "min_day": 6,
            # Any ONE of these conditions is sufficient:
            "any_of": [
                {"min_day": 6},
                {"min_trust": 15},
            ],
        },
        "events": [
            {
                "event_id": "forbidden_land",
                "description": "西边废弃农庄区域出现异常描述",
                "condition": {"min_day": 6},
            },
            {
                "event_id": "nightmares",
                "description": "NPC偶尔提到奇怪的梦",
                "condition": {"min_day": 8},
            },
            {
                "event_id": "well_sounds",
                "description": "老井夜里传来声音",
                "condition": {"min_day": 10, "time_phase": "night"},
            },
            {
                "event_id": "old_photo",
                "description": "老照片里有陌生人",
                "condition": {"player_explored_house": True},
            },
            {
                "event_id": "night_light",
                "description": "夜里地图某处出现短暂的光源",
                "condition": {"min_day": 10},
            },
        ],
    },
    {
        "id": 2,
        "name": "碎片期",
        "description": "信任建立后，NPC开始透露碎片信息",
        "trigger_conditions": {
            "min_day": 16,
            "min_trust": 30,
        },
        "events": [
            {
                "event_id": "mention_grandpa",
                "description": "NPC偶然提起爷爷，说了一句奇怪的话",
                "condition": {"min_trust": 30, "any_npc_affinity_above": 30},
            },
            {
                "event_id": "dave_stories",
                "description": "Dave开始主动找玩家讲古老的故事",
                "condition": {"helped_npcs_count": 3},
            },
            {
                "event_id": "bob_warning",
                "description": "Bob警告玩家不要去废弃农庄",
                "condition": {"player_explored_west": True},
            },
            {
                "event_id": "alice_map",
                "description": "Alice拿出草药手册里的地图碎片",
                "condition": {"min_trust": 60},
            },
            {
                "event_id": "carol_ritual",
                "description": "Carol无意间提到村子的仪式",
                "condition": {"min_trust": 50},
            },
        ],
    },
    {
        "id": 3,
        "name": "真相",
        "description": "抉择与揭示，天灾前兆出现",
        "trigger_conditions": {
            "min_day": 30,
            "min_trust": 70,
            "min_clues_revealed": 3,
        },
        "events": [
            {
                "event_id": "red_snow",
                "description": "天灾前兆——红雪降临",
                "condition": {"min_day": 30, "min_trust": 70},
            },
            {
                "event_id": "dave_full_truth",
                "description": "Dave揭示爷爷的身份与协议的全部真相",
                "condition": {"min_trust": 80},
            },
            {
                "event_id": "boundary_revealed",
                "description": "村子边界的秘密显现，玩家发现无法离开",
                "condition": {"player_explored_boundary": True},
            },
            {
                "event_id": "final_choice",
                "description": "最终抉择：保护村子 / 打破桎梏",
                "condition": {"all_clues_revealed": True},
            },
        ],
    },
]


# ── Clue keyword definitions ───────────────────────────────────────────────

# Defines what keywords in NPC/player dialogue trigger the hint system.
# Each keyword maps to:
#   - clue_id: unique identifier for the clue
#   - base_hint_level: default hint subtlety level
#   - escalation_thresholds: trust levels at which the hint becomes more direct
#   - correct_player_action: what the player "should" do when they notice this clue

CLUE_DEFINITIONS = {
    "mine": {
        "clue_id": "mine",
        "display_name": "废弃矿山",
        "keywords": ["矿山", "矿区", "废弃"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {
            30: "subtle",    # trust < 30: subtle
            60: "cryptic",   # trust 30-60: cryptic
            80: "near_direct",  # trust > 80: near_direct
        },
        "correct_player_action": "探索西边的废弃矿山，调查矿山被关闭的真正原因",
        "related_npc": "npc_bob",
    },
    "pact": {
        "clue_id": "pact",
        "display_name": "爷爷的协议",
        "keywords": ["老协议", "约定", "承诺"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {
            50: "cryptic",
            80: "near_direct",
        },
        "correct_player_action": "找到协议的内容，理解爷爷为什么做出这个选择",
        "related_npc": "npc_dave",
    },
    "isolation": {
        "clue_id": "isolation",
        "display_name": "村子的桎梏",
        "keywords": ["离开", "外面", "城市", "外界"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {
            20: "subtle",
            50: "cryptic",
            70: "near_direct",
        },
        "correct_player_action": "尝试走到地图边缘，发现无法离开；追问NPC关于'外面'的认知",
        "related_npc": None,
    },
    "grandpa": {
        "clue_id": "grandpa",
        "display_name": "爷爷的身份",
        "keywords": ["爷爷", "老人", "消失"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {
            30: "subtle",
            60: "cryptic",
            80: "near_direct",
        },
        "correct_player_action": "收集所有关于爷爷的线索，最终从Dave口中得知真相",
        "related_npc": "npc_dave",
    },
    "omen": {
        "clue_id": "omen",
        "display_name": "天灾前兆",
        "keywords": ["红雪"],
        "base_hint_level": "cryptic",
        "escalation_thresholds": {
            60: "cryptic",
            80: "near_direct",
        },
        "correct_player_action": "意识到天灾即将来临，加速收集线索并做出准备",
        "related_npc": None,
    },
    "west": {
        "clue_id": "west",
        "display_name": "西边的秘密",
        "keywords": ["西边", "废弃农庄"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {
            20: "subtle",
            50: "cryptic",
        },
        "correct_player_action": "不顾Bob的警告，探索西边区域，找到隐藏的线索",
        "related_npc": "npc_alice",
    },
    "ritual": {
        "clue_id": "ritual",
        "display_name": "村子的仪式",
        "keywords": ["仪式", "传统"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {
            40: "subtle",
            60: "cryptic",
        },
        "correct_player_action": "观察Carol的仪式，发现仪式与爷爷协议之间的关联",
        "related_npc": "npc_carol",
    },
    "map": {
        "clue_id": "map",
        "display_name": "神秘地图",
        "keywords": ["地图", "手册"],
        "base_hint_level": "subtle",
        "escalation_thresholds": {
            40: "subtle",
            60: "cryptic",
        },
        "correct_player_action": "获得Alice保管的地图碎片，拼合后找到目标位置",
        "related_npc": "npc_alice",
    },
}


# ── Trust level thresholds ──────────────────────────────────────────────────

# Trust changes per player action type
TRUST_DELTAS = {
    "help_npc": 5,          # 帮助NPC完成请求
    "gift_item": 3,         # 给NPC物品
    "positive_dialogue": 2, # 友好的对话选择
    "negative_dialogue": -3,  # 敌对的对话选择
    "ignore_request": -2,   # 忽略NPC的求助
    "explore_clue": 5,      # 主动探索线索相关区域
}

# Stage advancement thresholds
STAGE_ADVANCEMENT = {
    1: {"min_day": 6, "min_trust": 0},      # 进入异常浮现
    2: {"min_day": 16, "min_trust": 30},     # 进入碎片期
    3: {"min_day": 30, "min_trust": 70, "min_clues": 3},  # 进入真相
}
