-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_5 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v6 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_7 = nil
v6:require_shared(function() --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_7 ]]
    v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local function _(p8) --[[ Name: is_event_active ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v9, v10 = p8:is_event_type_active(v_u_1.EventType.HalloweenCountdown)
    return v9 and v10 == 9 and true or false;
end;
return {
    ["get_listening_party_reward_list"] = function(_) --[[ Name: get_listening_party_reward_list ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_7 ]]
        local v11 = v_u_2:new()
        v_u_7.RewardInfo:add_rewards_list_from_table(v11, {
            {
                ["Type"] = v_u_7.RewardType.CraftingMaterials,
                ["Id"] = 412,
                ["Amount"] = 1
            }
        })
        return v11;
    end,
    ["playerblob_test_owns_listening_party_reward"] = function(_, p12, p13) --[[ Name: playerblob_test_owns_listening_party_reward ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4 ]]
        return v_u_5:get_count_of_material(p12, 412) > 0 and true or v_u_4:get_playerblob_collection_type_database_id_owned(p12, v_u_4.Type.Icons, 212, p13) == true;
    end,
    ["is_event_active"] = function(_, p14, p15) --[[ Name: is_event_active ]] --[[ Line: 56 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
        local v16, v17 = p14:is_event_type_active(v_u_1.EventType.HalloweenCountdown)
        return (v16 and v17 == 9 and true or false) == true and true or v_u_3:is_tester_status(p15) == true;
    end
};
