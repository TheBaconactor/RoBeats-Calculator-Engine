-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_8 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_9 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
require(game.ReplicatedStorage.Avatar.ElementalColor)
require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_10 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v11 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
local v12 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v14 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_15 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_16 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_17 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v19 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_20 = nil
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
v19:require_client(function() --[[ Line: 32 ]]
    --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (ref 3): v_u_22, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_25 ]]
    v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_24 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_25 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
end)
local v_u_26 = {
    ["Node"] = {}
}
local v_u_27 = v_u_2:new()
local v_u_28 = 1
v_u_26.Node.new = function(_, p_u_29) --[[ Name: new ]] --[[ Line: 48 ]]
    --[[ Upvalues: (ref 1): v_u_28, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_5, (copy 5): v_u_10, (copy 6): v_u_27 ]]
    local v30 = {}
    local v_u_31 = v_u_28
    v_u_28 = v_u_28 + 1
    local v_u_32 = v_u_3:new()
    local v_u_33 = v_u_3:new()
    local v_u_34 = 0
    local v_u_35 = v_u_1:important_assetid()
    v30.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 58 ]]
        --[[ Upvalues: (copy 1): v_u_31 ]]
        return v_u_31;
    end;
    v30.get_display_name = function(_) --[[ Name: get_display_name ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): p_u_29 ]]
        return p_u_29;
    end;
    v30.get_display_icon = function(_) --[[ Name: get_display_icon ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v30.get_children = function(_) --[[ Name: get_children ]] --[[ Line: 61 ]]
        --[[ Upvalues: (copy 1): v_u_32 ]]
        return v_u_32;
    end;
    v30.get_rewards = function(_) --[[ Name: get_rewards ]] --[[ Line: 62 ]]
        --[[ Upvalues: (copy 1): v_u_33 ]]
        return v_u_33;
    end;
    v30.can_add_multiple_of_rewards = function(_) --[[ Name: can_add_multiple_of_rewards ]] --[[ Line: 63 ]]
        --[[ Upvalues: (copy 1): v_u_33 ]]
        local v36 = true
        for _, v37 in v_u_33:key_itr() do
            if v37:can_add_multiple() ~= true then
                return false;
            end;
        end;
        return v36;
    end;
    v30.get_price = function(_) --[[ Name: get_price ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34;
    end;
    v30.set_display_icon = function(p38, p39) --[[ Name: set_display_icon ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        v_u_35 = p39
        return p38;
    end;
    v30.set_price = function(p40, p41) --[[ Name: set_price ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_34 ]]
        v_u_5:is_int_greater_than(p41, 0)
        v_u_34 = p41
        return p40;
    end;
    v30.set_rewards = function(p42, p43) --[[ Name: set_rewards ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_32, (ref 3): v_u_3, (ref 4): v_u_10, (ref 5): p_u_29, (ref 6): v_u_35, (copy 7): v_u_33 ]]
        v_u_5:is_true(v_u_32:count() == 0)
        local v44 = v_u_3:new(p43)
        for _, v45 in v44:key_itr() do
            v_u_5:is_true(v45:get_type() ~= v_u_10.RewardType.None)
            if v45:get_amount() == 1 then
                p_u_29 = v45:get_name()
            else
                p_u_29 = v45:get_name_with_amount()
            end;
            v_u_35 = v45:get_image()
        end;
        v_u_33:push_back_from_list(v44)
        return p42;
    end;
    v30.set_children = function(p46, p47) --[[ Name: set_children ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_33, (ref 3): v_u_3, (copy 4): v_u_32 ]]
        v_u_5:is_true(v_u_33:count() == 0)
        local v48 = v_u_3:new(p47)
        for _, v49 in v48:key_itr() do
            if v49:get_price() <= 0 then
                v49:set_price(p46:get_price())
            end;
        end;
        for _, v50 in v48:key_itr() do
            v50:validate_node()
        end;
        v_u_32:push_back_from_list(v48)
        return p46;
    end;
    v30.validate_node = function(_) --[[ Name: validate_node ]] --[[ Line: 107 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_29, (copy 3): v_u_32, (copy 4): v_u_33, (ref 5): v_u_34 ]]
        v_u_5:is_true(#p_u_29 > 0)
        v_u_5:is_true(v_u_32:count() > 0 and true or v_u_33:count() > 0)
        if v_u_33:count() > 0 then
            v_u_5:is_true(v_u_34 > 0)
        end;
    end;
    v30.get_rewards_list_copy = function(_) --[[ Name: get_rewards_list_copy ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_33 ]]
        return v_u_10:list_copy(v_u_33);
    end;
    v_u_27:add(v_u_31, v30)
    return v30;
end;
local function f_Node(...) --[[ Name: Node ]] --[[ Line: 120 ]]
    --[[ Upvalues: (copy 1): v_u_26 ]]
    return v_u_26.Node:new(...);
end;
local function f_fevericon_id_to_materialid(p51) --[[ Name: fevericon_id_to_materialid ]] --[[ Line: 122 ]]
    --[[ Upvalues: (copy 1): v_u_18, (copy 2): v_u_7, (copy 3): v_u_4 ]]
    local v52 = v_u_18:singleton():get_fevericon_for_id(p51):get_material_id()
    if v_u_7:singleton():contains_material(v52) == true then
        return v52;
    else
        return v_u_4:errf("fevericon_id_to_materialid(%d)=%s not found", p51, (tostring(v52)));
    end;
end;
local function f_node_fever_icon(p53) --[[ Name: node_fever_icon ]] --[[ Line: 131 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_9, (copy 4): f_Node, (copy 5): v_u_10 ]]
    v_u_5:is_true(v_u_7:singleton():get_material_type(p53) == v_u_9.Type.FeverIcon)
    return f_Node():set_rewards({ v_u_10.RewardInfo:new(v_u_10.RewardType.CraftingMaterials, 1, p53) });
end;
local function f_node_rare_blueprint(p54) --[[ Name: node_rare_blueprint ]] --[[ Line: 138 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_9, (copy 4): f_Node, (copy 5): v_u_10 ]]
    v_u_5:is_true(v_u_7:singleton():get_material_type(p54) == v_u_9.Type.Blueprint)
    v_u_5:is_true(v_u_7:singleton():get_material_tier(p54) == v_u_9.Tier.T3)
    return f_Node():set_rewards({ v_u_10.RewardInfo:new(v_u_10.RewardType.CraftingMaterials, 1, p54) });
end;
local function f_node_legendary_blueprint(p55) --[[ Name: node_legendary_blueprint ]] --[[ Line: 146 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_9, (copy 4): f_Node, (copy 5): v_u_10 ]]
    v_u_5:is_true(v_u_7:singleton():get_material_type(p55) == v_u_9.Type.Blueprint)
    v_u_5:is_true(v_u_7:singleton():get_material_tier(p55) == v_u_9.Tier.T4)
    return f_Node():set_rewards({ v_u_10.RewardInfo:new(v_u_10.RewardType.CraftingMaterials, 1, p55) });
end;
local function f_node_box(p56, p57, p58) --[[ Name: node_box ]] --[[ Line: 154 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_9, (copy 4): f_Node, (copy 5): v_u_10 ]]
    v_u_5:is_int_greater_than(p58, 0)
    v_u_5:is_int_greater_than(p57, 0)
    v_u_5:is_true(v_u_7:singleton():get_material_type(p56) == v_u_9.Type.Box)
    return f_Node():set_rewards({ v_u_10.RewardInfo:new(v_u_10.RewardType.CraftingMaterials, p57, p56) }):set_price(p58);
end;
local function f_dance_tablist_of_rarity(p59) --[[ Name: dance_tablist_of_rarity ]] --[[ Line: 164 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_13, (copy 3): f_Node, (copy 4): v_u_10 ]]
    local v60 = v_u_3:new()
    for v61, v62 in v_u_13:singleton():key_itr() do
        if v61 >= 250 then
            break;
        end;
        if v62:get_dance_rarity() == p59 then
            v60:push_front(f_Node():set_rewards({ v_u_10.RewardInfo:new(v_u_10.RewardType.Dance, 1, v61) }))
        end;
    end;
    return v60:get_table();
end;
local v_u_75 = f_Node("Leaderboard Ticket Exchange"):set_children({
    f_Node("Boxes"):set_children({
        f_node_box(v12:get_small_note_box_id(), 1, 1),
        f_node_box(v12:get_medium_note_box_id(), 1, 2),
        f_node_box(v12:get_large_note_box_id(), 1, 3),
        f_node_box(v12:get_gem_box_id(), 1, 5),
        f_node_box(v12:get_mini_1star_box_id(), 1, 15),
        f_node_box(v12:get_mini_2star_box_id(), 1, 30),
        f_node_box(v12:get_token_box_id(), 1, 35),
        f_node_box(v12:get_vip_song_normal_box_id(), 1, 50),
        f_node_box(v12:get_vip_song_hard_box_id(), 1, 150)
    }),
    f_Node("Gear Blueprints"):set_children({ f_Node("Rare Blueprints"):set_price(25):set_children({
            f_node_rare_blueprint(57),
            f_node_rare_blueprint(58),
            f_node_rare_blueprint(59),
            f_node_rare_blueprint(60),
            f_node_rare_blueprint(61),
            f_node_rare_blueprint(62),
            f_node_rare_blueprint(69),
            f_node_rare_blueprint(70),
            f_node_rare_blueprint(71),
            f_node_rare_blueprint(72),
            f_node_rare_blueprint(73),
            f_node_rare_blueprint(74),
            f_node_rare_blueprint(81),
            f_node_rare_blueprint(82),
            f_node_rare_blueprint(83),
            f_node_rare_blueprint(84),
            f_node_rare_blueprint(85),
            f_node_rare_blueprint(86),
            f_node_rare_blueprint(93),
            f_node_rare_blueprint(94),
            f_node_rare_blueprint(95),
            f_node_rare_blueprint(96),
            f_node_rare_blueprint(97),
            f_node_rare_blueprint(98),
            f_node_rare_blueprint(105),
            f_node_rare_blueprint(106),
            f_node_rare_blueprint(107),
            f_node_rare_blueprint(108),
            f_node_rare_blueprint(109),
            f_node_rare_blueprint(110)
        }), f_Node("Legendary Blueprints"):set_price(150):set_children({
            f_node_legendary_blueprint(63),
            f_node_legendary_blueprint(64),
            f_node_legendary_blueprint(65),
            f_node_legendary_blueprint(66),
            f_node_legendary_blueprint(67),
            f_node_legendary_blueprint(68),
            f_node_legendary_blueprint(75),
            f_node_legendary_blueprint(76),
            f_node_legendary_blueprint(77),
            f_node_legendary_blueprint(78),
            f_node_legendary_blueprint(79),
            f_node_legendary_blueprint(80),
            f_node_legendary_blueprint(87),
            f_node_legendary_blueprint(88),
            f_node_legendary_blueprint(89),
            f_node_legendary_blueprint(90),
            f_node_legendary_blueprint(91),
            f_node_legendary_blueprint(92),
            f_node_legendary_blueprint(99),
            f_node_legendary_blueprint(100),
            f_node_legendary_blueprint(101),
            f_node_legendary_blueprint(102),
            f_node_legendary_blueprint(103),
            f_node_legendary_blueprint(104),
            f_node_legendary_blueprint(111),
            f_node_legendary_blueprint(112),
            f_node_legendary_blueprint(113),
            f_node_legendary_blueprint(114),
            f_node_legendary_blueprint(115),
            f_node_legendary_blueprint(116)
        }) }),
    f_Node("Dances"):set_children({ f_Node("Common Dances"):set_price(10):set_children(f_dance_tablist_of_rarity(v14.Common)), f_Node("Rare Dances"):set_price(20):set_children(f_dance_tablist_of_rarity(v14.Rare)), f_Node("Epic Dances"):set_price(50):set_children(f_dance_tablist_of_rarity(v14.Epic)) }),
    f_Node("Gear"):set_children((function() --[[ Name: get_node_tab_of_gear_sorted_by_rarity ]] --[[ Line: 177 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_15, (copy 4): v_u_16, (copy 5): f_Node, (copy 6): v_u_10 ]]
        local v63 = v_u_2:new():add_set_from_table_list({
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            32,
            33,
            34,
            35,
            36,
            37,
            38,
            39,
            40,
            41,
            42,
            43,
            62,
            63,
            64,
            65,
            66,
            67,
            68,
            69,
            70,
            136,
            137,
            138,
            139,
            140,
            141,
            142,
            143,
            144,
            145,
            146,
            147,
            148,
            149,
            150,
            151,
            152,
            153,
            154,
            155,
            156,
            157,
            158,
            159,
            160,
            161,
            162,
            163,
            164,
            165,
            166,
            167,
            168,
            169,
            170,
            171,
            172,
            174,
            175,
            176,
            177,
            178,
            179,
            180,
            181,
            182,
            183,
            184,
            185,
            186,
            187,
            188,
            189,
            173,
            174,
            175,
            176,
            177,
            178,
            179,
            180,
            181,
            182,
            183,
            184,
            185,
            186,
            187,
            188,
            189,
            190,
            191,
            192,
            193,
            194,
            195,
            196,
            197,
            198,
            199,
            200,
            201,
            202,
            224,
            235,
            236,
            239,
            241,
            242
        }):key_list()
        v_u_3:sort_fast(v63, function(p64, p65) --[[ Line: 183 ]]
            return p64 < p65;
        end)
        local v66 = v_u_15:new()
        for _, v67 in v63:key_itr() do
            local v68 = v_u_16:singleton():get_equipment_for_id(v67)
            if v68 then
                v66:push_back_to(v68:get_gear_tier(), v67)
            end;
        end;
        local v69 = v_u_3:new()
        for v70 = 1, 3 do
            if v66:list_of(v70):count() > 0 then
                local v71 = f_Node(string.format("Tier %d", v70))
                local v72 = v70 == 1 and 10 or (v70 == 2 and 25 or 50)
                v71:set_price(v72)
                local v73 = v_u_3:new()
                for _, v74 in v66:list_of(v70):key_itr() do
                    v73:push_front(f_Node():set_rewards({ v_u_10.RewardInfo:new(v_u_10.RewardType.Gear, 1, v74) }):set_price(v72))
                end;
                v71:set_children(v73:get_table())
                v69:push_back(v71)
            end;
        end;
        return v69:get_table();
    end)()),
    f_Node("Icons"):set_children({ f_Node("Classic Icons"):set_price(200):set_children({
            f_node_fever_icon(185),
            f_node_fever_icon(130),
            f_node_fever_icon(128),
            f_node_fever_icon(127),
            f_node_fever_icon(126),
            f_node_fever_icon(124),
            f_node_fever_icon(123),
            f_node_fever_icon(56),
            f_node_fever_icon(120),
            f_node_fever_icon(117),
            f_node_fever_icon(118),
            f_node_fever_icon(25),
            f_node_fever_icon(31),
            f_node_fever_icon(30),
            f_node_fever_icon(29),
            f_node_fever_icon(28),
            f_node_fever_icon(27),
            f_node_fever_icon(26),
            f_node_fever_icon(f_fevericon_id_to_materialid(168)),
            f_node_fever_icon(f_fevericon_id_to_materialid(169)),
            f_node_fever_icon(f_fevericon_id_to_materialid(170))
        }), f_Node("Special Icons"):set_price(500):set_children({
            f_node_fever_icon(f_fevericon_id_to_materialid(216)),
            f_node_fever_icon(f_fevericon_id_to_materialid(212)),
            f_node_fever_icon(f_fevericon_id_to_materialid(200)),
            f_node_fever_icon(f_fevericon_id_to_materialid(172)),
            f_node_fever_icon(f_fevericon_id_to_materialid(162)),
            f_node_fever_icon(f_fevericon_id_to_materialid(135)),
            f_node_fever_icon(f_fevericon_id_to_materialid(53)),
            f_node_fever_icon(f_fevericon_id_to_materialid(112)),
            f_node_fever_icon(f_fevericon_id_to_materialid(67)),
            f_node_fever_icon(f_fevericon_id_to_materialid(68)),
            f_node_fever_icon(f_fevericon_id_to_materialid(94)),
            f_node_fever_icon(261),
            f_node_fever_icon(285),
            f_node_fever_icon(145),
            f_node_fever_icon(f_fevericon_id_to_materialid(76)),
            f_node_fever_icon(227),
            f_node_fever_icon(244),
            f_node_fever_icon(238),
            f_node_fever_icon(173),
            f_node_fever_icon(220),
            f_node_fever_icon(137),
            f_node_fever_icon(149),
            f_node_fever_icon(50),
            f_node_fever_icon(48),
            f_node_fever_icon(24)
        }), f_Node("Challenge Pass Icons"):set_price(1000):set_children({
            f_node_fever_icon(403),
            f_node_fever_icon(402),
            f_node_fever_icon(379),
            f_node_fever_icon(378),
            f_node_fever_icon(377),
            f_node_fever_icon(375),
            f_node_fever_icon(374),
            f_node_fever_icon(376),
            f_node_fever_icon(373),
            f_node_fever_icon(179),
            f_node_fever_icon(52),
            f_node_fever_icon(307),
            f_node_fever_icon(306),
            f_node_fever_icon(182),
            f_node_fever_icon(305),
            f_node_fever_icon(304),
            f_node_fever_icon(303),
            f_node_fever_icon(302),
            f_node_fever_icon(301),
            f_node_fever_icon(300),
            f_node_fever_icon(237),
            f_node_fever_icon(236),
            f_node_fever_icon(235),
            f_node_fever_icon(234),
            f_node_fever_icon(233),
            f_node_fever_icon(232),
            f_node_fever_icon(231),
            f_node_fever_icon(230),
            f_node_fever_icon(229),
            f_node_fever_icon(181),
            f_node_fever_icon(f_fevericon_id_to_materialid(81)),
            f_node_fever_icon(f_fevericon_id_to_materialid(82)),
            f_node_fever_icon(129),
            f_node_fever_icon(119),
            f_node_fever_icon(132),
            f_node_fever_icon(131),
            f_node_fever_icon(54),
            f_node_fever_icon(53),
            f_node_fever_icon(51),
            f_node_fever_icon(49),
            f_node_fever_icon(47),
            f_node_fever_icon(46),
            f_node_fever_icon(45),
            f_node_fever_icon(44),
            f_node_fever_icon(43),
            f_node_fever_icon(42),
            f_node_fever_icon(41),
            f_node_fever_icon(40),
            f_node_fever_icon(39),
            f_node_fever_icon(38),
            f_node_fever_icon(37),
            f_node_fever_icon(36),
            f_node_fever_icon(35),
            f_node_fever_icon(34)
        }) })
})
local v_u_76 = v11:get_leaderboard_ticket_material_id()
v_u_26.client_show_menu = function(_, p_u_77) --[[ Name: client_show_menu ]] --[[ Line: 443 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_76, (ref 3): v_u_21, (copy 4): v_u_10, (ref 5): v_u_24, (copy 6): v_u_6, (copy 7): v_u_17, (ref 8): v_u_23, (ref 9): v_u_22, (ref 10): v_u_25, (copy 11): v_u_5, (copy 12): v_u_75 ]]
    local function f_get_owned_number_of_tickets() --[[ Name: get_owned_number_of_tickets ]] --[[ Line: 444 ]]
        --[[ Upvalues: (copy 1): p_u_77, (ref 2): v_u_8, (ref 3): v_u_76 ]]
        return v_u_8:get_count_of_material(p_u_77._player_blob_manager:get_player_blob(), v_u_76);
    end;
    local function f_show_menu_for_node(p_u_78) --[[ Name: show_menu_for_node ]] --[[ Line: 449 ]]
        --[[ Upvalues: (copy 1): p_u_77, (ref 2): v_u_21, (ref 3): v_u_8, (ref 4): v_u_76, (copy 5): f_show_menu_for_node, (ref 6): v_u_10, (ref 7): v_u_24, (ref 8): v_u_6, (ref 9): v_u_17, (ref 10): v_u_23, (ref 11): v_u_22, (ref 12): v_u_25, (ref 13): v_u_5, (copy 14): f_get_owned_number_of_tickets ]]
        p_u_77._menus:push_menu(v_u_21:new(p_u_77, p_u_77._spui, p_u_77._menus, function(p79) --[[ Line: 454 ]]
            --[[ Upvalues: (copy 1): p_u_78 ]]
            p79:set_header_text(p_u_78:get_display_name())
            p79:get_element_list():push_back_from_list(p_u_78:get_children())
        end, function(p80, p81, p82, _, p83) --[[ Line: 458 ]]
            --[[ Upvalues: (ref 1): p_u_77, (ref 2): v_u_8, (ref 3): v_u_76 ]]
            local v84 = p_u_77._player_blob_manager:get_player_blob()
            p81.Text = p80:get_display_name()
            p82.Image = p80:get_display_icon()
            if p80:get_rewards():count() > 0 then
                p83:get_description_display().Text = string.format("%d Ticket(s)", p80:get_price())
                local v85 = p80:get_price() <= v_u_8:get_count_of_material(p_u_77._player_blob_manager:get_player_blob(), v_u_76)
                if v85 then
                    for _, v86 in p80:get_rewards():key_itr() do
                        if v86:can_playerblob_add(v84) ~= true then
                            v85 = false
                        end;
                    end;
                end;
                p83:set_select_button_enabled(v85)
                p83:set_select_button_text("Exchange")
            else
                if p80:get_price() > 0 then
                    p83:get_description_display().Text = string.format("%d Ticket(s)", p80:get_price())
                else
                    p83:get_description_display().Text = ""
                end;
                p83:set_select_button_enabled(true)
                p83:set_select_button_text("View")
            end;
        end, function(p_u_87) --[[ Line: 484 ]]
            --[[ Upvalues: (ref 1): f_show_menu_for_node, (ref 2): v_u_10, (ref 3): p_u_77, (ref 4): v_u_24, (ref 5): v_u_6, (ref 6): v_u_17, (ref 7): v_u_23, (ref 8): v_u_22, (ref 9): v_u_8, (ref 10): v_u_76, (ref 11): v_u_25, (ref 12): v_u_5 ]]
            if p_u_87 == nil then
                return;
            elseif p_u_87:get_rewards():count() == 0 then
                f_show_menu_for_node(p_u_87)
            else
                local v_u_88 = 1
                local v_u_89 = p_u_87:get_price()
                local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 491 ]]
                    --[[ Upvalues: (copy 1): v_u_89, (ref 2): v_u_88, (ref 3): v_u_10, (copy 4): p_u_87, (ref 5): p_u_77, (ref 6): v_u_24, (ref 7): v_u_6, (ref 8): v_u_17, (ref 9): v_u_23, (ref 10): v_u_22 ]]
                    p_u_77._menus:push_menu(v_u_24:new(p_u_77, p_u_77._spui, p_u_77._menus):set_text("Confirm", (string.format("Are you sure you want to exchange %d Leaderboard Ticket(s) for \"%s\" x%d?", v_u_89 * v_u_88, v_u_10:generate_only_items_description_from_rewardinfo_list(p_u_87:get_rewards()), v_u_88))):set_okay_button_fn(function() --[[ Line: 498 ]]
                        --[[ Upvalues: (ref 1): p_u_77, (ref 2): v_u_24, (ref 3): v_u_6, (ref 4): v_u_17, (ref 5): v_u_23, (ref 6): v_u_10, (ref 7): v_u_22, (ref 8): p_u_87, (ref 9): v_u_88 ]]
                        local v_u_90 = p_u_77._menus:push_menu(v_u_24:new(p_u_77, p_u_77._spui, p_u_77._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_77._evt:wait_on_event_once(v_u_6.EVT_Leaderboard_ServerExchangeTicketResponse, function(p91, p92, p_u_93) --[[ Line: 500 ]]
                            --[[ Upvalues: (ref 1): p_u_77, (copy 2): v_u_90, (ref 3): v_u_24, (ref 4): v_u_17, (ref 5): v_u_23, (ref 6): v_u_10, (ref 7): v_u_22 ]]
                            if p91 ~= true then
                                p_u_77._menus:remove_menu(v_u_90)
                                return p_u_77._menus:push_menu(v_u_24:new(p_u_77, p_u_77._spui, p_u_77._menus):set_text("Error", p92));
                            end;
                            p_u_77._player_blob_manager:do_sync(function() --[[ Line: 505 ]]
                                --[[ Upvalues: (ref 1): p_u_77, (ref 2): v_u_90, (ref 3): v_u_17, (ref 4): v_u_23, (ref 5): v_u_10, (copy 6): p_u_93, (ref 7): v_u_22 ]]
                                p_u_77._menus:remove_menu(v_u_90)
                                if v_u_17.UseRewardDescriptionInfoAcquiredUI == true then
                                    p_u_77._menus:push_menu(v_u_23:new(p_u_77, p_u_77._spui, p_u_77._menus, v_u_10.RewardInfo:table_to_list(p_u_93)):set_header_text("Materials Acquired!"))
                                else
                                    p_u_77._menus:push_menu(v_u_22:new(p_u_77, p_u_77._spui, p_u_77._menus, v_u_10.RewardInfo:table_to_list(p_u_93)))
                                end;
                            end)
                        end)
                        p_u_77._evt:fire_event_to_server(v_u_6.EVT_Leaderboard_ClientExchangeTicket, p_u_87:get_id(), v_u_88)
                    end))
                end;
                local v_u_94 = math.floor(v_u_8:get_count_of_material(p_u_77._player_blob_manager:get_player_blob(), v_u_76) / v_u_89)
                if p_u_87:can_add_multiple_of_rewards() and v_u_94 >= 2 then
                    p_u_77._menus:push_menu(v_u_25:new(p_u_77, p_u_77._spui, p_u_77._menus, v_u_88, function(p95) --[[ Line: 528 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_94, (ref 3): v_u_88, (copy 4): f_do_purchase ]]
                        v_u_5:is_int(p95)
                        v_u_5:is_true(p95 > 0)
                        v_u_5:is_true(p95 <= v_u_94)
                        v_u_88 = p95
                        f_do_purchase()
                    end):set_value_increment(1):set_reset_value(1):set_range_min_max(1, v_u_94):set_title_sub_text("Select Amount", "Select how many you want to buy."):set_value_display_info_fn(function(p96) --[[ Line: 543 ]]
                        --[[ Upvalues: (copy 1): p_u_87, (ref 2): v_u_10, (copy 3): v_u_89 ]]
                        local v97 = p_u_87:get_rewards_list_copy()
                        for _, v98 in v97:key_itr() do
                            v98:set_amount(v98:get_amount() * p96)
                        end;
                        return v_u_10:generate_only_items_description_from_rewardinfo_list(v97), string.format("%d Leaderboard Ticket(s)", v_u_89 * p96);
                    end))
                else
                    f_do_purchase()
                end;
            end;
        end, function(p99) --[[ Line: 558 ]]
            --[[ Upvalues: (ref 1): f_get_owned_number_of_tickets ]]
            p99:set_sub_text(string.format("Owned Ticket(s): %d", f_get_owned_number_of_tickets()))
        end):set_close_on_element_select(false))
    end;
    f_show_menu_for_node(v_u_75)
end;
v_u_26.server_handle_events = function(_, p_u_100) --[[ Name: server_handle_events ]] --[[ Line: 568 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5, (copy 3): v_u_1, (copy 4): v_u_27, (copy 5): v_u_8, (copy 6): v_u_76, (copy 7): v_u_10 ]]
    p_u_100._evt:wait_on_event(v_u_6.EVT_Leaderboard_ClientExchangeTicket, function(p_u_101, p102, p_u_103) --[[ Line: 569 ]]
        --[[ Upvalues: (copy 1): p_u_100, (ref 2): v_u_6, (ref 3): v_u_5, (ref 4): v_u_1, (ref 5): v_u_27, (ref 6): v_u_8, (ref 7): v_u_76, (ref 8): v_u_10 ]]
        local function f_response(p104, p105, p106) --[[ Name: response ]] --[[ Line: 570 ]]
            --[[ Upvalues: (ref 1): p_u_100, (ref 2): v_u_6, (copy 3): p_u_101 ]]
            p_u_100._evt:fire_event_to_client(v_u_6.EVT_Leaderboard_ServerExchangeTicketResponse, p_u_101, p104, p105, p106 == nil and {} or p106)
        end;
        v_u_5:is_int(p_u_103)
        v_u_5:is_true(p_u_103 > 0)
        v_u_5:is_true(p_u_103 < v_u_1:input_max_number())
        local v_u_107 = v_u_27:get(p102)
        if v_u_107 == nil then
            return f_response(false, "null selection");
        end;
        if v_u_107:get_rewards():count() <= 0 then
            return f_response(false, "invalid selection");
        end;
        p_u_100._player_blob_manager:get_verified_cached_blob(p_u_101.UserId, function(p108) --[[ Line: 583 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_76, (copy 3): v_u_107, (ref 4): v_u_5, (copy 5): p_u_103, (copy 6): f_response, (ref 7): v_u_10, (ref 8): p_u_100, (copy 9): p_u_101, (ref 10): v_u_6 ]]
            local v109 = v_u_8:get_count_of_material(p108, v_u_76)
            local v110 = v_u_107:get_price()
            v_u_5:is_true(v110 > 0)
            local v111 = v_u_107:get_price() * p_u_103
            local v112 = math.floor(v109 / v110)
            if v109 < v111 then
                return f_response(false, "not enough tickets(1)");
            end;
            if v112 < p_u_103 then
                return f_response(false, "not enough tickets(2)");
            end;
            v_u_8:add_crafting_materials_of_id(p108, v_u_76, -v111)
            local v113 = v_u_107:get_rewards_list_copy()
            for _, v114 in v113:key_itr() do
                v114:set_amount(v114:get_amount() * p_u_103)
                if v114:can_playerblob_add(p108) ~= true then
                    return f_response(false, "Cannot add this item (Is your inventory full, or do you already own this item?");
                end;
            end;
            v_u_10:server_sync_reward_params(p_u_100, p_u_101, v_u_10:claim_reward_info_list_to_playerblob(p_u_100, p108, v113), function(p115, _, p116) --[[ Line: 608 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_100, (ref 3): v_u_6, (ref 4): p_u_101 ]]
                local v117 = v_u_10.RewardInfo:list_to_table(p116)
                p_u_100._evt:fire_event_to_client(v_u_6.EVT_Leaderboard_ServerExchangeTicketResponse, p_u_101, true, p115, v117 == nil and {} or v117)
            end)
        end)
    end)
end;
return v_u_26;
