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
    --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_6, (copy 3): v_u_8, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_9, (copy 7): v_u_7, (copy 8): v_u_1, (copy 9): v_u_3, (copy 10): v_u_2 ]]
    local v14 = v_u_12.EventBase:new()
    local function f_test_reward_info_playerblob_can_grant(p15, p16) --[[ Name: test_reward_info_playerblob_can_grant ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_8, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_9, (copy 6): p_u_13 ]]
        local v17 = false
        local v18 = false
        local v19 = ""
        if p15:get_type() == v_u_6.RewardType.Gear then
            if v_u_8:playerblob_get_owned_count_of_equipmentid(p16, p15:get_id()) == 0 then
                if p15:can_playerblob_add(p16) then
                    return true, v18, v19;
                else
                    return v17, true, "Could not add more gear (at max). Please free up space and try again.";
                end;
            end;
        elseif p15:get_type() == v_u_6.RewardType.Titles then
            if p15:can_playerblob_add(p16) then
                return true, v18, v19;
            end;
        elseif p15:get_type() == v_u_6.RewardType.CraftingMaterials then
            local v20 = p15:get_id()
            if v_u_5:singleton():get_material(v20):is_fever_icon() == true then
                v17 = v_u_4:get_count_of_material(p16, v20) == 0 and v_u_9:get_playerblob_collection_type_database_id_owned(p16, v_u_9.Type.Icons, v_u_5:singleton():get_material(v20):get_fever_icon_id(), p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(p16.UserId, p16)) == false and true or v17
            end;
        end;
        return v17, v18, v19;
    end;
    local v_u_21 = v_u_7:new({
        { v_u_1:get_autumn_claim_reward1_count(), v_u_1:get_autumn_claim_reward1_reward_list() },
        { v_u_1:get_autumn_claim_reward2_count(), v_u_1:get_autumn_claim_reward2_reward_list() },
        { v_u_1:get_autumn_claim_reward3_count(), v_u_1:get_autumn_claim_reward3_reward_list() }
    })
    local function _() --[[ Name: cons ]] --[[ Line: 75 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_3, (ref 3): v_u_2, (ref 4): v_u_7, (copy 5): v_u_21, (copy 6): f_test_reward_info_playerblob_can_grant, (ref 7): v_u_6 ]]
        p_u_13._evt:wait_on_event(v_u_3.EVT_AutumnJumpChallenge_ClientClaimReward, function(p_u_22, p_u_23) --[[ Line: 76 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): v_u_7, (ref 5): v_u_21, (ref 6): f_test_reward_info_playerblob_can_grant, (ref 7): v_u_6 ]]
            v_u_2:is_int(p_u_23)
            local function f_response(p24, p25, p26) --[[ Name: response ]] --[[ Line: 81 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_22 ]]
                p_u_13._evt:fire_event_to_client(v_u_3.EVT_AutumnJumpChallenge_ServerClaimReward, p_u_22, p24, p25, p26 == nil and {} or p26)
            end;
            p_u_13._player_blob_manager:get_verified_cached_blob(p_u_22.UserId, function(p27) --[[ Line: 88 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_21, (copy 3): p_u_23, (ref 4): f_test_reward_info_playerblob_can_grant, (copy 5): f_response, (ref 6): v_u_6, (ref 7): p_u_13, (copy 8): p_u_22, (ref 9): v_u_3 ]]
                local v28 = v_u_7:new()
                for v29 = 1, v_u_21:count() do
                    local v30 = v_u_21:get(v29)
                    local v31 = v30[1]
                    local v32 = v30[2]
                    if v31 <= p_u_23 then
                        for _, v33 in v32:key_itr() do
                            local v34, v35, v36 = f_test_reward_info_playerblob_can_grant(v33, p27)
                            if v35 == true then
                                return f_response(false, v36);
                            end;
                            if v34 == true then
                                v28:push_back(v33)
                            end;
                        end;
                    end;
                end;
                if v28:count() == 0 then
                    return f_response(true, "");
                end;
                v_u_6:server_sync_reward_params(p_u_13, p_u_22, v_u_6:claim_reward_info_list_to_playerblob(p_u_13, p27, v28), function(_, _, p37) --[[ Line: 120 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): p_u_22 ]]
                    local v38 = v_u_6.RewardInfo:list_to_table(p37)
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_AutumnJumpChallenge_ServerClaimReward, p_u_22, true, "", v38 == nil and {} or v38)
                end)
            end)
        end)
    end;
    p_u_13._evt:wait_on_event(v_u_3.EVT_AutumnJumpChallenge_ClientClaimReward, function(p_u_39, p_u_40) --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_13, (ref 3): v_u_3, (ref 4): v_u_7, (copy 5): v_u_21, (copy 6): f_test_reward_info_playerblob_can_grant, (ref 7): v_u_6 ]]
        v_u_2:is_int(p_u_40)
        local function f_response(p41, p42, p43) --[[ Name: response ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_39 ]]
            p_u_13._evt:fire_event_to_client(v_u_3.EVT_AutumnJumpChallenge_ServerClaimReward, p_u_39, p41, p42, p43 == nil and {} or p43)
        end;
        p_u_13._player_blob_manager:get_verified_cached_blob(p_u_39.UserId, function(p44) --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_21, (copy 3): p_u_40, (ref 4): f_test_reward_info_playerblob_can_grant, (copy 5): f_response, (ref 6): v_u_6, (ref 7): p_u_13, (copy 8): p_u_39, (ref 9): v_u_3 ]]
            local v45 = v_u_7:new()
            for v46 = 1, v_u_21:count() do
                local v47 = v_u_21:get(v46)
                local v48 = v47[1]
                local v49 = v47[2]
                if v48 <= p_u_40 then
                    for _, v50 in v49:key_itr() do
                        local v51, v52, v53 = f_test_reward_info_playerblob_can_grant(v50, p44)
                        if v52 == true then
                            return f_response(false, v53);
                        end;
                        if v51 == true then
                            v45:push_back(v50)
                        end;
                    end;
                end;
            end;
            if v45:count() == 0 then
                return f_response(true, "");
            end;
            v_u_6:server_sync_reward_params(p_u_13, p_u_39, v_u_6:claim_reward_info_list_to_playerblob(p_u_13, p44, v45), function(_, _, p54) --[[ Line: 120 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): p_u_39 ]]
                local v55 = v_u_6.RewardInfo:list_to_table(p54)
                p_u_13._evt:fire_event_to_client(v_u_3.EVT_AutumnJumpChallenge_ServerClaimReward, p_u_39, true, "", v55 == nil and {} or v55)
            end)
        end)
    end)
    return v14;
end;
return v10;
