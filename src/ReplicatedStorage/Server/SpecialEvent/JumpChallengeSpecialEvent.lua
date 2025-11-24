-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
local v5 = {}
local v6 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_7 = nil
v6:require_server(function() --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_7 ]]
    v_u_7 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v5.new = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_3 ]]
    local v9 = v_u_7.EventBase:new()
    local function _() --[[ Name: cons ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_2, (ref 3): v_u_1, (ref 4): v_u_4, (ref 5): v_u_3 ]]
        p_u_8._evt:wait_on_event(v_u_2.EVT_JumpChallenge_ClientClaimReward, function(p_u_10, p11) --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_8, (ref 3): v_u_2, (ref 4): v_u_4, (ref 5): v_u_3 ]]
            v_u_1:is_int(p11)
            local function f_response(p12, p13, p14) --[[ Name: response ]] --[[ Line: 27 ]]
                --[[ Upvalues: (ref 1): p_u_8, (ref 2): v_u_2, (copy 3): p_u_10 ]]
                p_u_8._evt:fire_event_to_client(v_u_2.EVT_JumpChallenge_ServerClaimReward, p_u_10, p12, p13, p14 == nil and {} or p14)
            end;
            if p11 ~= v_u_4:get_jump_challenge_1_id() then
                return f_response(false, "Invalid challenge.");
            end;
            p_u_8._player_blob_manager:get_verified_cached_blob(p_u_10.UserId, function(p15) --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): f_response, (ref 3): v_u_3, (ref 4): p_u_8, (copy 5): p_u_10, (ref 6): v_u_2 ]]
                if v_u_4:playerblob_has_claimed_jump_challenge_1_reward(p15) then
                    return f_response(false, "You have already claimed this reward.");
                end;
                local v_u_16 = v_u_3:claim_reward_info_list_to_playerblob(p_u_8, p15, v_u_4:get_jump_challenge_1_reward_desc_info_list())
                v_u_3:server_sync_reward_params(p_u_8, p_u_10, v_u_16, function(p17) --[[ Line: 40 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_16, (ref 3): p_u_8, (ref 4): v_u_2, (ref 5): p_u_10 ]]
                    local v18 = v_u_3.RewardInfo:list_to_table(v_u_3:reward_params_get_resolved_reward_list(v_u_16))
                    p_u_8._evt:fire_event_to_client(v_u_2.EVT_JumpChallenge_ServerClaimReward, p_u_10, true, p17, v18 == nil and {} or v18)
                end)
            end)
        end)
    end;
    p_u_8._evt:wait_on_event(v_u_2.EVT_JumpChallenge_ClientClaimReward, function(p_u_19, p20) --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_8, (ref 3): v_u_2, (ref 4): v_u_4, (ref 5): v_u_3 ]]
        v_u_1:is_int(p20)
        local function f_response(p21, p22, p23) --[[ Name: response ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): p_u_8, (ref 2): v_u_2, (copy 3): p_u_19 ]]
            p_u_8._evt:fire_event_to_client(v_u_2.EVT_JumpChallenge_ServerClaimReward, p_u_19, p21, p22, p23 == nil and {} or p23)
        end;
        if p20 ~= v_u_4:get_jump_challenge_1_id() then
            return f_response(false, "Invalid challenge.");
        end;
        p_u_8._player_blob_manager:get_verified_cached_blob(p_u_19.UserId, function(p24) --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): f_response, (ref 3): v_u_3, (ref 4): p_u_8, (copy 5): p_u_19, (ref 6): v_u_2 ]]
            if v_u_4:playerblob_has_claimed_jump_challenge_1_reward(p24) then
                return f_response(false, "You have already claimed this reward.");
            end;
            local v_u_25 = v_u_3:claim_reward_info_list_to_playerblob(p_u_8, p24, v_u_4:get_jump_challenge_1_reward_desc_info_list())
            v_u_3:server_sync_reward_params(p_u_8, p_u_19, v_u_25, function(p26) --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_25, (ref 3): p_u_8, (ref 4): v_u_2, (ref 5): p_u_19 ]]
                local v27 = v_u_3.RewardInfo:list_to_table(v_u_3:reward_params_get_resolved_reward_list(v_u_25))
                p_u_8._evt:fire_event_to_client(v_u_2.EVT_JumpChallenge_ServerClaimReward, p_u_19, true, p26, v27 == nil and {} or v27)
            end)
        end)
    end)
    return v9;
end;
return v5;
