-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.GuildData)
require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.Bit)
local v_u_7 = {
    ["MoreEventPoints"] = 1,
    ["MorePetEXP"] = 2,
    ["DoubleRouletteRewards"] = 3,
    ["FreeMarketplaceSales"] = 4
}
local v_u_9 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v8 = {
            ["get_bonus_id"] = function(_) --[[ Name: get_bonus_id ]] --[[ Line: 22 ]]
                return -1;
            end,
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 23 ]]
                return "";
            end,
            ["get_bonus_description"] = function(_) --[[ Name: get_bonus_description ]] --[[ Line: 24 ]]
                return "";
            end,
            ["get_bonus_base_price"] = function(_) --[[ Name: get_bonus_base_price ]] --[[ Line: 26 ]]
                return 5;
            end,
            ["get_bonus_price_per_member"] = function(_) --[[ Name: get_bonus_price_per_member ]] --[[ Line: 27 ]]
                return 1;
            end
        }
        v8.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            return v_u_4:important_assetid();
        end;
        return v8;
    end
}
local v_u_10 = v_u_2:new()
local function _(p11) --[[ Name: add_bonus_info ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_10 ]]
    v_u_3:is_false(v_u_10:contains(p11:get_bonus_id()))
    v_u_10:add(p11:get_bonus_id(), p11)
end;
local v13 = (function() --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_7 ]]
    local v12 = v_u_9:new()
    v12.get_bonus_id = function(_) --[[ Name: get_bonus_id ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return v_u_7.MoreEventPoints;
    end;
    v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 40 ]]
        return "More Event Points per Play (x1.25)";
    end;
    v12.get_bonus_base_price = function(_) --[[ Name: get_bonus_base_price ]] --[[ Line: 41 ]]
        return 20;
    end;
    v12.get_bonus_price_per_member = function(_) --[[ Name: get_bonus_price_per_member ]] --[[ Line: 42 ]]
        return 2;
    end;
    return v12;
end)()
v_u_3:is_false(v_u_10:contains(v13:get_bonus_id()))
v_u_10:add(v13:get_bonus_id(), v13)
local v15 = (function() --[[ Line: 45 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_7 ]]
    local v14 = v_u_9:new()
    v14.get_bonus_id = function(_) --[[ Name: get_bonus_id ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return v_u_7.MorePetEXP;
    end;
    v14.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 48 ]]
        return "More Mini EXP per Play (x2)";
    end;
    v14.get_bonus_base_price = function(_) --[[ Name: get_bonus_base_price ]] --[[ Line: 49 ]]
        return 10;
    end;
    v14.get_bonus_price_per_member = function(_) --[[ Name: get_bonus_price_per_member ]] --[[ Line: 50 ]]
        return 1;
    end;
    return v14;
end)()
v_u_3:is_false(v_u_10:contains(v15:get_bonus_id()))
v_u_10:add(v15:get_bonus_id(), v15)
local v17 = (function() --[[ Line: 53 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_7 ]]
    local v16 = v_u_9:new()
    v16.get_bonus_id = function(_) --[[ Name: get_bonus_id ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return v_u_7.DoubleRouletteRewards;
    end;
    v16.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 56 ]]
        return "Double Match Roulette Rewards";
    end;
    v16.get_bonus_base_price = function(_) --[[ Name: get_bonus_base_price ]] --[[ Line: 57 ]]
        return 15;
    end;
    v16.get_bonus_price_per_member = function(_) --[[ Name: get_bonus_price_per_member ]] --[[ Line: 58 ]]
        return 2;
    end;
    return v16;
end)()
v_u_3:is_false(v_u_10:contains(v17:get_bonus_id()))
v_u_10:add(v17:get_bonus_id(), v17)
local v19 = (function() --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_7 ]]
    local v18 = v_u_9:new()
    v18.get_bonus_id = function(_) --[[ Name: get_bonus_id ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return v_u_7.FreeMarketplaceSales;
    end;
    v18.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 64 ]]
        return "Free Marketplace Sales";
    end;
    v18.get_bonus_base_price = function(_) --[[ Name: get_bonus_base_price ]] --[[ Line: 65 ]]
        return 10;
    end;
    v18.get_bonus_price_per_member = function(_) --[[ Name: get_bonus_price_per_member ]] --[[ Line: 66 ]]
        return 1;
    end;
    return v18;
end)()
v_u_3:is_false(v_u_10:contains(v19:get_bonus_id()))
v_u_10:add(v19:get_bonus_id(), v19)
local v_u_20 = {
    ["BonusType"] = {
        ["MoreEventPoints"] = 1,
        ["MorePetEXP"] = 2,
        ["DoubleRouletteRewards"] = 3,
        ["FreeMarketplaceSales"] = 4
    }
}
for _, v21 in pairs(v_u_7) do
    v_u_3:is_true(v_u_10:contains(v21))
end;
v_u_20.get_bonus_info_for_id = function(_, p22) --[[ Name: get_bonus_info_for_id ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    return v_u_10:get(p22);
end;
v_u_20.get_bonus_info_list = function(_) --[[ Name: get_bonus_info_list ]] --[[ Line: 78 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_7, (copy 3): v_u_10 ]]
    local v23 = v_u_1:new()
    for _, v24 in pairs(v_u_7) do
        v23:push_back(v_u_10:get(v24))
    end;
    v23:sort(function(p25, p26) --[[ Line: 83 ]]
        return p26:get_bonus_id() - p25:get_bonus_id();
    end)
    return v23;
end;
check_flag_bonus_id_claimed = function(p27, p28) --[[ Name: check_flag_bonus_id_claimed ]] --[[ Line: 89 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6.And(p27, v_u_6.LShift(1, p28 - 1)) ~= 0;
end;
get_flag_active_bonus_ids_set = function(p29) --[[ Name: get_flag_active_bonus_ids_set ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_20 ]]
    local v30 = v_u_2:new()
    for _, v31 in v_u_20:get_bonus_info_list():key_itr() do
        if check_flag_bonus_id_claimed(p29, v31:get_bonus_id()) then
            v30:add_set(v31:get_bonus_id())
        end;
    end;
    return v30;
end;
v_u_20.guild_data_get_bonus_id_price = function(_, p32, p33) --[[ Name: guild_data_get_bonus_id_price ]] --[[ Line: 103 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_5 ]]
    local v34 = v_u_10:get(p33)
    return v34:get_bonus_base_price() + v34:get_bonus_price_per_member() * math.max(v_u_5:get_member_count_with_join_date_older_than_current_week(p32) - 1, 0);
end;
v_u_20.guild_data_get_updated_flag_with_bonus_id_claimed_for_weekid = function(_, p35, p36, p37) --[[ Name: guild_data_get_updated_flag_with_bonus_id_claimed_for_weekid ]] --[[ Line: 109 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7, (copy 3): v_u_6 ]]
    v_u_3:is_enum_member(p36, v_u_7)
    v_u_3:is_int(p37)
    return v_u_6.Or(p35:get_bonus_weekid() ~= p37 and 0 or p35:get_bonus_flag(), v_u_6.LShift(1, p36 - 1));
end;
local function _(p38, p39) --[[ Name: unverified_guild_data_is_bonus_id_active ]] --[[ Line: 119 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7 ]]
    v_u_3:is_enum_member(p39, v_u_7)
    return check_flag_bonus_id_claimed(p38:get_bonus_flag(), p39);
end;
v_u_20.guild_data_get_active_bonus_ids_set_for_weekid = function(_, p40, p41) --[[ Name: guild_data_get_active_bonus_ids_set_for_weekid ]] --[[ Line: 124 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2 ]]
    v_u_3:is_int(p41)
    if p40:get_bonus_weekid() == p41 then
        return get_flag_active_bonus_ids_set(p40:get_bonus_flag());
    else
        return v_u_2:new();
    end;
end;
v_u_20.guild_data_can_activate_bonus_id_for_weekid = function(_, p42, p43, p44) --[[ Name: guild_data_can_activate_bonus_id_for_weekid ]] --[[ Line: 130 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7 ]]
    v_u_3:is_int(p44)
    if p42:get_bonus_weekid() ~= p44 then
        return true;
    end;
    v_u_3:is_enum_member(p43, v_u_7)
    return check_flag_bonus_id_claimed(p42:get_bonus_flag(), p43) ~= true;
end;
local function _(p45, p46) --[[ Name: unverified_playerblob_is_bonus_id_claimed ]] --[[ Line: 136 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7 ]]
    v_u_3:is_enum_member(p46, v_u_7)
    return check_flag_bonus_id_claimed(p45.TeamBonusClaimed, p46);
end;
v_u_20.playerblob_get_active_bonus_ids_set_for_weekid = function(_, p47, p48) --[[ Name: playerblob_get_active_bonus_ids_set_for_weekid ]] --[[ Line: 141 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2 ]]
    v_u_3:is_int(p48)
    if p47.TeamBonusWeekID == p48 then
        return get_flag_active_bonus_ids_set(p47.TeamBonusClaimed);
    else
        return v_u_2:new();
    end;
end;
v_u_20.playerblob_is_bonus_id_active_for_weekid = function(_, p49, p50, p51) --[[ Name: playerblob_is_bonus_id_active_for_weekid ]] --[[ Line: 147 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7 ]]
    v_u_3:is_int(p51)
    local v52
    if p49.TeamBonusWeekID == p51 then
        v_u_3:is_enum_member(p50, v_u_7)
        v52 = check_flag_bonus_id_claimed(p49.TeamBonusClaimed, p50)
    else
        v52 = false
    end;
    return v52;
end;
v_u_20.playerblob_guild_data_can_claim_any_bonus_for_weekid = function(_, p53, p54, p55) --[[ Name: playerblob_guild_data_can_claim_any_bonus_for_weekid ]] --[[ Line: 152 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_20, (copy 3): v_u_5 ]]
    v_u_3:is_int(p55)
    if p54:get_bonus_weekid() == p55 and v_u_20:guild_data_get_active_bonus_ids_set_for_weekid(p54, p55):count() > 0 then
        if v_u_5:get_player_info(p54, p53.UserId):get_joined_week() >= p54:get_bonus_weekid() then
            return false, 0, "Must be in team for at least one week in order to claim the bonus";
        elseif p53.TeamBonusWeekID == p54:get_bonus_weekid() then
            if p53.TeamBonusClaimed == p54:get_bonus_flag() then
                return false, 0, "Already claimed bonus";
            else
                return true, 1, "";
            end;
        else
            return true, 1, "";
        end;
    else
        return false, 0, "No bonus active";
    end;
end;
return v_u_20;
