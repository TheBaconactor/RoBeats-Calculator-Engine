-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.Bit)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_11 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_14 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_15 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventShopItemType)
local v17 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfoData)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.GameStage.GameStageUtil)
local v_u_18 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_19 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_20 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_54 = {
    ["get_play_event_point_count"] = function(_) --[[ Name: get_play_event_point_count ]] --[[ Line: 31 ]]
        return 20;
    end,
    ["get_cheer_event_point_count"] = function(_) --[[ Name: get_cheer_event_point_count ]] --[[ Line: 32 ]]
        return 2;
    end,
    ["ShopItemType"] = v_u_16,
    ["EventShopItem"] = {
        ["new"] = function(_, p_u_55, p_u_56) --[[ Name: new ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_16, (copy 3): v_u_54, (copy 4): v_u_6, (copy 5): v_u_11, (copy 6): v_u_12, (copy 7): v_u_13, (copy 8): v_u_15, (copy 9): v_u_19 ]]
            local v_u_57 = {}
            v_u_7:is_enum_member(p_u_56.Type, v_u_16)
            v_u_7:is_int(p_u_55)
            v_u_7:is_int_greater_than(p_u_56.Amount, 0)
            v_u_7:is_int_greater_than(p_u_56.Price, -1)
            v_u_7:is_int(p_u_56.RewardID)
            v_u_7:is_bool(p_u_56.Repeat)
            local function f_cons() --[[ Name: cons ]] --[[ Line: 49 ]]
                --[[ Upvalues: (copy 1): v_u_57, (ref 2): v_u_54, (ref 3): v_u_7, (ref 4): v_u_6, (ref 5): v_u_11, (ref 6): v_u_12, (ref 7): v_u_13, (ref 8): v_u_15 ]]
                if v_u_57:get_type() == v_u_54.ShopItemType.Coins then
                    v_u_7:is_int_greater_than(v_u_57:get_amount(), -1)
                    return;
                elseif v_u_57:get_type() == v_u_54.ShopItemType.Stars then
                    v_u_7:is_int_greater_than(v_u_57:get_amount(), -1)
                    return;
                elseif v_u_57:get_type() == v_u_54.ShopItemType.Song then
                    v_u_7:is_true(v_u_6:singleton():contains_key(v_u_57:get_reward_id()))
                    return;
                elseif v_u_57:get_type() == v_u_54.ShopItemType.Material then
                    v_u_7:is_true(v_u_11:singleton():contains_material(v_u_57:get_reward_id()))
                    return;
                elseif v_u_57:get_type() == v_u_54.ShopItemType.Title then
                    v_u_7:is_true(v_u_12:singleton():contains_title_for_id(v_u_57:get_reward_id()))
                    return;
                elseif v_u_57:get_type() == v_u_54.ShopItemType.Dance then
                    v_u_7:is_true(v_u_13:singleton():contains_dance_for_id(v_u_57:get_reward_id()))
                elseif v_u_57:get_type() == v_u_54.ShopItemType.Equipment then
                    v_u_7:is_true(v_u_15:singleton():get_equipment_for_id(v_u_57:get_reward_id()) ~= nil)
                end;
            end;
            v_u_57.get_item_id = function(_) --[[ Name: get_item_id ]] --[[ Line: 74 ]]
                --[[ Upvalues: (copy 1): p_u_55 ]]
                return p_u_55;
            end;
            v_u_57.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 75 ]]
                --[[ Upvalues: (copy 1): p_u_56 ]]
                return p_u_56.Type;
            end;
            v_u_57.get_amount = function(_) --[[ Name: get_amount ]] --[[ Line: 76 ]]
                --[[ Upvalues: (copy 1): p_u_56 ]]
                return p_u_56.Amount;
            end;
            v_u_57.get_price = function(_) --[[ Name: get_price ]] --[[ Line: 77 ]]
                --[[ Upvalues: (copy 1): p_u_56 ]]
                return p_u_56.Price;
            end;
            v_u_57.get_reward_id = function(_) --[[ Name: get_reward_id ]] --[[ Line: 78 ]]
                --[[ Upvalues: (copy 1): p_u_56 ]]
                return p_u_56.RewardID;
            end;
            v_u_57.is_repeat = function(_) --[[ Name: is_repeat ]] --[[ Line: 79 ]]
                --[[ Upvalues: (copy 1): p_u_56 ]]
                return p_u_56.Repeat;
            end;
            v_u_57.to_reward_description_info = function(p58) --[[ Name: to_reward_description_info ]] --[[ Line: 81 ]]
                --[[ Upvalues: (ref 1): v_u_54, (ref 2): v_u_19, (ref 3): v_u_11 ]]
                if p58:get_type() == v_u_54.ShopItemType.Coins then
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Coins, p58:get_amount(), -1);
                elseif p58:get_type() == v_u_54.ShopItemType.Stars then
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Stars, p58:get_amount(), -1);
                elseif p58:get_type() == v_u_54.ShopItemType.Song then
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Song, p58:get_amount(), p58:get_reward_id());
                elseif p58:get_type() == v_u_54.ShopItemType.Material then
                    local v59 = v_u_11:singleton():get_material(p58:get_reward_id())
                    if v59:is_pet() then
                        return v_u_19.RewardInfo:new(v_u_19.RewardType.Pet, p58:get_amount(), v59:get_pet_id());
                    else
                        return v_u_19.RewardInfo:new(v_u_19.RewardType.CraftingMaterials, p58:get_amount(), p58:get_reward_id());
                    end;
                elseif p58:get_type() == v_u_54.ShopItemType.Title then
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Titles, 1, p58:get_reward_id());
                elseif p58:get_type() == v_u_54.ShopItemType.Dance then
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Dance, 1, p58:get_reward_id());
                elseif p58:get_type() == v_u_54.ShopItemType.Equipment then
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Gear, 1, p58:get_reward_id());
                else
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Coins, 0, -1);
                end;
            end;
            f_cons()
            return v_u_57;
        end
    },
    ["EventInfo"] = {
        ["new"] = function(_, p62, p_u_63) --[[ Name: new ]] --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_6, (copy 3): v_u_14, (copy 4): v_u_5, (copy 5): v_u_2, (copy 6): v_u_1, (copy 7): v_u_60, (copy 8): v_u_54, (copy 9): v_u_18, (copy 10): v_u_19 ]]
            v_u_7:is_string(p_u_63.Title)
            v_u_7:is_string(p_u_63.Description)
            v_u_7:is_string(p_u_63.Image)
            v_u_7:is_string(p_u_63.Icon)
            local v64 = {}
            for v65, _ in p_u_63.Songs:key_itr() do
                v_u_7:is_true(v_u_6:singleton():contains_key(v65), (tostring(v65)))
                if v_u_6:singleton():key_get_audiomod(v65) == v_u_14.Easy then
                    local v66 = v_u_6:singleton():get_easy_mode_to_songkey_dict():get(v65)
                    local _, v67 = v_u_6:singleton():key_has_combineinfo(v66)
                    local l_OutputKey_2 = v67.OutputKey
                    v_u_7:is_true(v_u_6:singleton():contains_key(v66))
                    v_u_7:is_true(v_u_6:singleton():contains_key(l_OutputKey_2))
                    if p_u_63.Songs:contains(v66) ~= true then
                        v_u_5:warnf("_event_id(%d) easy songkey(%d) does not contain normal(%d)", p62, v65, v66)
                        p_u_63.Songs:add(v66)
                    end;
                    if p_u_63.Songs:contains(l_OutputKey_2) ~= true then
                        v_u_5:warnf("_event_id(%d) easy songkey(%d) does not contain hard(%d)", p62, v65, l_OutputKey_2)
                        p_u_63.Songs:add(l_OutputKey_2)
                    end;
                elseif v_u_6:singleton():key_get_audiomod(v65) == v_u_14.Normal then
                    local v68 = v_u_6:singleton():get_songkey_to_easy_mode_dict():get(v65)
                    if v68 ~= nil then
                        v_u_7:is_true(v_u_6:singleton():contains_key(v68))
                        if p_u_63.Songs:contains(v68) ~= true then
                            v_u_5:warnf("_event_id(%d) normal songkey(%d) does not contain easy(%d)", p62, v65, v68)
                            p_u_63.Songs:add(v68)
                        end;
                    end;
                    local _, v69 = v_u_6:singleton():key_has_combineinfo(v65)
                    local l_OutputKey_3 = v69.OutputKey
                    v_u_7:is_true(v_u_6:singleton():contains_key(l_OutputKey_3))
                    if p_u_63.Songs:contains(l_OutputKey_3) ~= true then
                        v_u_5:warnf("_event_id(%d) normal songkey(%d) does not contain hard(%d)", p62, v65, l_OutputKey_3)
                        p_u_63.Songs:add(l_OutputKey_3)
                    end;
                elseif v_u_6:singleton():key_get_audiomod(v65) == v_u_14.Hard then
                    local v70 = v_u_6:singleton():key_is_fusionresult_of(v65)
                    v_u_7:is_true(v_u_6:singleton():contains_key(v70))
                    if p_u_63.Songs:contains(v70) ~= true then
                        v_u_5:warnf("_event_id(%d) hard songkey(%d) does not contain normal(%d)", p62, v65, v70)
                        p_u_63.Songs:add(v70)
                    end;
                    local v71 = v_u_6:singleton():get_songkey_to_easy_mode_dict():get(v70)
                    if v71 ~= nil then
                        v_u_7:is_true(v_u_6:singleton():contains_key(v71))
                        if p_u_63.Songs:contains(v71) ~= true then
                            v_u_5:warnf("_event_id(%d) hard songkey(%d) does not contain easy(%d)", p62, v65, v71)
                            p_u_63.Songs:add(v71)
                        end;
                    end;
                else
                    v_u_5:errf("ArtistEventInfo(%d) Songs unexpected AudioMod", p62)
                end;
            end;
            v_u_7:is_table(p_u_63.Shop)
            v_u_7:is_true(#p_u_63.Shop < 32, string.format("eventid(%d) shopitems(%d)", p62, #p_u_63.Shop))
            local v_u_72 = v_u_2:new()
            local v73 = v_u_1:new()
            for v74, v75 in pairs(p_u_63.Shop) do
                local v76 = v_u_60:new(v74, v75)
                v_u_72:push_back(v76)
                if v76:get_type() == v_u_54.ShopItemType.Song then
                    if v73:contains(v76:get_reward_id()) then
                        v_u_5:errf("duplicate ArtistEventInfo(%d) _shop_songs_set song(%d)", p62, v76:get_reward_id())
                    end;
                    v73:add_set(v76:get_reward_id())
                end;
            end;
            v64.get_title = function(_) --[[ Name: get_title ]] --[[ Line: 202 ]]
                --[[ Upvalues: (copy 1): p_u_63 ]]
                return p_u_63.Title;
            end;
            v64.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 203 ]]
                --[[ Upvalues: (copy 1): p_u_63 ]]
                return p_u_63.Description;
            end;
            v64.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 204 ]]
                --[[ Upvalues: (copy 1): p_u_63 ]]
                return p_u_63.Image;
            end;
            v64.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 205 ]]
                --[[ Upvalues: (copy 1): p_u_63 ]]
                return p_u_63.Icon;
            end;
            v64.get_songs_set = function(_) --[[ Name: get_songs_set ]] --[[ Line: 206 ]]
                --[[ Upvalues: (copy 1): p_u_63 ]]
                return p_u_63.Songs:copy();
            end;
            v64.get_songs_list = function(p77) --[[ Name: get_songs_list ]] --[[ Line: 207 ]]
                return p77:get_songs_set():key_list();
            end;
            v64.get_shop_items_list = function(_) --[[ Name: get_shop_items_list ]] --[[ Line: 208 ]]
                --[[ Upvalues: (copy 1): v_u_72 ]]
                return v_u_72;
            end;
            local v_u_78, v_u_79
            if p_u_63.HUDButton == nil then
                v_u_78 = false
                v_u_79 = ""
            else
                v_u_79 = p_u_63.HUDButton
                v_u_78 = true
            end;
            v64.has_hud_icon = function(_) --[[ Name: has_hud_icon ]] --[[ Line: 216 ]]
                --[[ Upvalues: (ref 1): v_u_78, (ref 2): v_u_79 ]]
                return v_u_78, v_u_79;
            end;
            local v_u_80, v_u_81, v_u_82, v_u_83
            if p_u_63.NPCID == nil then
                v_u_80 = false
                v_u_81 = "Default"
                v_u_82 = "Fan"
                v_u_83 = "Event"
            else
                v_u_81 = p_u_63.NPCID
                v_u_82 = p_u_63.NPCName
                v_u_83 = p_u_63.NPCTitle
                v_u_80 = true
            end;
            v64.has_lobby_npc = function(_) --[[ Name: has_lobby_npc ]] --[[ Line: 228 ]]
                --[[ Upvalues: (ref 1): v_u_80 ]]
                return v_u_80;
            end;
            v64.get_lobby_npc_info = function(_) --[[ Name: get_lobby_npc_info ]] --[[ Line: 229 ]]
                --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_82, (ref 3): v_u_83 ]]
                return v_u_81, v_u_82, v_u_83;
            end;
            local v_u_84
            if p_u_63.LobbyNPCNameTagOffset == nil then
                v_u_84 = nil
            else
                v_u_7:is_true(typeof(p_u_63.LobbyNPCNameTagOffset) == "Vector3")
                v_u_84 = p_u_63.LobbyNPCNameTagOffset
            end;
            v64.get_lobby_npc_nametag_offset = function(_) --[[ Name: get_lobby_npc_nametag_offset ]] --[[ Line: 236 ]]
                --[[ Upvalues: (ref 1): v_u_84 ]]
                return v_u_84;
            end;
            local v_u_85
            if p_u_63.LobbyNPCDialogueTriggerPopupOffset == nil then
                v_u_85 = nil
            else
                v_u_7:is_true(typeof(p_u_63.LobbyNPCDialogueTriggerPopupOffset) == "Vector3")
                v_u_85 = p_u_63.LobbyNPCDialogueTriggerPopupOffset
            end;
            v64.get_lobby_npc_dialogue_trigger_popup_offset = function(_) --[[ Name: get_lobby_npc_dialogue_trigger_popup_offset ]] --[[ Line: 243 ]]
                --[[ Upvalues: (ref 1): v_u_85 ]]
                return v_u_85;
            end;
            local v_u_86 = v_u_18:singleton():get_default_stage_id()
            local v_u_87
            if p_u_63.StageID == nil then
                v_u_87 = false
            else
                v_u_86 = p_u_63.StageID
                v_u_87 = true
            end;
            v64.has_stage = function(_) --[[ Name: has_stage ]] --[[ Line: 251 ]]
                --[[ Upvalues: (ref 1): v_u_87 ]]
                return v_u_87;
            end;
            v64.get_stage_id = function(_) --[[ Name: get_stage_id ]] --[[ Line: 252 ]]
                --[[ Upvalues: (ref 1): v_u_86 ]]
                return v_u_86;
            end;
            local v_u_88 = v_u_2:new()
            if p_u_63.EventPointPurchaseRewards ~= nil then
                for _, v89 in pairs(p_u_63.EventPointPurchaseRewards) do
                    v_u_7:is_enum_member(v89:get_type(), v_u_19.RewardType)
                    v_u_88:push_back(v89)
                end;
            end;
            v64.has_event_point_purchase_rewards = function(_) --[[ Name: has_event_point_purchase_rewards ]] --[[ Line: 262 ]]
                --[[ Upvalues: (copy 1): v_u_88 ]]
                return v_u_88:count() > 0;
            end;
            v64.get_event_point_purchase_rewards = function(_) --[[ Name: get_event_point_purchase_rewards ]] --[[ Line: 263 ]]
                --[[ Upvalues: (ref 1): v_u_19, (copy 2): v_u_88 ]]
                return v_u_19.RewardInfo:table_to_list(v_u_19.RewardInfo:list_to_table(v_u_88));
            end;
            return v64;
        end
    }
}
local v_u_60 = {
    ["new"] = function(_, p_u_55, p_u_56) --[[ Name: new ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_16, (copy 3): v_u_54, (copy 4): v_u_6, (copy 5): v_u_11, (copy 6): v_u_12, (copy 7): v_u_13, (copy 8): v_u_15, (copy 9): v_u_19 ]]
        local v_u_57 = {}
        v_u_7:is_enum_member(p_u_56.Type, v_u_16)
        v_u_7:is_int(p_u_55)
        v_u_7:is_int_greater_than(p_u_56.Amount, 0)
        v_u_7:is_int_greater_than(p_u_56.Price, -1)
        v_u_7:is_int(p_u_56.RewardID)
        v_u_7:is_bool(p_u_56.Repeat)
        local function f_cons() --[[ Name: cons ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_57, (ref 2): v_u_54, (ref 3): v_u_7, (ref 4): v_u_6, (ref 5): v_u_11, (ref 6): v_u_12, (ref 7): v_u_13, (ref 8): v_u_15 ]]
            if v_u_57:get_type() == v_u_54.ShopItemType.Coins then
                v_u_7:is_int_greater_than(v_u_57:get_amount(), -1)
                return;
            elseif v_u_57:get_type() == v_u_54.ShopItemType.Stars then
                v_u_7:is_int_greater_than(v_u_57:get_amount(), -1)
                return;
            elseif v_u_57:get_type() == v_u_54.ShopItemType.Song then
                v_u_7:is_true(v_u_6:singleton():contains_key(v_u_57:get_reward_id()))
                return;
            elseif v_u_57:get_type() == v_u_54.ShopItemType.Material then
                v_u_7:is_true(v_u_11:singleton():contains_material(v_u_57:get_reward_id()))
                return;
            elseif v_u_57:get_type() == v_u_54.ShopItemType.Title then
                v_u_7:is_true(v_u_12:singleton():contains_title_for_id(v_u_57:get_reward_id()))
                return;
            elseif v_u_57:get_type() == v_u_54.ShopItemType.Dance then
                v_u_7:is_true(v_u_13:singleton():contains_dance_for_id(v_u_57:get_reward_id()))
            elseif v_u_57:get_type() == v_u_54.ShopItemType.Equipment then
                v_u_7:is_true(v_u_15:singleton():get_equipment_for_id(v_u_57:get_reward_id()) ~= nil)
            end;
        end;
        v_u_57.get_item_id = function(_) --[[ Name: get_item_id ]] --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): p_u_55 ]]
            return p_u_55;
        end;
        v_u_57.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 75 ]]
            --[[ Upvalues: (copy 1): p_u_56 ]]
            return p_u_56.Type;
        end;
        v_u_57.get_amount = function(_) --[[ Name: get_amount ]] --[[ Line: 76 ]]
            --[[ Upvalues: (copy 1): p_u_56 ]]
            return p_u_56.Amount;
        end;
        v_u_57.get_price = function(_) --[[ Name: get_price ]] --[[ Line: 77 ]]
            --[[ Upvalues: (copy 1): p_u_56 ]]
            return p_u_56.Price;
        end;
        v_u_57.get_reward_id = function(_) --[[ Name: get_reward_id ]] --[[ Line: 78 ]]
            --[[ Upvalues: (copy 1): p_u_56 ]]
            return p_u_56.RewardID;
        end;
        v_u_57.is_repeat = function(_) --[[ Name: is_repeat ]] --[[ Line: 79 ]]
            --[[ Upvalues: (copy 1): p_u_56 ]]
            return p_u_56.Repeat;
        end;
        v_u_57.to_reward_description_info = function(p58) --[[ Name: to_reward_description_info ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_54, (ref 2): v_u_19, (ref 3): v_u_11 ]]
            if p58:get_type() == v_u_54.ShopItemType.Coins then
                return v_u_19.RewardInfo:new(v_u_19.RewardType.Coins, p58:get_amount(), -1);
            elseif p58:get_type() == v_u_54.ShopItemType.Stars then
                return v_u_19.RewardInfo:new(v_u_19.RewardType.Stars, p58:get_amount(), -1);
            elseif p58:get_type() == v_u_54.ShopItemType.Song then
                return v_u_19.RewardInfo:new(v_u_19.RewardType.Song, p58:get_amount(), p58:get_reward_id());
            elseif p58:get_type() == v_u_54.ShopItemType.Material then
                local v59 = v_u_11:singleton():get_material(p58:get_reward_id())
                if v59:is_pet() then
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.Pet, p58:get_amount(), v59:get_pet_id());
                else
                    return v_u_19.RewardInfo:new(v_u_19.RewardType.CraftingMaterials, p58:get_amount(), p58:get_reward_id());
                end;
            elseif p58:get_type() == v_u_54.ShopItemType.Title then
                return v_u_19.RewardInfo:new(v_u_19.RewardType.Titles, 1, p58:get_reward_id());
            elseif p58:get_type() == v_u_54.ShopItemType.Dance then
                return v_u_19.RewardInfo:new(v_u_19.RewardType.Dance, 1, p58:get_reward_id());
            elseif p58:get_type() == v_u_54.ShopItemType.Equipment then
                return v_u_19.RewardInfo:new(v_u_19.RewardType.Gear, 1, p58:get_reward_id());
            else
                return v_u_19.RewardInfo:new(v_u_19.RewardType.Coins, 0, -1);
            end;
        end;
        f_cons()
        return v_u_57;
    end
}
local v_u_61 = v_u_1:new()
local v90 = {
    ["new"] = function(_, p62, p_u_63) --[[ Name: new ]] --[[ Line: 119 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_6, (copy 3): v_u_14, (copy 4): v_u_5, (copy 5): v_u_2, (copy 6): v_u_1, (copy 7): v_u_60, (copy 8): v_u_54, (copy 9): v_u_18, (copy 10): v_u_19 ]]
        v_u_7:is_string(p_u_63.Title)
        v_u_7:is_string(p_u_63.Description)
        v_u_7:is_string(p_u_63.Image)
        v_u_7:is_string(p_u_63.Icon)
        local v64 = {}
        for v65, _ in p_u_63.Songs:key_itr() do
            v_u_7:is_true(v_u_6:singleton():contains_key(v65), (tostring(v65)))
            if v_u_6:singleton():key_get_audiomod(v65) == v_u_14.Easy then
                local v66 = v_u_6:singleton():get_easy_mode_to_songkey_dict():get(v65)
                local _, v67 = v_u_6:singleton():key_has_combineinfo(v66)
                local l_OutputKey_2 = v67.OutputKey
                v_u_7:is_true(v_u_6:singleton():contains_key(v66))
                v_u_7:is_true(v_u_6:singleton():contains_key(l_OutputKey_2))
                if p_u_63.Songs:contains(v66) ~= true then
                    v_u_5:warnf("_event_id(%d) easy songkey(%d) does not contain normal(%d)", p62, v65, v66)
                    p_u_63.Songs:add(v66)
                end;
                if p_u_63.Songs:contains(l_OutputKey_2) ~= true then
                    v_u_5:warnf("_event_id(%d) easy songkey(%d) does not contain hard(%d)", p62, v65, l_OutputKey_2)
                    p_u_63.Songs:add(l_OutputKey_2)
                end;
            elseif v_u_6:singleton():key_get_audiomod(v65) == v_u_14.Normal then
                local v68 = v_u_6:singleton():get_songkey_to_easy_mode_dict():get(v65)
                if v68 ~= nil then
                    v_u_7:is_true(v_u_6:singleton():contains_key(v68))
                    if p_u_63.Songs:contains(v68) ~= true then
                        v_u_5:warnf("_event_id(%d) normal songkey(%d) does not contain easy(%d)", p62, v65, v68)
                        p_u_63.Songs:add(v68)
                    end;
                end;
                local _, v69 = v_u_6:singleton():key_has_combineinfo(v65)
                local l_OutputKey_3 = v69.OutputKey
                v_u_7:is_true(v_u_6:singleton():contains_key(l_OutputKey_3))
                if p_u_63.Songs:contains(l_OutputKey_3) ~= true then
                    v_u_5:warnf("_event_id(%d) normal songkey(%d) does not contain hard(%d)", p62, v65, l_OutputKey_3)
                    p_u_63.Songs:add(l_OutputKey_3)
                end;
            elseif v_u_6:singleton():key_get_audiomod(v65) == v_u_14.Hard then
                local v70 = v_u_6:singleton():key_is_fusionresult_of(v65)
                v_u_7:is_true(v_u_6:singleton():contains_key(v70))
                if p_u_63.Songs:contains(v70) ~= true then
                    v_u_5:warnf("_event_id(%d) hard songkey(%d) does not contain normal(%d)", p62, v65, v70)
                    p_u_63.Songs:add(v70)
                end;
                local v71 = v_u_6:singleton():get_songkey_to_easy_mode_dict():get(v70)
                if v71 ~= nil then
                    v_u_7:is_true(v_u_6:singleton():contains_key(v71))
                    if p_u_63.Songs:contains(v71) ~= true then
                        v_u_5:warnf("_event_id(%d) hard songkey(%d) does not contain easy(%d)", p62, v65, v71)
                        p_u_63.Songs:add(v71)
                    end;
                end;
            else
                v_u_5:errf("ArtistEventInfo(%d) Songs unexpected AudioMod", p62)
            end;
        end;
        v_u_7:is_table(p_u_63.Shop)
        v_u_7:is_true(#p_u_63.Shop < 32, string.format("eventid(%d) shopitems(%d)", p62, #p_u_63.Shop))
        local v_u_72 = v_u_2:new()
        local v73 = v_u_1:new()
        for v74, v75 in pairs(p_u_63.Shop) do
            local v76 = v_u_60:new(v74, v75)
            v_u_72:push_back(v76)
            if v76:get_type() == v_u_54.ShopItemType.Song then
                if v73:contains(v76:get_reward_id()) then
                    v_u_5:errf("duplicate ArtistEventInfo(%d) _shop_songs_set song(%d)", p62, v76:get_reward_id())
                end;
                v73:add_set(v76:get_reward_id())
            end;
        end;
        v64.get_title = function(_) --[[ Name: get_title ]] --[[ Line: 202 ]]
            --[[ Upvalues: (copy 1): p_u_63 ]]
            return p_u_63.Title;
        end;
        v64.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 203 ]]
            --[[ Upvalues: (copy 1): p_u_63 ]]
            return p_u_63.Description;
        end;
        v64.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 204 ]]
            --[[ Upvalues: (copy 1): p_u_63 ]]
            return p_u_63.Image;
        end;
        v64.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 205 ]]
            --[[ Upvalues: (copy 1): p_u_63 ]]
            return p_u_63.Icon;
        end;
        v64.get_songs_set = function(_) --[[ Name: get_songs_set ]] --[[ Line: 206 ]]
            --[[ Upvalues: (copy 1): p_u_63 ]]
            return p_u_63.Songs:copy();
        end;
        v64.get_songs_list = function(p77) --[[ Name: get_songs_list ]] --[[ Line: 207 ]]
            return p77:get_songs_set():key_list();
        end;
        v64.get_shop_items_list = function(_) --[[ Name: get_shop_items_list ]] --[[ Line: 208 ]]
            --[[ Upvalues: (copy 1): v_u_72 ]]
            return v_u_72;
        end;
        local v_u_78, v_u_79
        if p_u_63.HUDButton == nil then
            v_u_78 = false
            v_u_79 = ""
        else
            v_u_79 = p_u_63.HUDButton
            v_u_78 = true
        end;
        v64.has_hud_icon = function(_) --[[ Name: has_hud_icon ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_78, (ref 2): v_u_79 ]]
            return v_u_78, v_u_79;
        end;
        local v_u_80, v_u_81, v_u_82, v_u_83
        if p_u_63.NPCID == nil then
            v_u_80 = false
            v_u_81 = "Default"
            v_u_82 = "Fan"
            v_u_83 = "Event"
        else
            v_u_81 = p_u_63.NPCID
            v_u_82 = p_u_63.NPCName
            v_u_83 = p_u_63.NPCTitle
            v_u_80 = true
        end;
        v64.has_lobby_npc = function(_) --[[ Name: has_lobby_npc ]] --[[ Line: 228 ]]
            --[[ Upvalues: (ref 1): v_u_80 ]]
            return v_u_80;
        end;
        v64.get_lobby_npc_info = function(_) --[[ Name: get_lobby_npc_info ]] --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_82, (ref 3): v_u_83 ]]
            return v_u_81, v_u_82, v_u_83;
        end;
        local v_u_84
        if p_u_63.LobbyNPCNameTagOffset == nil then
            v_u_84 = nil
        else
            v_u_7:is_true(typeof(p_u_63.LobbyNPCNameTagOffset) == "Vector3")
            v_u_84 = p_u_63.LobbyNPCNameTagOffset
        end;
        v64.get_lobby_npc_nametag_offset = function(_) --[[ Name: get_lobby_npc_nametag_offset ]] --[[ Line: 236 ]]
            --[[ Upvalues: (ref 1): v_u_84 ]]
            return v_u_84;
        end;
        local v_u_85
        if p_u_63.LobbyNPCDialogueTriggerPopupOffset == nil then
            v_u_85 = nil
        else
            v_u_7:is_true(typeof(p_u_63.LobbyNPCDialogueTriggerPopupOffset) == "Vector3")
            v_u_85 = p_u_63.LobbyNPCDialogueTriggerPopupOffset
        end;
        v64.get_lobby_npc_dialogue_trigger_popup_offset = function(_) --[[ Name: get_lobby_npc_dialogue_trigger_popup_offset ]] --[[ Line: 243 ]]
            --[[ Upvalues: (ref 1): v_u_85 ]]
            return v_u_85;
        end;
        local v_u_86 = v_u_18:singleton():get_default_stage_id()
        local v_u_87
        if p_u_63.StageID == nil then
            v_u_87 = false
        else
            v_u_86 = p_u_63.StageID
            v_u_87 = true
        end;
        v64.has_stage = function(_) --[[ Name: has_stage ]] --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_87 ]]
            return v_u_87;
        end;
        v64.get_stage_id = function(_) --[[ Name: get_stage_id ]] --[[ Line: 252 ]]
            --[[ Upvalues: (ref 1): v_u_86 ]]
            return v_u_86;
        end;
        local v_u_88 = v_u_2:new()
        if p_u_63.EventPointPurchaseRewards ~= nil then
            for _, v89 in pairs(p_u_63.EventPointPurchaseRewards) do
                v_u_7:is_enum_member(v89:get_type(), v_u_19.RewardType)
                v_u_88:push_back(v89)
            end;
        end;
        v64.has_event_point_purchase_rewards = function(_) --[[ Name: has_event_point_purchase_rewards ]] --[[ Line: 262 ]]
            --[[ Upvalues: (copy 1): v_u_88 ]]
            return v_u_88:count() > 0;
        end;
        v64.get_event_point_purchase_rewards = function(_) --[[ Name: get_event_point_purchase_rewards ]] --[[ Line: 263 ]]
            --[[ Upvalues: (ref 1): v_u_19, (copy 2): v_u_88 ]]
            return v_u_19.RewardInfo:table_to_list(v_u_19.RewardInfo:list_to_table(v_u_88));
        end;
        return v64;
    end
}
for v91, v92 in pairs(v17) do
    v_u_61:add(v91, v90:new(v91, v92))
end;
local v_u_93 = v_u_1:new()
for v94, v95 in v_u_61:key_itr() do
    for v96, _ in v95:get_songs_set():key_itr() do
        v_u_93:add(v96, v94)
    end;
end;
v_u_54.is_event_active = function(_, p97) --[[ Name: is_event_active ]] --[[ Line: 280 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_61 ]]
    local v98, v99, v100, v101 = p97:is_event_type_active(v_u_4.EventType.ArtistEvent)
    if v98 and v_u_61:contains(v99) ~= true then
        v98 = false
    end;
    return v98, v99, v100, v101;
end;
v_u_54.get_event_info = function(_, p102) --[[ Name: get_event_info ]] --[[ Line: 290 ]]
    --[[ Upvalues: (copy 1): v_u_61 ]]
    return v_u_61:get(p102);
end;
v_u_54.get_playable_song_set = function(_, p103) --[[ Name: get_playable_song_set ]] --[[ Line: 294 ]]
    --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_1 ]]
    local v104 = v_u_54:get_event_info(p103)
    if v104 == nil then
        return v_u_1:new();
    else
        return v104:get_songs_set();
    end;
end;
v_u_54.get_event_point_reward_song_set = function(_, p105) --[[ Name: get_event_point_reward_song_set ]] --[[ Line: 300 ]]
    --[[ Upvalues: (copy 1): v_u_54 ]]
    return v_u_54:get_playable_song_set(p105);
end;
v_u_54.playerblob_needs_event_info_validate = function(_, p106, p107) --[[ Name: playerblob_needs_event_info_validate ]] --[[ Line: 304 ]]
    return p106.ArtEvtID ~= p107;
end;
v_u_54.playerblob_validate_event_info = function(_, p108, p109) --[[ Name: playerblob_validate_event_info ]] --[[ Line: 307 ]]
    if p108.ArtEvtID ~= p109 then
        p108.ArtEvtID = p109
        p108.ArtEvtPoints = 0
        p108.ArtEvtClaimed = 0
    end;
end;
v_u_54.playerblob_get_event_points = function(_, p110) --[[ Name: playerblob_get_event_points ]] --[[ Line: 315 ]]
    return p110.ArtEvtPoints;
end;
v_u_54.playerblob_set_event_points = function(_, p111, p112) --[[ Name: playerblob_set_event_points ]] --[[ Line: 316 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    if p112 < v_u_8:input_max_number() then
        p111.ArtEvtPoints = p112
    end;
end;
v_u_54.playerblob_is_item_id_claimed = function(_, p113, p114) --[[ Name: playerblob_is_item_id_claimed ]] --[[ Line: 322 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_9 ]]
    local v115 = v_u_7
    local v116
    if p114 > 0 then
        v116 = p114 <= 32
    else
        v116 = false
    end;
    v115:is_true(v116)
    return v_u_9.And(p113.ArtEvtClaimed, v_u_9.LShift(1, p114 - 1)) ~= 0;
end;
v_u_54.playerblob_set_item_id_claimed = function(_, p117, p118) --[[ Name: playerblob_set_item_id_claimed ]] --[[ Line: 327 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_9 ]]
    local v119 = v_u_7
    local v120
    if p118 > 0 then
        v120 = p118 <= 32
    else
        v120 = false
    end;
    v119:is_true(v120)
    p117.ArtEvtClaimed = v_u_9.Or(p117.ArtEvtClaimed, v_u_9.LShift(1, p118 - 1))
end;
v_u_54.can_playerblob_claim_shop_item = function(_, p121, p122) --[[ Name: can_playerblob_claim_shop_item ]] --[[ Line: 332 ]]
    --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_16, (copy 3): v_u_10, (copy 4): v_u_3 ]]
    if v_u_54:playerblob_is_item_id_claimed(p121, p122:get_item_id()) and p122:is_repeat() ~= true then
        return false;
    end;
    if p122:get_type() == v_u_16.Dance then
        if v_u_10:get_owned_danceid_to_equipped_dict(p121):contains(p122:get_reward_id()) == true then
            return false;
        end;
    elseif p122:get_type() == v_u_16.Title and v_u_3:owns_title_id(p121, p122:get_reward_id()) == true then
        return false;
    end;
    return true;
end;
v_u_54.get_name_for_shop_item = function(_, p123) --[[ Name: get_name_for_shop_item ]] --[[ Line: 348 ]]
    --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_6, (copy 3): v_u_11, (copy 4): v_u_12, (copy 5): v_u_13, (copy 6): v_u_15 ]]
    local v124 = ""
    if p123:get_type() == v_u_54.ShopItemType.Coins then
        v124 = string.format("Coins")
    elseif p123:get_type() == v_u_54.ShopItemType.Stars then
        v124 = string.format("Stars")
    elseif p123:get_type() == v_u_54.ShopItemType.Song then
        v124 = string.format("Song: %s", v_u_6:singleton():get_title_for_key(p123:get_reward_id()))
    elseif p123:get_type() == v_u_54.ShopItemType.Material then
        v124 = string.format("Item: %s", v_u_11:singleton():get_material_name(p123:get_reward_id()), p123:get_amount())
    elseif p123:get_type() == v_u_54.ShopItemType.Title then
        v124 = string.format("Title: %s", v_u_12:singleton():get_title_name_for_id(p123:get_reward_id()))
    elseif p123:get_type() == v_u_54.ShopItemType.Dance then
        v124 = string.format("Dance: %s", v_u_13:singleton():get_dance_name_for_id(p123:get_reward_id()))
    elseif p123:get_type() == v_u_54.ShopItemType.Equipment then
        v124 = string.format("Gear: %s", v_u_15:singleton():get_equipment_for_id(p123:get_reward_id()):get_name())
    end;
    if p123:get_amount() > 1 then
        v124 = v124 .. string.format(" x%d", p123:get_amount())
    end;
    return v124;
end;
v_u_54.get_event_shop_danceids_list = function(_, p125) --[[ Name: get_event_shop_danceids_list ]] --[[ Line: 379 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_61, (copy 3): v_u_54 ]]
    local v126 = v_u_2:new()
    if v_u_61:contains(p125) == false then
        return v126;
    end;
    for _, v127 in v_u_61:get(p125):get_shop_items_list():key_itr() do
        if v127:get_type() == v_u_54.ShopItemType.Dance then
            v126:push_back(v127:get_reward_id())
        end;
    end;
    return v126;
end;
v_u_54.get_event_shop_random_dance_assetid = function(_, p128) --[[ Name: get_event_shop_random_dance_assetid ]] --[[ Line: 391 ]]
    --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_13 ]]
    local v129 = v_u_54:get_event_shop_danceids_list(p128)
    return v129:count() == 0 and "rbxassetid://718420920" or v_u_13:singleton():get_dance_assetid_for_id(v129:random());
end;
v_u_54.songkey_to_event_id = function(_, p130) --[[ Name: songkey_to_event_id ]] --[[ Line: 397 ]]
    --[[ Upvalues: (copy 1): v_u_93 ]]
    return v_u_93:get(p130);
end;
v_u_54.get_event_shop_titleids_list = function(_, p131) --[[ Name: get_event_shop_titleids_list ]] --[[ Line: 401 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_61, (copy 3): v_u_54 ]]
    local v132 = v_u_2:new()
    if v_u_61:contains(p131) == false then
        return v132;
    end;
    for _, v133 in v_u_61:get(p131):get_shop_items_list():key_itr() do
        if v133:get_type() == v_u_54.ShopItemType.Title then
            v132:push_back(v133:get_reward_id())
        end;
    end;
    return v132;
end;
v_u_54.get_event_pet_ids_set = function(_, p134) --[[ Name: get_event_pet_ids_set ]] --[[ Line: 413 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_61, (copy 3): v_u_54, (copy 4): v_u_11, (copy 5): v_u_20 ]]
    local v135 = v_u_1:new()
    if v_u_61:contains(p134) == false then
        return v135;
    end;
    for _, v136 in v_u_61:get(p134):get_shop_items_list():key_itr() do
        if v136:get_type() == v_u_54.ShopItemType.Material then
            local v137 = v_u_11:singleton():get_material((v136:get_reward_id()))
            if v137:get_type() == v_u_20.Type.Pet then
                v135:add_set((v137:get_pet_id()))
            end;
        end;
    end;
    return v135;
end;
v_u_54.get_artistevent_info = function(_) --[[ Name: get_artistevent_info ]] --[[ Line: 430 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_61 ]]
    local v138 = v_u_2:new()
    for v139, v140 in v_u_61:key_itr() do
        v138:push_back({
            ["EventId"] = v139,
            ["SongList"] = v140:get_songs_list():get_table(),
            ["Name"] = v140:get_title()
        })
    end;
    return v138:get_table();
end;
local v_u_141 = v_u_1:new()
local v142 = {}
v142.new = function(_, p_u_143, p_u_144) --[[ Name: new ]] --[[ Line: 444 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_2, (copy 3): v_u_19 ]]
    v_u_7:is_int_greater_than(p_u_143, 0)
    v_u_7:is_int_greater_than(p_u_144, 0)
    local v145 = {}
    v145.get_star_amount = function(_) --[[ Name: get_star_amount ]] --[[ Line: 450 ]]
        --[[ Upvalues: (copy 1): p_u_143 ]]
        return p_u_143;
    end;
    v145.get_event_point_amount = function(_) --[[ Name: get_event_point_amount ]] --[[ Line: 451 ]]
        --[[ Upvalues: (copy 1): p_u_144 ]]
        return p_u_144;
    end;
    v145.get_reward_desc_info_list = function(_) --[[ Name: get_reward_desc_info_list ]] --[[ Line: 452 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_19, (copy 3): p_u_144 ]]
        return v_u_2:new({ v_u_19.RewardInfo:new(v_u_19.RewardType.EventPoints, p_u_144, -1) });
    end;
    return v145;
end;
v_u_141:add(1, v142:new(5, 150))
v_u_141:add(2, v142:new(25, 850))
v_u_141:add(3, v142:new(50, 1800))
v_u_54.get_star_purchase_id_to_info = function(_) --[[ Name: get_star_purchase_id_to_info ]] --[[ Line: 463 ]]
    --[[ Upvalues: (copy 1): v_u_141 ]]
    return v_u_141;
end;
v_u_54.get_eventid_songkey_purchase_info = function(_, p146, p147) --[[ Name: get_eventid_songkey_purchase_info ]] --[[ Line: 465 ]]
    --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_6, (copy 3): v_u_14 ]]
    local v148 = false
    local v149 = 25
    local v150 = v_u_54:get_event_info(p146)
    local v151 = v_u_6:singleton():key_get_audiomod(p147)
    local v152 = v_u_6:singleton():key_is_vip(p147)
    if v_u_6:singleton():contains_key(p147) and (v150 ~= nil and v150:get_songs_set():contains(p147)) then
        if v151 == v_u_14.Normal then
            local v153 = true
            if v152 then
                return v153, 150;
            else
                return v153, 50;
            end;
        end;
        if v151 == v_u_14.Hard then
            v148 = true
            if v152 then
                return v148, 500;
            end;
            v149 = 250
        end;
    end;
    return v148, v149;
end;
return v_u_54;
