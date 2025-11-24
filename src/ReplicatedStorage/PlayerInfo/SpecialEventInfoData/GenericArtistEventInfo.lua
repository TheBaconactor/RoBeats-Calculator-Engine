-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_6 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_13 = {
    ["is_event_active"] = function(_, _) --[[ Name: is_event_active ]] --[[ Line: 14 ]]
        return false;
    end,
    ["get_playable_song_set"] = function(_) --[[ Name: get_playable_song_set ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({});
    end,
    ["get_required_song_set"] = function(_) --[[ Name: get_required_song_set ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({});
    end,
    ["playerblob_owns_song"] = function(_, p7, p8, p9, p10) --[[ Name: playerblob_owns_song ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4 ]]
        if p9 == nil then
            p9 = v_u_5:song_inventory_songids_set(p7)
        end;
        if p10 == nil then
            p10 = v_u_4:get_collection_info_from_playerblob(p7)
        end;
        return p9:contains(p8) or v_u_4:get_playerblob_songkey_in_collection(p7, p8, p10);
    end,
    ["test_playerblob_has_claimed_reward"] = function(_, p11) --[[ Name: test_playerblob_has_claimed_reward ]] --[[ Line: 66 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        return v_u_2:get_owned_danceid_to_equipped_dict(p11):contains(241);
    end,
    ["get_stage_id"] = function(_) --[[ Name: get_stage_id ]] --[[ Line: 71 ]]
        return 1;
    end,
    ["get_backup_dancer_npc_id"] = function(_) --[[ Name: get_backup_dancer_npc_id ]] --[[ Line: 75 ]]
        return "NPC_SuperLeagueArcade";
    end,
    ["external_badge_reward_enabled"] = function(_) --[[ Name: external_badge_reward_enabled ]] --[[ Line: 97 ]]
        return false;
    end,
    ["test_playerblob_has_claimed_external_badge_reward"] = function(_, p12) --[[ Name: test_playerblob_has_claimed_external_badge_reward ]] --[[ Line: 102 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        return v_u_5:owns_title_id(p12, 71);
    end
}
v_u_13.get_playerblob_owned_required_song_count = function(_, p14, p15) --[[ Name: get_playerblob_owned_required_song_count ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_13 ]]
    local v16 = v_u_5:song_inventory_songids_set(p14)
    local v17 = 0
    for v18, _ in v_u_13:get_required_song_set():key_itr() do
        if v_u_13:playerblob_owns_song(p14, v18, v16, p15) then
            v17 = v17 + 1
        end;
    end;
    return v17;
end;
local v19 = v3:new()
v_u_6.RewardInfo:add_rewards_list_from_table(v19, {})
local v_u_20 = v_u_6.RewardInfo:list_to_table(v19)
v_u_13.get_reward_info_list = function(_) --[[ Name: get_reward_info_list ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_20 ]]
    return v_u_6.RewardInfo:table_to_list(v_u_20);
end;
local v21 = v3:new()
v_u_6.RewardInfo:add_rewards_list_from_table(v21, {})
local v_u_22 = v_u_6.RewardInfo:list_to_table(v21)
v_u_13.get_external_badge_reward_info_list = function(_) --[[ Name: get_external_badge_reward_info_list ]] --[[ Line: 116 ]]
    --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_22 ]]
    return v_u_6.RewardInfo:table_to_list(v_u_22);
end;
return v_u_13;
