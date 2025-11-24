-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v4 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_5 = nil
v4:require_shared(function() --[[ Line: 11 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    v_u_5 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local v_u_9 = {
    ["is_event_active"] = function(_, _) --[[ Name: is_event_active ]] --[[ Line: 17 ]]
        return false;
    end,
    ["get_playable_song_set"] = function(_) --[[ Name: get_playable_song_set ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({});
    end,
    ["get_song_launch_claimed_id"] = function(_) --[[ Name: get_song_launch_claimed_id ]] --[[ Line: 41 ]]
        return 43;
    end,
    ["get_dance_id"] = function(_) --[[ Name: get_dance_id ]] --[[ Line: 50 ]]
        return 164;
    end,
    ["get_stage_id"] = function(_) --[[ Name: get_stage_id ]] --[[ Line: 51 ]]
        return 8;
    end,
    ["get_reward_info_list"] = function(_) --[[ Name: get_reward_info_list ]] --[[ Line: 53 ]]
        --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_5 ]]
        local v6 = v_u_2:new()
        v_u_5.RewardInfo:add_rewards_list_from_table(v6, {})
        return v6;
    end,
    ["playerblob_owns_song"] = function(_, _, _, _, _) --[[ Name: playerblob_owns_song ]] --[[ Line: 64 ]]
        return false;
    end,
    ["get_backup_dancer_npc_id"] = function(_) --[[ Name: get_backup_dancer_npc_id ]] --[[ Line: 75 ]]
        return "NPC_JoanEventA";
    end,
    ["get_npc_title"] = function(_) --[[ Name: get_npc_title ]] --[[ Line: 79 ]]
        return "joan";
    end,
    ["should_show_hud_button"] = function(_) --[[ Name: should_show_hud_button ]] --[[ Line: 83 ]]
        return false;
    end,
    ["get_hud_button_assetid"] = function(_) --[[ Name: get_hud_button_assetid ]] --[[ Line: 84 ]]
        return "rbxassetid://10207465331";
    end,
    ["get_claim_reward1_count"] = function(_) --[[ Name: get_claim_reward1_count ]] --[[ Line: 86 ]]
        return 4;
    end,
    ["get_claim_reward1_reward_list"] = function(_) --[[ Name: get_claim_reward1_reward_list ]] --[[ Line: 88 ]]
        --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_5 ]]
        local v7 = v_u_2:new()
        v_u_5.RewardInfo:add_rewards_list_from_table(v7, {
            {
                ["Type"] = v_u_5.RewardType.Gear,
                ["Id"] = 216,
                ["Amount"] = 1
            }
        })
        return v7;
    end,
    ["get_claim_reward2_count"] = function(_) --[[ Name: get_claim_reward2_count ]] --[[ Line: 95 ]]
        return 8;
    end,
    ["get_claim_reward2_reward_list"] = function(_) --[[ Name: get_claim_reward2_reward_list ]] --[[ Line: 97 ]]
        --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_5 ]]
        local v8 = v_u_2:new()
        v_u_5.RewardInfo:add_rewards_list_from_table(v8, {
            {
                ["Type"] = v_u_5.RewardType.Titles,
                ["Id"] = 92,
                ["Amount"] = 1
            }
        })
        return v8;
    end
}
v_u_9.is_event_active_or_playerblob_tester_status = function(_, p10, p11) --[[ Name: is_event_active_or_playerblob_tester_status ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_3 ]]
    return v_u_9:is_event_active(p10) or v_u_3:is_tester_status(p11);
end;
v_u_9.set_playerblob_claimed = function(_, p12) --[[ Name: set_playerblob_claimed ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    p12.SongLaunchClaimedID = v_u_9:get_song_launch_claimed_id()
end;
v_u_9.test_playerblob_has_claimed_reward = function(_, p13) --[[ Name: test_playerblob_has_claimed_reward ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    return p13.SongLaunchClaimedID >= v_u_9:get_song_launch_claimed_id();
end;
return v_u_9;
