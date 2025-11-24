-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_10 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_11 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_12 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_13 = require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_14 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_15 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_16 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_17 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_20 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
local v_u_26 = nil
local v_u_27 = nil
v21:require_client(function() --[[ Line: 32 ]]
    --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_26, (ref 6): v_u_27 ]]
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_25 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_26 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
    v_u_27 = require(game.ReplicatedStorage.Lobby.Menus.PreviewCharacterUI)
end)
local v_u_28 = nil
v21:require_shared(function() --[[ Line: 42 ]]
    --[[ Upvalues: (ref 1): v_u_28 ]]
    v_u_28 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
end)
local v29 = v_u_2:new():add_set_from_table_list({
    495,
    496,
    533,
    534
})
local v30 = v_u_2:new():add_set_from_table_list({})
local v_u_31 = v_u_2:new()
local v32 = v_u_17:singleton()
local l_Normal_0 = v_u_17.SongPriority.Normal
local v_u_33 = v_u_27
local v_u_34 = v_u_28
local v_u_35 = v_u_23
local v_u_36 = v_u_22
local v_u_37 = v_u_24
local v_u_38 = v_u_26
local v_u_39 = v_u_25
local v_u_40 = {}
for v41, _ in v32:all_keys():key_itr() do
    if v32:key_is_vip(v41) == true and (v29:contains(v41) ~= true and (v32:key_is_remix_flagged(v41) ~= true and v32:get_songkey_priority(v41) == l_Normal_0)) then
        v_u_31:add_set(v41)
    end;
end;
v_u_40.type_invalid = function(_) --[[ Name: type_invalid ]] --[[ Line: 72 ]]
    return -1;
end;
v_u_40.get_materialid_box_type = function(_, p42) --[[ Name: get_materialid_box_type ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_40, (copy 3): v_u_10 ]]
    if v_u_9:singleton():contains_material(p42) == true then
        if v_u_9:singleton():get_material_type(p42) == v_u_10.Type.Box then
            return v_u_9:singleton():get_material(p42):get_box_type();
        else
            return v_u_40:type_invalid();
        end;
    else
        return v_u_40:type_invalid();
    end;
end;
v_u_40.get_small_note_box_id = function(_) --[[ Name: get_small_note_box_id ]] --[[ Line: 101 ]]
    return 165;
end;
v_u_40.get_medium_note_box_id = function(_) --[[ Name: get_medium_note_box_id ]] --[[ Line: 102 ]]
    return 166;
end;
v_u_40.get_large_note_box_id = function(_) --[[ Name: get_large_note_box_id ]] --[[ Line: 103 ]]
    return 167;
end;
v_u_40.get_gem_box_id = function(_) --[[ Name: get_gem_box_id ]] --[[ Line: 104 ]]
    return 168;
end;
v_u_40.get_mini_1star_box_id = function(_) --[[ Name: get_mini_1star_box_id ]] --[[ Line: 105 ]]
    return 169;
end;
v_u_40.get_mini_1star_box_not_tradeable_id = function(_) --[[ Name: get_mini_1star_box_not_tradeable_id ]] --[[ Line: 106 ]]
    return 292;
end;
v_u_40.get_vip_song_normal_box_id = function(_) --[[ Name: get_vip_song_normal_box_id ]] --[[ Line: 107 ]]
    return 195;
end;
v_u_40.get_vip_song_hard_box_id = function(_) --[[ Name: get_vip_song_hard_box_id ]] --[[ Line: 108 ]]
    return 196;
end;
v_u_40.get_vip_song_normal_box_not_tradeable_id = function(_) --[[ Name: get_vip_song_normal_box_not_tradeable_id ]] --[[ Line: 109 ]]
    return 271;
end;
v_u_40.get_vip_song_hard_box_not_tradeable_id = function(_) --[[ Name: get_vip_song_hard_box_not_tradeable_id ]] --[[ Line: 110 ]]
    return 272;
end;
v_u_40.get_mini_2star_box_id = function(_) --[[ Name: get_mini_2star_box_id ]] --[[ Line: 111 ]]
    return 199;
end;
v_u_40.get_mini_2star_box_not_tradeable_id = function(_) --[[ Name: get_mini_2star_box_not_tradeable_id ]] --[[ Line: 112 ]]
    return 293;
end;
v_u_40.get_token_box_id = function(_) --[[ Name: get_token_box_id ]] --[[ Line: 113 ]]
    return 249;
end;
v_u_40.get_dance_box_id = function(_) --[[ Name: get_dance_box_id ]] --[[ Line: 114 ]]
    return 367;
end;
v_u_40.get_dance_box_not_tradeable_id = function(_) --[[ Name: get_dance_box_not_tradeable_id ]] --[[ Line: 115 ]]
    return 368;
end;
v_u_40.material_id_to_reward_count = function(_, p43) --[[ Name: material_id_to_reward_count ]] --[[ Line: 117 ]]
    return p43 == 165 and 10 or (p43 == 166 and 5 or (p43 == 167 and 3 or 1));
end;
v_u_40.box_type_multiple_use_enabled = function(_, p44) --[[ Name: box_type_multiple_use_enabled ]] --[[ Line: 129 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    return (p44 == v_u_10.BoxType.SmallNote or (p44 == v_u_10.BoxType.MediumNote or (p44 == v_u_10.BoxType.LargeNote or (p44 == v_u_10.BoxType.Gem or (p44 == v_u_10.BoxType.Token or p44 == v_u_10.BoxType.MiniOneStar))))) and true or p44 == v_u_10.BoxType.MiniTwoStar;
end;
v_u_40.box_type_use_max_count = function(_, _) --[[ Name: box_type_use_max_count ]] --[[ Line: 139 ]]
    return -1;
end;
local v_u_45 = v_u_2:new()
for _, v46 in pairs(v_u_14.Rarity) do
    v_u_45:add(v46, v_u_2:new())
end;
for _, v47 in v_u_13:singleton():get_pet_id_list():key_itr() do
    if v30:contains(v47) ~= true then
        v_u_45:get(v_u_13:singleton():get_data_for_petid(v47):get_rarity()):add_set(v47)
    end;
end;
local function f_get_rarity_petids_set_for_selection(p48, p49) --[[ Name: get_rarity_petids_set_for_selection ]] --[[ Line: 160 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4 ]]
    local v50 = v_u_2:new()
    if p49:contains(p48) then
        v50 = p49:get(p48)
    end;
    if v50:count() == 0 then
        v_u_4:warnf("playerblob_get_unowned_petids_set_for_rarity rarity(%s) empty set, adding debug 1", (tostring(p48)))
        v50:add_set(1)
    end;
    return v50;
end;
local function f_playerblob_set_of_unowned_available_dance_ids(p51) --[[ Name: playerblob_set_of_unowned_available_dance_ids ]] --[[ Line: 174 ]]
    --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_34, (copy 3): v_u_19, (copy 4): v_u_20 ]]
    local v52 = v_u_2:new()
    local v53 = v_u_34:get_owned_danceid_to_equipped_dict(p51)
    for v54, v55 in v_u_19:singleton():key_itr() do
        if v54 <= 260 and (v55:get_dance_rarity() == v_u_20.Epic and v53:contains(v54) ~= true) then
            v52:add_set(v54)
        end;
    end;
    return v52;
end;
v_u_40.server_player_get_reward_info_list_for_box_of_materialid = function(_, p56, p57, p_u_58, p_u_59, p_u_60) --[[ Name: server_player_get_reward_info_list_for_box_of_materialid ]] --[[ Line: 187 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_40, (copy 3): v_u_10, (copy 4): v_u_9, (copy 5): v_u_3, (copy 6): v_u_11, (copy 7): v_u_12, (copy 8): v_u_15, (copy 9): f_get_rarity_petids_set_for_selection, (copy 10): v_u_45, (copy 11): v_u_13, (copy 12): v_u_2, (copy 13): v_u_31, (copy 14): v_u_17, (copy 15): v_u_14, (copy 16): v_u_16, (copy 17): f_playerblob_set_of_unowned_available_dance_ids ]]
    v_u_7:is_int_greater_than(p_u_60, 0)
    local v61 = v_u_40:get_materialid_box_type(p_u_58)
    v_u_7:is_enum_member(v61, v_u_10.BoxType)
    if p_u_60 > 1 then
        v_u_7:is_true(v_u_40:box_type_multiple_use_enabled(v61))
    end;
    local v_u_62 = v_u_9:singleton():is_material_tradeable(p_u_58)
    local v_u_63 = v_u_3:new()
    local function f_grant_reward_of_tier(p64) --[[ Name: grant_reward_of_tier ]] --[[ Line: 198 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_59, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_40, (copy 6): p_u_58, (copy 7): p_u_60, (ref 8): v_u_9, (copy 9): v_u_63, (ref 10): v_u_15 ]]
        v_u_7:is_enum_member(p_u_59, v_u_11)
        local v65 = v_u_12:color_and_tier_to_material_id(p_u_59, p64)
        local v66 = v_u_40:material_id_to_reward_count(p_u_58) * p_u_60
        v_u_7:is_true(v_u_9:singleton():contains_material(v65))
        v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.CraftingMaterials, v66, v65))
    end;
    local function f_grant_pet_of_rarity(p67) --[[ Name: grant_pet_of_rarity ]] --[[ Line: 206 ]]
        --[[ Upvalues: (copy 1): p_u_60, (ref 2): f_get_rarity_petids_set_for_selection, (ref 3): v_u_45, (copy 4): v_u_62, (copy 5): v_u_63, (ref 6): v_u_15, (ref 7): v_u_13 ]]
        for _ = 1, p_u_60 do
            local v68 = f_get_rarity_petids_set_for_selection(p67, v_u_45):key_list():random()
            if v_u_62 then
                v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.CraftingMaterials, 1, v_u_13:singleton():get_data_for_petid(v68):get_material_id()))
            else
                v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.Pet, 1, v68))
            end;
        end;
    end;
    local function f_grant_vip_song_of_audiomod(p69) --[[ Name: grant_vip_song_of_audiomod ]] --[[ Line: 229 ]]
        --[[ Upvalues: (copy 1): p_u_59, (ref 2): v_u_2, (ref 3): v_u_31, (ref 4): v_u_17, (copy 5): v_u_63, (ref 6): v_u_15, (ref 7): v_u_7 ]]
        if p_u_59 == -2 then
            local v70 = v_u_2:new()
            for v71, _ in v_u_31:key_itr() do
                if v_u_17:singleton():key_get_audiomod(v71) == p69 then
                    v70:add_set(v71)
                end;
            end;
            v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.Song, 1, v70:key_list():random()))
        else
            v_u_7:is_true(v_u_31:contains(p_u_59))
            v_u_7:is_true(v_u_17:singleton():key_get_audiomod(p_u_59) == p69)
            v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.Song, 1, p_u_59))
        end;
    end;
    local function _() --[[ Name: grant_token ]] --[[ Line: 245 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_12, (copy 3): p_u_59, (copy 4): v_u_63, (ref 5): v_u_15, (copy 6): p_u_60 ]]
        v_u_7:is_true(v_u_12:get_token_id_set():contains(p_u_59))
        v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.CraftingMaterials, p_u_60, p_u_59))
    end;
    if v61 == v_u_10.BoxType.SmallNote then
        f_grant_reward_of_tier(v_u_10.Tier.T1)
        return v_u_63;
    end;
    if v61 == v_u_10.BoxType.MediumNote then
        f_grant_reward_of_tier(v_u_10.Tier.T2)
        return v_u_63;
    end;
    if v61 == v_u_10.BoxType.LargeNote then
        f_grant_reward_of_tier(v_u_10.Tier.T3)
        return v_u_63;
    end;
    if v61 == v_u_10.BoxType.Gem then
        f_grant_reward_of_tier(v_u_10.Tier.T4)
        return v_u_63;
    end;
    if v61 == v_u_10.BoxType.MiniOneStar then
        f_grant_pet_of_rarity(v_u_14.Rarity.Tier1)
        return v_u_63;
    end;
    if v61 == v_u_10.BoxType.MiniTwoStar then
        f_grant_pet_of_rarity(v_u_14.Rarity.Tier2)
        return v_u_63;
    end;
    if v61 == v_u_10.BoxType.VIPSongNormal then
        f_grant_vip_song_of_audiomod(v_u_16.Normal)
        return v_u_63;
    end;
    if v61 == v_u_10.BoxType.VIPSongHard then
        f_grant_vip_song_of_audiomod(v_u_16.Hard)
        return v_u_63;
    end;
    if v61 ~= v_u_10.BoxType.Token then
        if v61 == v_u_10.BoxType.Dance then
            local v72 = f_playerblob_set_of_unowned_available_dance_ids(p56._player_blob_manager:get_cached_blob(p57.UserId))
            if v72:count() > 0 then
                v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.Dance, 1, v72:key_list():random()))
                return v_u_63;
            end;
        else
            v_u_7:is_true(false, "Not handled box_type")
        end;
        return v_u_63;
    end;
    v_u_7:is_true(v_u_12:get_token_id_set():contains(p_u_59))
    v_u_63:push_back(v_u_15.RewardInfo:new(v_u_15.RewardType.CraftingMaterials, p_u_60, p_u_59))
    return v_u_63;
end;
v_u_40.client_use_box_materialid = function(_, p_u_73, p_u_74, p_u_75) --[[ Name: client_use_box_materialid ]] --[[ Line: 290 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_40, (copy 3): v_u_4, (ref 4): v_u_37, (ref 5): v_u_39, (copy 6): v_u_8, (copy 7): v_u_15, (copy 8): v_u_10, (ref 9): v_u_36, (copy 10): v_u_16, (copy 11): v_u_5, (copy 12): v_u_18, (ref 13): v_u_35, (copy 14): v_u_31, (copy 15): v_u_17, (copy 16): v_u_1, (ref 17): v_u_38, (copy 18): v_u_3, (copy 19): v_u_12, (copy 20): v_u_9, (copy 21): f_playerblob_set_of_unowned_available_dance_ids, (copy 22): v_u_19, (ref 23): v_u_33, (copy 24): v_u_6 ]]
    v_u_7:is_int_greater_than(p_u_75, 0)
    local v76 = v_u_40:get_materialid_box_type(p_u_74)
    if v76 == v_u_40:type_invalid() then
        return v_u_4:warnf("BoxInfo:use_box_materialid(%s) invalid", (tostring(p_u_74)));
    else
        local l__spui_0 = p_u_73._spui
        local l__menus_0 = p_u_73._menus
        local function f_send_open_box_request(p77, p78) --[[ Name: send_open_box_request ]] --[[ Line: 301 ]]
            --[[ Upvalues: (copy 1): l__menus_0, (ref 2): v_u_37, (copy 3): p_u_73, (copy 4): l__spui_0, (ref 5): v_u_39, (ref 6): v_u_8, (ref 7): v_u_15, (copy 8): p_u_74, (copy 9): p_u_75 ]]
            local v_u_80 = p78 == nil and function(p79) --[[ Line: 303 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_37, (ref 3): p_u_73, (ref 4): l__spui_0 ]]
                l__menus_0:push_menu(v_u_37:new(p_u_73, l__spui_0, l__menus_0, p79):set_header_text("Box Opened!"):set_sub_text("Acquired the following materials..."))
            end or p78
            local v_u_81 = l__menus_0:push_menu(v_u_39:new(p_u_73, l__spui_0, l__menus_0):set_text("Loading...", ""):set_close_button_visible(false))
            p_u_73._evt:wait_on_event_once(v_u_8.EVT_Crafting_OpenBoxServer, function(p82, p83, p_u_84) --[[ Line: 313 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (copy 2): v_u_81, (ref 3): v_u_39, (ref 4): p_u_73, (ref 5): l__spui_0, (ref 6): v_u_80, (ref 7): v_u_15 ]]
                if p82 == true then
                    p_u_73._player_blob_manager:do_sync(function() --[[ Line: 319 ]]
                        --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_81, (ref 3): v_u_80, (ref 4): v_u_15, (copy 5): p_u_84 ]]
                        l__menus_0:remove_menu(v_u_81)
                        v_u_80(v_u_15.RewardInfo:table_to_list(p_u_84))
                    end)
                else
                    l__menus_0:remove_menu(v_u_81)
                    l__menus_0:push_menu(v_u_39:new(p_u_73, l__spui_0, l__menus_0):set_text("Failed", p83))
                end;
            end)
            p_u_73._evt:fire_event_to_server(v_u_8.EVT_Crafting_OpenBoxClient, p_u_74, p77, p_u_75)
        end;
        if v76 == v_u_10.BoxType.SmallNote or (v76 == v_u_10.BoxType.MediumNote or (v76 == v_u_10.BoxType.LargeNote or v76 == v_u_10.BoxType.Gem)) then
            l__menus_0:push_menu(v_u_36:new(p_u_73, l__spui_0, l__menus_0, "Select Color", "Select the color you want these to be...", function(p85) --[[ Line: 335 ]]
                --[[ Upvalues: (copy 1): f_send_open_box_request ]]
                f_send_open_box_request(p85)
            end))
            return;
        elseif v76 == v_u_10.BoxType.MiniOneStar or v76 == v_u_10.BoxType.MiniTwoStar then
            f_send_open_box_request(-2)
            return;
        elseif v76 == v_u_10.BoxType.VIPSongNormal or v76 == v_u_10.BoxType.VIPSongHard then
            local l_Normal_1 = v_u_16.Normal
            if v76 == v_u_10.BoxType.VIPSongHard then
                l_Normal_1 = v_u_16.Hard
            end;
            local v86 = p_u_73._player_blob_manager:get_player_blob()
            local v_u_87 = v_u_5:song_inventory_songids_set(v86)
            v_u_18:playerblob_add_collection_songkeys_to_set(v86, v_u_87, p_u_73._player_blob_manager:get_cached_collection_info())
            local v_u_88 = nil
            v_u_88 = p_u_73._menus:push_menu(v_u_35:new(p_u_73, p_u_73._spui, p_u_73._menus, function(p89) --[[ Line: 355 ]]
                --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_17, (ref 3): l_Normal_1, (copy 4): v_u_87 ]]
                p89:set_header_text("Select Song")
                for v90, _ in v_u_31:key_itr() do
                    if v_u_17:singleton():key_get_audiomod(v90) == l_Normal_1 and v_u_87:contains(v90) ~= true then
                        p89:get_element_list():push_back(v90)
                    end;
                end;
                p89:get_element_list():sort(function(p91, p92) --[[ Line: 362 ]]
                    return p91 - p92;
                end)
                p89:get_element_list():push_front(-2)
            end, function(p93, p94, p95, _, p96) --[[ Line: 368 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_17 ]]
                if p93 == -2 then
                    p94.Text = "Random"
                    p95.Image = v_u_1:get_question_assetid()
                    p96:set_select_button_text("Select")
                elseif p93 and v_u_17:singleton():contains_key(p93) then
                    p94.Text = v_u_17:singleton():get_title_for_key(p93)
                    p95.Image = v_u_17:singleton():get_coverimage_assetid_for_key(p93)
                    p96:get_description_display().Text = string.format("Difficulty: %d", v_u_17:singleton():get_difficulty_for_key(p93))
                    p96:set_select_button_text("Preview")
                end;
            end, function(p_u_97) --[[ Line: 382 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_38, (copy 3): p_u_73, (ref 4): v_u_3, (ref 5): v_u_88, (copy 6): f_send_open_box_request ]]
                if p_u_97 then
                    if v_u_17:singleton():contains_key(p_u_97) then
                        v_u_38:show_song_info_popup(p_u_73, p_u_97, nil, nil, v_u_3:new({ function(p_u_98, _) --[[ Line: 385 ]]
                                --[[ Upvalues: (ref 1): p_u_73, (ref 2): v_u_88, (ref 3): f_send_open_box_request, (copy 4): p_u_97 ]]
                                return "Select", function() --[[ Line: 388 ]]
                                    --[[ Upvalues: (ref 1): p_u_73, (ref 2): v_u_88, (copy 3): p_u_98, (ref 4): f_send_open_box_request, (ref 5): p_u_97 ]]
                                    p_u_73._menus:remove_menu(v_u_88)
                                    p_u_73._menus:remove_menu(p_u_98)
                                    f_send_open_box_request(p_u_97)
                                end;
                            end }))
                        return;
                    end;
                    p_u_73._menus:remove_menu(v_u_88)
                    f_send_open_box_request(p_u_97)
                end;
            end))
            v_u_88:set_close_on_element_select(false)
            return;
        elseif v76 == v_u_10.BoxType.Token then
            p_u_73._menus:push_menu(v_u_35:new(p_u_73, p_u_73._spui, p_u_73._menus, function(p99) --[[ Line: 405 ]]
                --[[ Upvalues: (ref 1): v_u_12 ]]
                p99:set_header_text("Select Token")
                for v100, _ in v_u_12:get_token_id_set():key_itr() do
                    p99:get_element_list():push_back(v100)
                end;
            end, function(p101, p102, p103, _) --[[ Line: 411 ]]
                --[[ Upvalues: (ref 1): v_u_9 ]]
                p102.Text = v_u_9:singleton():get_material_name(p101)
                p103.Image = v_u_9:singleton():get_material_icon(p101)
            end, function(p104) --[[ Line: 415 ]]
                --[[ Upvalues: (copy 1): f_send_open_box_request ]]
                if p104 then
                    f_send_open_box_request(p104)
                end;
            end))
            return;
        elseif v76 == v_u_10.BoxType.Dance then
            if f_playerblob_set_of_unowned_available_dance_ids(p_u_73._player_blob_manager:get_player_blob()):count() == 0 then
                l__menus_0:push_menu(v_u_39:new(p_u_73, l__spui_0, l__menus_0):set_text("No Available Dances", "You currently own all available dances."))
            else
                f_send_open_box_request(-2, function(p105) --[[ Line: 428 ]]
                    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_19, (copy 3): l__menus_0, (ref 4): v_u_33, (copy 5): p_u_73, (copy 6): l__spui_0, (ref 7): v_u_6 ]]
                    local v106 = -1
                    for _, v107 in p105:key_itr() do
                        if v107:get_type() == v_u_15.RewardType.Dance then
                            v106 = v107:get_id()
                            break;
                        end;
                    end;
                    if v_u_19:singleton():contains_dance_for_id(v106) then
                        local v108 = l__menus_0:push_menu(v_u_33:new(p_u_73, l__spui_0, l__menus_0))
                        local v109 = v108:get_character_display()
                        v109:push_animation_assetid(v_u_19:singleton():get_dance_assetid_for_id(v106))
                        v109:set_dance_active(true)
                        v109:play_selected_animation()
                        v108:set_text(string.format("Dance: %s", v_u_19:singleton():get_dance_name_for_id(v106)), "Received this dance!")
                        p_u_73._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                    end;
                end)
            end;
        else
            v_u_4:warnf("ERROR: unexpected box type(%s)", (tostring(v76)))
            return;
        end;
    end;
end;
return v_u_40;
