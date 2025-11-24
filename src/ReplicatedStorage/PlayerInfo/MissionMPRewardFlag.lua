-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPUtil)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = nil
v3:require_shared(function() --[[ Line: 9 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local v8 = {
    ["Flag"] = {
        ["MissionMPReward1"] = 0,
        ["MissionMPReward2"] = 1,
        ["MissionMPReward3"] = 2
    },
    ["playerblob_has_flag_set"] = function(_, p5, p6, p7) --[[ Name: playerblob_has_flag_set ]] --[[ Line: 56 ]]
        if p5.MissionMPRewardDayID == p7 then
            return bit32.band(p5.MissionMPRewardFlag, (bit32.lshift(1, p6))) ~= 0;
        else
            return false;
        end;
    end
}
local v_u_9 = {
    ["MissionMPReward1"] = 0,
    ["MissionMPReward2"] = 1,
    ["MissionMPReward3"] = 2
}
v8.flag_to_unclaimed_reward_desc_info_list = function(_, p10) --[[ Name: flag_to_unclaimed_reward_desc_info_list ]] --[[ Line: 22 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_9, (copy 3): v_u_1, (ref 4): v_u_4 ]]
    v_u_2:is_enum_member(p10, v_u_9)
    local v11 = v_u_1:new()
    if p10 == v_u_9.MissionMPReward1 then
        v11:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 1, -1))
        v11:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 100, -1))
        return v11;
    end;
    if p10 ~= v_u_9.MissionMPReward2 then
        if p10 == v_u_9.MissionMPReward3 then
            v11:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 3, -1))
            v11:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 200, -1))
        end;
        return v11;
    end;
    v11:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 2, -1))
    v11:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 150, -1))
    return v11;
end;
v8.flag_to_claimed_reward_desc_info_list = function(_, p12) --[[ Name: flag_to_claimed_reward_desc_info_list ]] --[[ Line: 40 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_9, (copy 3): v_u_1, (ref 4): v_u_4 ]]
    v_u_2:is_enum_member(p12, v_u_9)
    local v13 = v_u_1:new()
    if p12 == v_u_9.MissionMPReward1 then
        v13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 100, -1))
        return v13;
    elseif p12 == v_u_9.MissionMPReward2 then
        v13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 150, -1))
        return v13;
    else
        if p12 == v_u_9.MissionMPReward3 then
            v13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 200, -1))
        end;
        return v13;
    end;
end;
v8.playerblob_set_flag = function(_, p14, p15, p16) --[[ Name: playerblob_set_flag ]] --[[ Line: 64 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_9 ]]
    v_u_2:is_enum_member(p15, v_u_9)
    v_u_2:is_int(p16)
    if p14.MissionMPRewardDayID ~= p16 then
        p14.MissionMPRewardFlag = 0
    end;
    p14.MissionMPRewardFlag = bit32.bor(p14.MissionMPRewardFlag, (bit32.lshift(1, p15)))
    p14.MissionMPRewardDayID = p16
end;
return v8;
