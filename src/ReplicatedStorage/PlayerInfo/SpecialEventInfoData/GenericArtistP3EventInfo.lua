-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_5 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_6 = require(game.ReplicatedStorage.GameStage.GameStageUtil)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.FeverIconInfo)
local v_u_8 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_18 = {
    ["is_event_active"] = function(_, _, _) --[[ Name: is_event_active ]] --[[ Line: 17 ]]
        return false;
    end,
    ["get_playable_song_set"] = function(_) --[[ Name: get_playable_song_set ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({});
    end,
    ["get_required_song_set"] = function(_) --[[ Name: get_required_song_set ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new():add_set_from_table_list({});
    end,
    ["get_required_song_set_owned_count"] = function(_) --[[ Name: get_required_song_set_owned_count ]] --[[ Line: 37 ]]
        return 2;
    end,
    ["playerblob_owns_song"] = function(_, p9, p10, p11, p12) --[[ Name: playerblob_owns_song ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3 ]]
        if p11 == nil then
            p11 = v_u_4:song_inventory_songids_set(p9)
        end;
        if p12 == nil then
            p12 = v_u_3:get_collection_info_from_playerblob(p9)
        end;
        return p11:contains(p10) or v_u_3:get_playerblob_songkey_in_collection(p9, p10, p12);
    end,
    ["test_playerblob_has_claimed_stage_reward"] = function(_, p13, p14) --[[ Name: test_playerblob_has_claimed_stage_reward ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        return v_u_6:playerblob_get_owned_stage_ids_set(p13, p14):contains(21);
    end,
    ["test_playerblob_has_claimed_gear_reward"] = function(_, p15) --[[ Name: test_playerblob_has_claimed_gear_reward ]] --[[ Line: 89 ]]
        --[[ Upvalues: (copy 1): v_u_8 ]]
        return v_u_8:playerblob_get_owned_count_of_equipmentid(p15, 224) >= 1;
    end,
    ["get_stage_id"] = function(_) --[[ Name: get_stage_id ]] --[[ Line: 97 ]]
        return 21;
    end,
    ["get_backup_dancer_npc_id"] = function(_) --[[ Name: get_backup_dancer_npc_id ]] --[[ Line: 101 ]]
        return "NPC_NoScopeJess";
    end,
    ["external_badge_reward_enabled"] = function(_) --[[ Name: external_badge_reward_enabled ]] --[[ Line: 121 ]]
        return true;
    end,
    ["test_playerblob_has_claimed_external_badge_reward"] = function(_, p16, p17) --[[ Name: test_playerblob_has_claimed_external_badge_reward ]] --[[ Line: 124 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        return v_u_7:get_playerblob_fevericon_owned_set(p16, 0, p17):contains(172);
    end
}
v_u_18.get_playerblob_owned_required_song_count = function(_, p19, p20) --[[ Name: get_playerblob_owned_required_song_count ]] --[[ Line: 51 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_18 ]]
    local v21 = v_u_4:song_inventory_songids_set(p19)
    local v22 = 0
    for v23, _ in v_u_18:get_required_song_set():key_itr() do
        if v_u_18:playerblob_owns_song(p19, v23, v21, p20) then
            v22 = v22 + 1
        end;
    end;
    return v22;
end;
local v24 = v2:new()
v_u_5.RewardInfo:add_rewards_list_from_table(v24, {
    {
        ["Type"] = v_u_5.RewardType.CraftingMaterials,
        ["Id"] = 346,
        ["Amount"] = 1
    }
})
local v_u_25 = v24
v_u_18.get_reward_stage_list = function(_) --[[ Name: get_reward_stage_list ]] --[[ Line: 76 ]]
    --[[ Upvalues: (ref 1): v_u_25 ]]
    return v_u_25;
end;
local v26 = v2:new()
v_u_5.RewardInfo:add_rewards_list_from_table(v26, {
    {
        ["Type"] = v_u_5.RewardType.Gear,
        ["Id"] = 224,
        ["Amount"] = 1
    }
})
local v_u_27 = v26
v_u_18.get_reward_gear_list = function(_) --[[ Name: get_reward_gear_list ]] --[[ Line: 87 ]]
    --[[ Upvalues: (ref 1): v_u_27 ]]
    return v_u_27;
end;
v_u_18.test_playerblob_has_claimed_reward = function(_, p28, p29) --[[ Name: test_playerblob_has_claimed_reward ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_18 ]]
    local v30 = v_u_18:test_playerblob_has_claimed_stage_reward(p28, p29)
    if v30 then
        v30 = v_u_18:test_playerblob_has_claimed_gear_reward(p28, p29)
    end;
    return v30;
end;
local v31 = v2:new()
v31:push_back(v_u_25:get(1))
v31:push_back(v_u_27:get(1))
local v_u_32 = v_u_5.RewardInfo:list_to_table(v31)
v_u_18.get_reward_info_list = function(_) --[[ Name: get_reward_info_list ]] --[[ Line: 117 ]]
    --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_32 ]]
    return v_u_5.RewardInfo:table_to_list(v_u_32);
end;
local v33 = v2:new()
v_u_5.RewardInfo:add_rewards_list_from_table(v33, {
    {
        ["Type"] = v_u_5.RewardType.CraftingMaterials,
        ["Id"] = 355,
        ["Amount"] = 1
    }
})
local v_u_34 = v_u_5.RewardInfo:list_to_table(v33)
v_u_18.get_external_badge_reward_info_list = function(_) --[[ Name: get_external_badge_reward_info_list ]] --[[ Line: 142 ]]
    --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_34 ]]
    return v_u_5.RewardInfo:table_to_list(v_u_34);
end;
return v_u_18;
