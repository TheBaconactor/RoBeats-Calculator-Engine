-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
local v3 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v4 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v5 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v6 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
local v15 = {
    ["playerblob_can_claim_login_reward_for_dayid_monthid"] = function(_, p7, p8, p9) --[[ Name: playerblob_can_claim_login_reward_for_dayid_monthid ]] --[[ Line: 11 ]]
        return p7.LoginDayID ~= p8 and true or p7.LoginMonthID ~= p9;
    end,
    ["playerblob_mark_as_claimed_for_dayid_monthid"] = function(_, p10, p11, p12) --[[ Name: playerblob_mark_as_claimed_for_dayid_monthid ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        v_u_1:is_int(p11)
        v_u_1:is_int(p12)
        if p10.LoginMonthID == p12 then
            p10.LoginDayCount = p10.LoginDayCount + 1
        else
            p10.LoginDayCount = 1
        end;
        p10.LoginDayID = p11
        p10.LoginMonthID = p12
    end,
    ["get_reward_day_count_for_playerblob_dayid_monthid"] = function(_, p13, _, p14) --[[ Name: get_reward_day_count_for_playerblob_dayid_monthid ]] --[[ Line: 301 ]]
        return (p13.LoginMonthID ~= p14 and 0 or p13.LoginDayCount) + 1;
    end
}
local function f_validate_day_reward_list(p16) --[[ Name: validate_day_reward_list ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    for v17 = 1, p16:count() do
        v_u_1:is_non_nil(p16:get(v17))
        v_u_1:is_true(p16:get(v17):count() >= 1)
    end;
end;
local v_u_18 = v2:new():push_back_table_list({
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomSmallNote, 3, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomMediumNote, 2, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomLargeNote, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomSmallNote, 3, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomMediumNote, 2, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomLargeNote, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_protect_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomSmallNote, 3, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomMediumNote, 2, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomLargeNote, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1), v3.RewardInfo:new(v3.RewardType.RandomGem, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomSmallNote, 3, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomMediumNote, 2, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomLargeNote, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_protect_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1), v3.RewardInfo:new(v3.RewardType.RandomGem, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomSmallNote, 3, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomMediumNote, 2, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomLargeNote, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_protect_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1), v3.RewardInfo:new(v3.RewardType.RandomGem, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomSmallNote, 6, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomMediumNote, 4, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomLargeNote, 2, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.RandomGem, 2, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) })
})
f_validate_day_reward_list(v_u_18)
local v_u_19 = v2:new():push_back_table_list({
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 50, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_small_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_medium_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 75, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_large_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_gem_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_protect_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Stars, 1, -1) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_mini_1star_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 150, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_small_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 150, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_medium_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.Coins, 150, -1), v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_large_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_gem_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_protect_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_mini_1star_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 2, v4:get_small_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 2, v4:get_medium_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 2, v4:get_large_note_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_mini_1star_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_protect_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v6:get_leaderboard_ticket_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_gem_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_protect_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_mini_1star_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v4:get_gem_box_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) }),
    v2:new():push_back_table_list({ v3.RewardInfo:new(v3.RewardType.CraftingMaterials, 1, v5:singleton():get_upgrade_boost_untradeable_material_id()) })
})
f_validate_day_reward_list(v_u_19)
local v_u_20 = v2:new()
v15.get_reward_for_day_count = function(_, p21, p22) --[[ Name: get_reward_for_day_count ]] --[[ Line: 310 ]]
    --[[ Upvalues: (copy 1): v_u_20, (copy 2): v_u_19, (copy 3): v_u_18 ]]
    if p21 <= 0 then
        return v_u_20;
    else
        local v23 = v_u_19
        if p22 >= 53 then
            v23 = v_u_18
        end;
        if v23 == nil then
            return v_u_20;
        elseif v23:get(p21) == nil then
            return v23:get(v23:count());
        else
            return v23:get(p21);
        end;
    end;
end;
local v_u_24 = true
v15.get_notification_state = function(_) --[[ Name: get_notification_state ]] --[[ Line: 326 ]]
    --[[ Upvalues: (ref 1): v_u_24 ]]
    return v_u_24;
end;
v15.set_notification_state = function(_, p25) --[[ Name: set_notification_state ]] --[[ Line: 327 ]]
    --[[ Upvalues: (ref 1): v_u_24 ]]
    v_u_24 = p25
end;
return v15;
