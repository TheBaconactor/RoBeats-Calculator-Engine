-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = nil
v3:require_shared(function() --[[ Line: 6 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local v_u_8 = {
    ["get_level_to_max_gear_slot_count"] = function(_, p5) --[[ Name: get_level_to_max_gear_slot_count ]] --[[ Line: 14 ]]
        return p5 == 1 and 60 or (p5 == 2 and 70 or (p5 == 3 and 80 or (p5 == 4 and 90 or (p5 == 5 and 100 or 50))));
    end,
    ["get_currency_to_next_level"] = function(_, p6) --[[ Name: get_currency_to_next_level ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local l_Stars_0 = v_u_1.CurrencyType.Stars
        if p6 == 1 then
            return 100, l_Stars_0;
        elseif p6 == 2 then
            return 200, l_Stars_0;
        elseif p6 == 3 then
            return 400, l_Stars_0;
        elseif p6 == 4 then
            return 800, l_Stars_0;
        else
            return 50, l_Stars_0;
        end;
    end,
    ["playerblob_get_gear_slot_increase_level"] = function(_, p7) --[[ Name: playerblob_get_gear_slot_increase_level ]] --[[ Line: 45 ]]
        return p7.GSLvl;
    end
}
v_u_8.can_playerblob_increase_level = function(_, p9) --[[ Name: can_playerblob_increase_level ]] --[[ Line: 49 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    return v_u_8:playerblob_get_gear_slot_increase_level(p9) < 5;
end;
v_u_8.playerblob_do_increment_max_gear_slot_level = function(_, p10) --[[ Name: playerblob_do_increment_max_gear_slot_level ]] --[[ Line: 53 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    if not v_u_8:can_playerblob_increase_level(p10) then
        return false;
    end;
    p10.GSLvl = v_u_8:playerblob_get_gear_slot_increase_level(p10) + 1
    return true;
end;
v_u_8.playerblob_get_max_gear_slot_count = function(_, p11) --[[ Name: playerblob_get_max_gear_slot_count ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    return v_u_8:get_level_to_max_gear_slot_count(v_u_8:playerblob_get_gear_slot_increase_level(p11));
end;
v_u_8.playerblob_get_available_reward_desc_info_list = function(_, p_u_12) --[[ Name: playerblob_get_available_reward_desc_info_list ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (ref 3): v_u_4, (copy 4): v_u_8 ]]
    local v_u_13 = v_u_2:new()
    local function _(p14) --[[ Name: add_title_if_not_owned ]] --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_12, (copy 3): v_u_13, (ref 4): v_u_4 ]]
        if v_u_1:owns_title_id(p_u_12, p14) ~= true then
            v_u_13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, p14))
        end;
    end;
    if v_u_8:can_playerblob_increase_level(p_u_12) ~= true and v_u_1:owns_title_id(p_u_12, 76) ~= true then
        v_u_13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 76))
    end;
    if p_u_12.LSLvl >= 1 and v_u_1:owns_title_id(p_u_12, 113) ~= true then
        v_u_13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 113))
    end;
    if p_u_12.LSLvl >= 5 and v_u_1:owns_title_id(p_u_12, 114) ~= true then
        v_u_13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 114))
    end;
    if p_u_12.LSLvl >= 10 and v_u_1:owns_title_id(p_u_12, 115) ~= true then
        v_u_13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 115))
    end;
    if p_u_12.LSLvl >= 10 and (v_u_8:can_playerblob_increase_level(p_u_12) ~= true and v_u_1:owns_title_id(p_u_12, 116) ~= true) then
        v_u_13:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 116))
    end;
    return v_u_13;
end;
return v_u_8;
