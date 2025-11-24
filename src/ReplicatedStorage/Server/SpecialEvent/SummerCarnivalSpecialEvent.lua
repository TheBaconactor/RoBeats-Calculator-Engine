-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:20 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_3 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_4 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_5 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local _ = game:GetService("BadgeService")
local _ = game:GetService("TeleportService")
local v_u_9 = require(game.ReplicatedStorage.Shared.SPDict)
local v10 = {}
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
v11:require_server(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v10.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_9, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_6, (copy 6): v_u_7, (copy 7): v_u_5, (copy 8): v_u_4, (copy 9): v_u_3, (copy 10): v_u_8 ]]
    local v14 = v_u_12.EventBase:new()
    local v_u_15 = v_u_9:new()
    local function _() --[[ Name: cons ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_1, (copy 4): v_u_15, (ref 5): v_u_6, (ref 6): v_u_7, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_3, (ref 10): v_u_8 ]]
        p_u_13._evt:wait_on_event(v_u_2.EVT_CarnivalJumpChallenge_ClientClaimReward, function(p_u_16, p_u_17) --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_13, (ref 3): v_u_2, (ref 4): v_u_15, (ref 5): v_u_6, (ref 6): v_u_7, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_3, (ref 10): v_u_8 ]]
            v_u_1:is_int(p_u_17)
            local function f_response(p18, p19, p20) --[[ Name: response ]] --[[ Line: 36 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (copy 3): p_u_16 ]]
                p_u_13._evt:fire_event_to_client(v_u_2.EVT_CarnivalJumpChallenge_ServerClaimReward, p_u_16, p18, p19, p20 == nil and {} or p20)
            end;
            if v_u_15:contains(p_u_16.UserId) then
                return f_response(true, "Already claimed.");
            end;
            p_u_13._player_blob_manager:get_verified_cached_blob(p_u_16.UserId, function(p21) --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_17, (ref 3): v_u_7, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): v_u_3, (ref 7): v_u_8, (ref 8): p_u_13, (ref 9): v_u_15, (copy 10): p_u_16, (copy 11): f_response, (ref 12): v_u_2 ]]
                local v22 = v_u_6:new()
                if p_u_17 >= v_u_7:get_carnival_reward_count() then
                    for _, v23 in v_u_7:get_carnival_reward_list():key_itr() do
                        if v23:get_type() == v_u_5.RewardType.Titles then
                            if v23:can_playerblob_add(p21) then
                                v22:push_back(v23)
                            end;
                        elseif v23:get_type() == v_u_5.RewardType.CraftingMaterials then
                            local v24 = v23:get_id()
                            if v_u_4:singleton():get_material(v24):is_fever_icon() == true and (v_u_3:get_count_of_material(p21, v24) == 0 and v_u_8:get_playerblob_collection_type_database_id_owned(p21, v_u_8.Type.Icons, v_u_4:singleton():get_material(v24):get_fever_icon_id(), p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(p21.UserId, p21)) == false) then
                                v_u_15:add_set(p_u_16.UserId)
                                v22:push_back(v23)
                            end;
                        end;
                    end;
                end;
                if v22:count() == 0 then
                    return f_response(true, "");
                end;
                v_u_5:server_sync_reward_params(p_u_13, p_u_16, v_u_5:claim_reward_info_list_to_playerblob(p_u_13, p21, v22), function(_, _, p25) --[[ Line: 80 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_13, (ref 3): v_u_2, (ref 4): p_u_16 ]]
                    local v26 = v_u_5.RewardInfo:list_to_table(p25)
                    p_u_13._evt:fire_event_to_client(v_u_2.EVT_CarnivalJumpChallenge_ServerClaimReward, p_u_16, true, "", v26 == nil and {} or v26)
                end)
            end)
        end)
    end;
    p_u_13._evt:wait_on_event(v_u_2.EVT_CarnivalJumpChallenge_ClientClaimReward, function(p_u_27, p_u_28) --[[ Line: 33 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_13, (ref 3): v_u_2, (copy 4): v_u_15, (ref 5): v_u_6, (ref 6): v_u_7, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_3, (ref 10): v_u_8 ]]
        v_u_1:is_int(p_u_28)
        local function f_response(p29, p30, p31) --[[ Name: response ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (copy 3): p_u_27 ]]
            p_u_13._evt:fire_event_to_client(v_u_2.EVT_CarnivalJumpChallenge_ServerClaimReward, p_u_27, p29, p30, p31 == nil and {} or p31)
        end;
        if v_u_15:contains(p_u_27.UserId) then
            return f_response(true, "Already claimed.");
        end;
        p_u_13._player_blob_manager:get_verified_cached_blob(p_u_27.UserId, function(p32) --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_28, (ref 3): v_u_7, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): v_u_3, (ref 7): v_u_8, (ref 8): p_u_13, (ref 9): v_u_15, (copy 10): p_u_27, (copy 11): f_response, (ref 12): v_u_2 ]]
            local v33 = v_u_6:new()
            if p_u_28 >= v_u_7:get_carnival_reward_count() then
                for _, v34 in v_u_7:get_carnival_reward_list():key_itr() do
                    if v34:get_type() == v_u_5.RewardType.Titles then
                        if v34:can_playerblob_add(p32) then
                            v33:push_back(v34)
                        end;
                    elseif v34:get_type() == v_u_5.RewardType.CraftingMaterials then
                        local v35 = v34:get_id()
                        if v_u_4:singleton():get_material(v35):is_fever_icon() == true and (v_u_3:get_count_of_material(p32, v35) == 0 and v_u_8:get_playerblob_collection_type_database_id_owned(p32, v_u_8.Type.Icons, v_u_4:singleton():get_material(v35):get_fever_icon_id(), p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(p32.UserId, p32)) == false) then
                            v_u_15:add_set(p_u_27.UserId)
                            v33:push_back(v34)
                        end;
                    end;
                end;
            end;
            if v33:count() == 0 then
                return f_response(true, "");
            end;
            v_u_5:server_sync_reward_params(p_u_13, p_u_27, v_u_5:claim_reward_info_list_to_playerblob(p_u_13, p32, v33), function(_, _, p36) --[[ Line: 80 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_13, (ref 3): v_u_2, (ref 4): p_u_27 ]]
                local v37 = v_u_5.RewardInfo:list_to_table(p36)
                p_u_13._evt:fire_event_to_client(v_u_2.EVT_CarnivalJumpChallenge_ServerClaimReward, p_u_27, true, "", v37 == nil and {} or v37)
            end)
        end)
    end)
    return v14;
end;
return v10;
