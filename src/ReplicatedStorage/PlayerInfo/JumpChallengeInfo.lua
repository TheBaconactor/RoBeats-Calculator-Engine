-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v12 = {
    ["playerblob_has_claimed_jump_challenge_1_reward"] = function(_, p4) --[[ Name: playerblob_has_claimed_jump_challenge_1_reward ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        return v_u_3:owns_title_id(p4, 77);
    end,
    ["get_jump_challenge_1_id"] = function(_) --[[ Name: get_jump_challenge_1_id ]] --[[ Line: 13 ]]
        return 1;
    end,
    ["get_summer_beach_claim_reward1_count"] = function(_) --[[ Name: get_summer_beach_claim_reward1_count ]] --[[ Line: 17 ]]
        return 4;
    end,
    ["get_summer_beach_claim_reward1_reward_list"] = function(_) --[[ Name: get_summer_beach_claim_reward1_reward_list ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v5 = v_u_2:new()
        v_u_1.RewardInfo:add_rewards_list_from_table(v5, {
            {
                ["Type"] = v_u_1.RewardType.Gear,
                ["Id"] = 216,
                ["Amount"] = 1
            }
        })
        return v5;
    end,
    ["get_summer_beach_claim_reward2_count"] = function(_) --[[ Name: get_summer_beach_claim_reward2_count ]] --[[ Line: 25 ]]
        return 8;
    end,
    ["get_summer_beach_claim_reward2_reward_list"] = function(_) --[[ Name: get_summer_beach_claim_reward2_reward_list ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v6 = v_u_2:new()
        v_u_1.RewardInfo:add_rewards_list_from_table(v6, {
            {
                ["Type"] = v_u_1.RewardType.Titles,
                ["Id"] = 92,
                ["Amount"] = 1
            }
        })
        return v6;
    end,
    ["get_summer_beach_claim_reward3_count"] = function(_) --[[ Name: get_summer_beach_claim_reward3_count ]] --[[ Line: 33 ]]
        return 10;
    end,
    ["get_summer_beach_claim_reward3_reward_list"] = function(_) --[[ Name: get_summer_beach_claim_reward3_reward_list ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v7 = v_u_2:new()
        v_u_1.RewardInfo:add_rewards_list_from_table(v7, {
            {
                ["Type"] = v_u_1.RewardType.CraftingMaterials,
                ["Id"] = 450,
                ["Amount"] = 1
            }
        })
        return v7;
    end,
    ["get_carnival_reward_count"] = function(_) --[[ Name: get_carnival_reward_count ]] --[[ Line: 44 ]]
        return 4;
    end,
    ["get_carnival_reward_list"] = function(_) --[[ Name: get_carnival_reward_list ]] --[[ Line: 46 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v8 = v_u_2:new()
        v_u_1.RewardInfo:add_rewards_list_from_table(v8, {
            {
                ["Type"] = v_u_1.RewardType.Titles,
                ["Id"] = 100,
                ["Amount"] = 1
            },
            {
                ["Type"] = v_u_1.RewardType.CraftingMaterials,
                ["Id"] = 339,
                ["Amount"] = 1
            }
        })
        return v8;
    end,
    ["get_autumn_claim_reward1_count"] = function(_) --[[ Name: get_autumn_claim_reward1_count ]] --[[ Line: 57 ]]
        return 3;
    end,
    ["get_autumn_claim_reward1_reward_list"] = function(_) --[[ Name: get_autumn_claim_reward1_reward_list ]] --[[ Line: 58 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v9 = v_u_2:new()
        v_u_1.RewardInfo:add_rewards_list_from_table(v9, {
            {
                ["Type"] = v_u_1.RewardType.Gear,
                ["Id"] = 239,
                ["Amount"] = 1
            }
        })
        return v9;
    end,
    ["get_autumn_claim_reward2_count"] = function(_) --[[ Name: get_autumn_claim_reward2_count ]] --[[ Line: 66 ]]
        return 6;
    end,
    ["get_autumn_claim_reward2_reward_list"] = function(_) --[[ Name: get_autumn_claim_reward2_reward_list ]] --[[ Line: 67 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v10 = v_u_2:new()
        v_u_1.RewardInfo:add_rewards_list_from_table(v10, {
            {
                ["Type"] = v_u_1.RewardType.CraftingMaterials,
                ["Id"] = 413,
                ["Amount"] = 1
            }
        })
        return v10;
    end,
    ["get_autumn_claim_reward3_count"] = function(_) --[[ Name: get_autumn_claim_reward3_count ]] --[[ Line: 75 ]]
        return 10;
    end,
    ["get_autumn_claim_reward3_reward_list"] = function(_) --[[ Name: get_autumn_claim_reward3_reward_list ]] --[[ Line: 76 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v11 = v_u_2:new()
        v_u_1.RewardInfo:add_rewards_list_from_table(v11, {
            {
                ["Type"] = v_u_1.RewardType.Titles,
                ["Id"] = 136,
                ["Amount"] = 1
            }
        })
        return v11;
    end
}
local v_u_13 = v_u_2:new({ v_u_1.RewardInfo:new(v_u_1.RewardType.Titles, 1, 77) })
v12.get_jump_challenge_1_reward_desc_info_list = function(_) --[[ Name: get_jump_challenge_1_reward_desc_info_list ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13;
end;
return v12;
