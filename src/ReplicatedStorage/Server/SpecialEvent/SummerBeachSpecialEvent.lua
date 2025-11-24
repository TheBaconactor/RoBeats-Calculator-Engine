-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:20 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_4 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_5 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local _ = game:GetService("BadgeService")
local v10 = {}
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
v11:require_server(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v10.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_7, (copy 5): v_u_1, (copy 6): v_u_6, (copy 7): v_u_8, (copy 8): v_u_5, (copy 9): v_u_4, (copy 10): v_u_9 ]]
    local v14 = v_u_12.EventBase:new()
    local function _() --[[ Name: cons ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_3, (ref 3): v_u_2, (ref 4): v_u_7, (ref 5): v_u_1, (ref 6): v_u_6, (ref 7): v_u_8, (ref 8): v_u_5, (ref 9): v_u_4, (ref 10): v_u_9 ]]
        p_u_13._evt:wait_on_event(v_u_3.EVT_SummerJumpChallenge_ClientClaimReward, function(p_u_15, p_u_16) --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): v_u_7, (ref 5): v_u_1, (ref 6): v_u_6, (ref 7): v_u_8, (ref 8): v_u_5, (ref 9): v_u_4, (ref 10): v_u_9 ]]
            v_u_2:is_int(p_u_16)
            local function f_response(p17, p18, p19) --[[ Name: response ]] --[[ Line: 33 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_15 ]]
                p_u_13._evt:fire_event_to_client(v_u_3.EVT_SummerJumpChallenge_ServerClaimReward, p_u_15, p17, p18, p19 == nil and {} or p19)
            end;
            p_u_13._player_blob_manager:get_verified_cached_blob(p_u_15.UserId, function(p20) --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_16, (ref 3): v_u_1, (ref 4): v_u_2, (ref 5): v_u_6, (ref 6): v_u_8, (copy 7): f_response, (ref 8): v_u_5, (ref 9): v_u_4, (ref 10): v_u_9, (ref 11): p_u_13, (copy 12): p_u_15, (ref 13): v_u_3 ]]
                local v21 = v_u_7:new()
                if p_u_16 >= v_u_1:get_summer_beach_claim_reward1_count() then
                    for _, v22 in v_u_1:get_summer_beach_claim_reward1_reward_list():key_itr() do
                        v_u_2:is_true(v22:get_type() == v_u_6.RewardType.Gear)
                        if v_u_8:playerblob_get_owned_count_of_equipmentid(p20, v22:get_id()) == 0 then
                            if not v22:can_playerblob_add(p20) then
                                return f_response(false, "Could not add more gear (at max). Please free up space and try again.");
                            end;
                            v21:push_back(v22)
                        end;
                    end;
                end;
                if p_u_16 >= v_u_1:get_summer_beach_claim_reward2_count() then
                    for _, v23 in v_u_1:get_summer_beach_claim_reward2_reward_list():key_itr() do
                        v_u_2:is_true(v23:get_type() == v_u_6.RewardType.Titles)
                        if v23:can_playerblob_add(p20) then
                            v21:push_back(v23)
                        end;
                    end;
                end;
                if p_u_16 >= v_u_1:get_summer_beach_claim_reward3_count() then
                    for _, v24 in v_u_1:get_summer_beach_claim_reward3_reward_list():key_itr() do
                        if v24:get_type() == v_u_6.RewardType.CraftingMaterials then
                            local v25 = v24:get_id()
                            if v_u_5:singleton():get_material(v25):is_fever_icon() == true and (v_u_4:get_count_of_material(p20, v25) == 0 and v_u_9:get_playerblob_collection_type_database_id_owned(p20, v_u_9.Type.Icons, v_u_5:singleton():get_material(v25):get_fever_icon_id(), p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(p20.UserId, p20)) == false) then
                                v21:push_back(v24)
                            end;
                        end;
                    end;
                end;
                if v21:count() == 0 then
                    return f_response(true, "");
                end;
                v_u_6:server_sync_reward_params(p_u_13, p_u_15, v_u_6:claim_reward_info_list_to_playerblob(p_u_13, p20, v21), function(_, _, p26) --[[ Line: 87 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): p_u_15 ]]
                    local v27 = v_u_6.RewardInfo:list_to_table(p26)
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_SummerJumpChallenge_ServerClaimReward, p_u_15, true, "", v27 == nil and {} or v27)
                end)
            end)
        end)
    end;
    p_u_13._evt:wait_on_event(v_u_3.EVT_SummerJumpChallenge_ClientClaimReward, function(p_u_28, p_u_29) --[[ Line: 30 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_13, (ref 3): v_u_3, (ref 4): v_u_7, (ref 5): v_u_1, (ref 6): v_u_6, (ref 7): v_u_8, (ref 8): v_u_5, (ref 9): v_u_4, (ref 10): v_u_9 ]]
        v_u_2:is_int(p_u_29)
        local function f_response(p30, p31, p32) --[[ Name: response ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_28 ]]
            p_u_13._evt:fire_event_to_client(v_u_3.EVT_SummerJumpChallenge_ServerClaimReward, p_u_28, p30, p31, p32 == nil and {} or p32)
        end;
        p_u_13._player_blob_manager:get_verified_cached_blob(p_u_28.UserId, function(p33) --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_29, (ref 3): v_u_1, (ref 4): v_u_2, (ref 5): v_u_6, (ref 6): v_u_8, (copy 7): f_response, (ref 8): v_u_5, (ref 9): v_u_4, (ref 10): v_u_9, (ref 11): p_u_13, (copy 12): p_u_28, (ref 13): v_u_3 ]]
            local v34 = v_u_7:new()
            if p_u_29 >= v_u_1:get_summer_beach_claim_reward1_count() then
                for _, v35 in v_u_1:get_summer_beach_claim_reward1_reward_list():key_itr() do
                    v_u_2:is_true(v35:get_type() == v_u_6.RewardType.Gear)
                    if v_u_8:playerblob_get_owned_count_of_equipmentid(p33, v35:get_id()) == 0 then
                        if not v35:can_playerblob_add(p33) then
                            return f_response(false, "Could not add more gear (at max). Please free up space and try again.");
                        end;
                        v34:push_back(v35)
                    end;
                end;
            end;
            if p_u_29 >= v_u_1:get_summer_beach_claim_reward2_count() then
                for _, v36 in v_u_1:get_summer_beach_claim_reward2_reward_list():key_itr() do
                    v_u_2:is_true(v36:get_type() == v_u_6.RewardType.Titles)
                    if v36:can_playerblob_add(p33) then
                        v34:push_back(v36)
                    end;
                end;
            end;
            if p_u_29 >= v_u_1:get_summer_beach_claim_reward3_count() then
                for _, v37 in v_u_1:get_summer_beach_claim_reward3_reward_list():key_itr() do
                    if v37:get_type() == v_u_6.RewardType.CraftingMaterials then
                        local v38 = v37:get_id()
                        if v_u_5:singleton():get_material(v38):is_fever_icon() == true and (v_u_4:get_count_of_material(p33, v38) == 0 and v_u_9:get_playerblob_collection_type_database_id_owned(p33, v_u_9.Type.Icons, v_u_5:singleton():get_material(v38):get_fever_icon_id(), p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(p33.UserId, p33)) == false) then
                            v34:push_back(v37)
                        end;
                    end;
                end;
            end;
            if v34:count() == 0 then
                return f_response(true, "");
            end;
            v_u_6:server_sync_reward_params(p_u_13, p_u_28, v_u_6:claim_reward_info_list_to_playerblob(p_u_13, p33, v34), function(_, _, p39) --[[ Line: 87 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): p_u_28 ]]
                local v40 = v_u_6.RewardInfo:list_to_table(p39)
                p_u_13._evt:fire_event_to_client(v_u_3.EVT_SummerJumpChallenge_ServerClaimReward, p_u_28, true, "", v40 == nil and {} or v40)
            end)
        end)
    end)
    return v14;
end;
return v10;
