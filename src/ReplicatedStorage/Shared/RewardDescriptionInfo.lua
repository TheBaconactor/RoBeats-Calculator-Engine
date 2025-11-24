-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_3 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_8 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_9 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_12 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_13 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_15 = require(game.ReplicatedStorage.Crafting.CraftingRewardCategories)
local v_u_16 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_18 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v20 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
v20:require_shared(function() --[[ Line: 29 ]]
    --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22, (ref 3): v_u_23, (ref 4): v_u_24, (ref 5): v_u_25 ]]
    v_u_21 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
    v_u_22 = require(game.ReplicatedStorage.Shared.GuildUtil)
    v_u_23 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Data)
    v_u_24 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
    v_u_25 = require(game.ReplicatedStorage.PlayerInfo.MissionMPRewardFlag)
end)
local v_u_32 = {
    ["RewardType"] = {
        ["None"] = -1,
        ["Coins"] = 0,
        ["Stars"] = 1,
        ["CraftingMaterials"] = 2,
        ["Titles"] = 3,
        ["Pet"] = 4,
        ["Gear"] = 5,
        ["Song"] = 6,
        ["EventPoints"] = 7,
        ["Dance"] = 8,
        ["RandomToken"] = 9,
        ["TeamContributionPoints"] = 10,
        ["TeamContributionPointsFromDailySongMission"] = 11,
        ["VIP"] = 12,
        ["ChallengePassSeasonUnlock"] = 13,
        ["ChallengePassComplete"] = 14,
        ["EventPointPurchaseRewards"] = 15,
        ["RandomLegendaryBlueprint"] = 16,
        ["RandomRareBlueprint"] = 17,
        ["RandomSmallNote"] = 18,
        ["RandomMediumNote"] = 19,
        ["RandomLargeNote"] = 20,
        ["RandomGem"] = 21,
        ["ChallengePassV2VIPTierUnlock"] = 22,
        ["ChallengePassV2Points"] = 23,
        ["MissionMPReward"] = 24
    },
    ["RewardInfo"] = {},
    ["generate_only_items_description_from_rewardinfo_list"] = function(_, p26) --[[ Name: generate_only_items_description_from_rewardinfo_list ]] --[[ Line: 460 ]]
        local v27 = ""
        for v28, v29 in p26:key_itr() do
            v27 = v27 .. v29:get_name_with_amount()
            if v28 < p26:count() then
                v27 = v27 .. ", "
            end;
        end;
        return #v27 == 0 and "None" or v27;
    end,
    ["reward_params_get_resolved_reward_list"] = function(_, p30) --[[ Name: reward_params_get_resolved_reward_list ]] --[[ Line: 478 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        local v31 = p30 == nil and {} or p30
        if v31.ResolvedRewardList == nil then
            v31.ResolvedRewardList = v_u_5:new()
        end;
        return v31.ResolvedRewardList;
    end
}
v_u_32.RewardType.is_type_team_contribution_points = function(_, p33) --[[ Name: is_type_team_contribution_points ]] --[[ Line: 68 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    return p33 == v_u_32.RewardType.TeamContributionPoints and true or p33 == v_u_32.RewardType.TeamContributionPointsFromDailySongMission;
end;
v_u_32.RewardType.is_type_random = function(_, p34) --[[ Name: is_type_random ]] --[[ Line: 73 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    return (p34 == v_u_32.RewardType.RandomToken or (p34 == v_u_32.RewardType.RandomLegendaryBlueprint or (p34 == v_u_32.RewardType.RandomRareBlueprint or (p34 == v_u_32.RewardType.RandomSmallNote or (p34 == v_u_32.RewardType.RandomMediumNote or p34 == v_u_32.RewardType.RandomLargeNote))))) and true or p34 == v_u_32.RewardType.RandomGem;
end;
v_u_32.RewardInfo.new = function(_, p_u_35, p_u_36, p_u_37) --[[ Name: new ]] --[[ Line: 84 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_32, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_7, (copy 6): v_u_9, (copy 7): v_u_12, (copy 8): v_u_14, (ref 9): v_u_25, (copy 10): v_u_16, (copy 11): v_u_2, (ref 12): v_u_23, (copy 13): v_u_3, (ref 14): v_u_21, (ref 15): v_u_24, (copy 16): v_u_13, (copy 17): v_u_10 ]]
    local function f_validate_params() --[[ Name: validate_params ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_35, (ref 3): v_u_32, (ref 4): p_u_36, (ref 5): v_u_1, (ref 6): p_u_37, (ref 7): v_u_4, (ref 8): v_u_7, (ref 9): v_u_9, (ref 10): v_u_12, (ref 11): v_u_14, (ref 12): v_u_25 ]]
        v_u_6:is_enum_member(p_u_35, v_u_32.RewardType)
        v_u_6:is_int_greater_than(p_u_36, 0)
        if p_u_35 == v_u_32.RewardType.CraftingMaterials then
            v_u_6:is_true(v_u_1:singleton():contains_material(p_u_37))
            return;
        elseif p_u_35 == v_u_32.RewardType.Titles then
            v_u_6:is_true(v_u_4:singleton():contains_title_for_id(p_u_37))
            return;
        elseif p_u_35 == v_u_32.RewardType.Pet then
            v_u_6:is_true(v_u_7:singleton():contains_petid(p_u_37))
            return;
        elseif p_u_35 == v_u_32.RewardType.Gear then
            v_u_6:is_true(v_u_9:singleton():get_equipment_for_id(p_u_37) ~= nil)
            return;
        elseif p_u_35 == v_u_32.RewardType.Song then
            v_u_6:is_true(v_u_12:singleton():contains_key(p_u_37))
            return;
        elseif p_u_35 == v_u_32.RewardType.EventPoints then
            v_u_6:is_int_greater_than(p_u_36, 0)
            return;
        elseif p_u_35 == v_u_32.RewardType.Dance then
            v_u_6:is_true(v_u_14:singleton():contains_dance_for_id(p_u_37))
            return;
        elseif v_u_32.RewardType:is_type_team_contribution_points(p_u_35) then
            v_u_6:is_int_greater_than(p_u_36, 0)
        elseif p_u_35 == v_u_32.RewardType.MissionMPReward then
            v_u_6:is_enum_member(p_u_37, v_u_25.Flag)
        end;
    end;
    f_validate_params()
    local v38 = {}
    v38.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): p_u_35 ]]
        return p_u_35;
    end;
    v38.set_type = function(_, p39) --[[ Name: set_type ]] --[[ Line: 113 ]]
        --[[ Upvalues: (ref 1): p_u_35, (copy 2): f_validate_params ]]
        p_u_35 = p39
        f_validate_params()
    end;
    v38.get_amount = function(_) --[[ Name: get_amount ]] --[[ Line: 114 ]]
        --[[ Upvalues: (ref 1): p_u_36 ]]
        return p_u_36;
    end;
    v38.set_amount = function(_, p40) --[[ Name: set_amount ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): p_u_36, (copy 2): f_validate_params ]]
        p_u_36 = p40
        f_validate_params()
    end;
    v38.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): p_u_37 ]]
        return p_u_37;
    end;
    v38.set_id = function(_, p41) --[[ Name: set_id ]] --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): p_u_37, (copy 2): f_validate_params ]]
        p_u_37 = p41
        f_validate_params()
    end;
    v38.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 119 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_32, (ref 3): v_u_1, (ref 4): p_u_37, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): v_u_9, (ref 8): v_u_12, (ref 9): v_u_14, (ref 10): v_u_25 ]]
        if p_u_35 == v_u_32.RewardType.Coins then
            return "Coin(s)";
        elseif p_u_35 == v_u_32.RewardType.Stars then
            return "Star(s)";
        elseif p_u_35 == v_u_32.RewardType.CraftingMaterials then
            return v_u_1:singleton():get_material_name(p_u_37);
        elseif p_u_35 == v_u_32.RewardType.Titles then
            return string.format("Title: %s", v_u_4:singleton():get_title_name_for_id(p_u_37));
        elseif p_u_35 == v_u_32.RewardType.Pet then
            return string.format("\"%s\" Mini", v_u_7:singleton():get_name_for_petid(p_u_37));
        elseif p_u_35 == v_u_32.RewardType.Gear then
            return string.format("\"%s\" Gear", v_u_9:singleton():get_equipment_for_id(p_u_37):get_name());
        elseif p_u_35 == v_u_32.RewardType.Song then
            return string.format("Song: \"%s\"", v_u_12:singleton():get_title_for_key(p_u_37));
        elseif p_u_35 == v_u_32.RewardType.EventPoints then
            return string.format("Event Points");
        elseif p_u_35 == v_u_32.RewardType.Dance then
            return string.format("Dance: %s", v_u_14:singleton():get_dance_name_for_id(p_u_37));
        elseif p_u_35 == v_u_32.RewardType.RandomToken then
            return string.format("Random Token(s)");
        elseif p_u_35 == v_u_32.RewardType.TeamContributionPoints then
            return string.format("Team Contribution Points");
        elseif p_u_35 == v_u_32.RewardType.TeamContributionPointsFromDailySongMission then
            return string.format("Team Contribution Points (Daily Song Mission)");
        elseif p_u_35 == v_u_32.RewardType.VIP then
            return string.format("RoBeats VIP Days");
        elseif p_u_35 == v_u_32.RewardType.ChallengePassSeasonUnlock then
            return string.format("Unlock Current VIP Challenge Pass");
        elseif p_u_35 == v_u_32.RewardType.ChallengePassComplete then
            return string.format("Complete Current Challenge Pass Tier");
        elseif p_u_35 == v_u_32.RewardType.ChallengePassV2VIPTierUnlock then
            return string.format("Unlock Challenge Pass VIP Tier");
        elseif p_u_35 == v_u_32.RewardType.ChallengePassV2Points then
            return string.format("Challenge Pass Points");
        elseif p_u_35 == v_u_32.RewardType.EventPointPurchaseRewards then
            return string.format("Event Point Purchase Rewards");
        elseif p_u_35 == v_u_32.RewardType.RandomLegendaryBlueprint then
            return string.format("Random Legendary Blueprint");
        elseif p_u_35 == v_u_32.RewardType.RandomRareBlueprint then
            return string.format("Random Rare Blueprint");
        else
            return p_u_35 == v_u_32.RewardType.RandomSmallNote and "Random Small Note(s)" or (p_u_35 == v_u_32.RewardType.RandomMediumNote and "Random Medium Note(s)" or (p_u_35 == v_u_32.RewardType.RandomLargeNote and "Random Large Note(s)" or (p_u_35 == v_u_32.RewardType.RandomGem and "Random Gem(s)" or (p_u_35 == v_u_32.RewardType.None and "None" or (p_u_35 ~= v_u_32.RewardType.MissionMPReward and "?" or string.format("Multiplayer Mission Reward %d (%s) - Once per day only.", p_u_37 + 1, v_u_32:generate_only_items_description_from_rewardinfo_list(v_u_25:flag_to_unclaimed_reward_desc_info_list(p_u_37))))))));
        end;
    end;
    v38.get_name_with_amount = function(p42) --[[ Name: get_name_with_amount ]] --[[ Line: 181 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return string.format("x%s %s", v_u_16:comma_value(p42:get_amount()), p42:get_name());
    end;
    v38.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 183 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): p_u_36, (ref 3): p_u_37 ]]
        return {
            ["Type"] = p_u_35,
            ["Amount"] = p_u_36,
            ["ID"] = p_u_37
        };
    end;
    v38.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_32, (ref 3): v_u_2, (ref 4): v_u_1, (ref 5): p_u_37, (ref 6): v_u_16, (ref 7): v_u_7, (ref 8): v_u_9, (ref 9): v_u_12, (ref 10): v_u_14, (ref 11): v_u_23 ]]
        if p_u_35 == v_u_32.RewardType.Coins then
            return v_u_2:currency_type_get_image(v_u_2.CurrencyType.Coins);
        elseif p_u_35 == v_u_32.RewardType.Stars then
            return v_u_2:currency_type_get_image(v_u_2.CurrencyType.Stars);
        elseif p_u_35 == v_u_32.RewardType.CraftingMaterials then
            return v_u_1:singleton():get_material_icon(p_u_37);
        elseif p_u_35 == v_u_32.RewardType.Titles then
            return v_u_16:important_assetid();
        elseif p_u_35 == v_u_32.RewardType.Pet then
            return v_u_7:singleton():get_data_for_petid(p_u_37):get_icon();
        elseif p_u_35 == v_u_32.RewardType.Gear then
            return v_u_9:singleton():get_equipment_for_id(p_u_37):get_icon();
        elseif p_u_35 == v_u_32.RewardType.Song then
            return v_u_12:singleton():get_coverimage_assetid_for_key(p_u_37);
        elseif p_u_35 == v_u_32.RewardType.EventPoints then
            return v_u_16:important_assetid();
        elseif p_u_35 == v_u_32.RewardType.Dance then
            return v_u_14:singleton():get_dance_icon_for_id(p_u_37);
        elseif p_u_35 == v_u_32.RewardType.RandomToken then
            return "rbxassetid://2642454531";
        elseif p_u_35 == v_u_32.RewardType.VIP then
            return "rbxassetid://5384697907";
        elseif p_u_35 == v_u_32.RewardType.None then
            return v_u_16:transparent_assetid();
        elseif p_u_35 == v_u_32.RewardType.RandomSmallNote then
            return "rbxassetid://16233898478";
        elseif p_u_35 == v_u_32.RewardType.RandomMediumNote then
            return "rbxassetid://16233898803";
        elseif p_u_35 == v_u_32.RewardType.RandomLargeNote then
            return "rbxassetid://16233899001";
        elseif p_u_35 == v_u_32.RewardType.RandomGem then
            return "rbxassetid://16233899119";
        elseif p_u_35 == v_u_32.RewardType.ChallengePassV2VIPTierUnlock or p_u_35 == v_u_32.RewardType.ChallengePassV2Points then
            return v_u_23:get_challengepassv2_square_icon_assetid();
        elseif p_u_35 == v_u_32.RewardType.MissionMPReward then
            return v_u_2:currency_type_get_image(v_u_2.CurrencyType.Stars);
        else
            return v_u_16:important_assetid();
        end;
    end;
    v38.get_description = function(_, p43) --[[ Name: get_description ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_32, (ref 3): v_u_1, (ref 4): p_u_37, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): v_u_12 ]]
        if p_u_35 == v_u_32.RewardType.Coins then
            return "Use coins to buy songs, gear, crafting materials and more!";
        elseif p_u_35 == v_u_32.RewardType.Stars then
            return "Use stars to buy rare gear, special crafting materials, and a whole lot more!";
        elseif p_u_35 == v_u_32.RewardType.CraftingMaterials then
            if p43 == true then
                return string.format("These item(s) have been added to your inventory. Description: %s", v_u_1:singleton():get_material_description(p_u_37));
            else
                return v_u_1:singleton():get_material_description(p_u_37);
            end;
        elseif p_u_35 == v_u_32.RewardType.Titles then
            return v_u_4:singleton():get_title_for_id(p_u_37):get_description();
        elseif p_u_35 == v_u_32.RewardType.Pet then
            if p43 == true then
                return string.format("This mini has been added to your roster. Description: %s", v_u_7:singleton():get_data_for_petid(p_u_37):get_description());
            else
                return v_u_7:singleton():get_data_for_petid(p_u_37):get_description();
            end;
        elseif p_u_35 == v_u_32.RewardType.Song then
            if p43 == true then
                return string.format("Artist: %s. Difficulty: %d. Description: %s", v_u_12:singleton():get_artist_for_key(p_u_37), v_u_12:singleton():get_difficulty_for_key(p_u_37), v_u_12:singleton():get_description_for_key(p_u_37));
            else
                return v_u_12:singleton():get_description_for_key(p_u_37);
            end;
        else
            return p_u_35 == v_u_32.RewardType.EventPoints and "Event Points can be used to purchase rewards for the duration of the current event." or ((p_u_35 == v_u_32.RewardType.TeamContributionPoints or p_u_35 == v_u_32.RewardType.TeamContributionPointsFromDailySongMission) and "Earn contribution points for your team by completing missions. More points for your team means a higher leaderboard placement!" or (p_u_35 == v_u_32.RewardType.ChallengePassSeasonUnlock and "You now have access to all tiers of the current challenge pass!" or (p_u_35 == v_u_32.RewardType.ChallengePassComplete and "You have automatically completed the current challenge pass tier!" or (p_u_35 == v_u_32.RewardType.ChallengePassV2VIPTierUnlock and "Unlocked the VIP tier of this month\'s Challenge Pass!" or (p_u_35 == v_u_32.RewardType.ChallengePassV2Points and "Earned points for this month\'s Challenge Pass!" or (p_u_35 == v_u_32.RewardType.RandomSmallNote and "A random small note of either Chill, Vibe, Flow, Rush or Beat element." or (p_u_35 == v_u_32.RewardType.RandomMediumNote and "A random medium note of either Chill, Vibe, Flow, Rush or Beat element." or (p_u_35 == v_u_32.RewardType.RandomLargeNote and "A random large note of either Chill, Vibe, Flow, Rush or Beat element." or (p_u_35 == v_u_32.RewardType.RandomGem and "A random Blue, Green, Purple, Red or Orange gem." or (p_u_35 == v_u_32.RewardType.MissionMPReward and "Rewards for completing a multiplayer mission." or ""))))))))));
        end;
    end;
    v38.get_display_text_color = function(_) --[[ Name: get_display_text_color ]] --[[ Line: 332 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_32, (ref 3): v_u_1, (ref 4): p_u_37, (ref 5): v_u_4 ]]
        if p_u_35 == v_u_32.RewardType.CraftingMaterials then
            return v_u_1:singleton():tier_get_color(v_u_1:singleton():get_material_tier(p_u_37)), false;
        elseif p_u_35 == v_u_32.RewardType.Titles then
            return v_u_4:singleton():get_title_for_id(p_u_37):get_color(), false;
        else
            return Color3.fromRGB(255, 255, 255), true;
        end;
    end;
    v38.playerblob_get_display_owned_count = function(_, p44) --[[ Name: playerblob_get_display_owned_count ]] --[[ Line: 345 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_32, (ref 3): v_u_2, (ref 4): v_u_3, (ref 5): p_u_37, (ref 6): v_u_21, (ref 7): v_u_24 ]]
        if p_u_35 == v_u_32.RewardType.Coins then
            return v_u_2:get_currency_type_amount(p44, v_u_2.CurrencyType.Coins);
        elseif p_u_35 == v_u_32.RewardType.Stars then
            return v_u_2:get_currency_type_amount(p44, v_u_2.CurrencyType.Stars);
        elseif p_u_35 == v_u_32.RewardType.CraftingMaterials then
            return v_u_3:get_count_of_material(p44, p_u_37);
        elseif p_u_35 == v_u_32.RewardType.Song then
            return v_u_2:get_song_key_owned_count(p44, p_u_37);
        elseif p_u_35 == v_u_32.RewardType.EventPoints then
            return v_u_21:playerblob_get_event_points(p44);
        else
            return p_u_35 == v_u_32.RewardType.TeamContributionPoints and -1 or (p_u_35 == v_u_32.RewardType.TeamContributionPointsFromDailySongMission and -1 or (p_u_35 == v_u_32.RewardType.VIP and -1 or (p_u_35 == v_u_32.RewardType.ChallengePassSeasonUnlock and -1 or (p_u_35 == v_u_32.RewardType.ChallengePassComplete and -1 or (p_u_35 == v_u_32.RewardType.ChallengePassV2VIPTierUnlock and -1 or (p_u_35 ~= v_u_32.RewardType.ChallengePassV2Points and (v_u_32.RewardType:is_type_random(p_u_35) and -1 or 1) or v_u_24:playerblob_get_points_total(p44)))))));
        end;
    end;
    v38.can_playerblob_add = function(_, p45) --[[ Name: can_playerblob_add ]] --[[ Line: 391 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_32, (ref 3): v_u_13, (ref 4): p_u_37, (ref 5): v_u_2, (ref 6): v_u_10 ]]
        if p_u_35 == v_u_32.RewardType.Dance then
            return v_u_13:get_owned_danceid_to_equipped_dict(p45):contains(p_u_37) ~= true;
        elseif p_u_35 == v_u_32.RewardType.Titles then
            return v_u_2:owns_title_id(p45, p_u_37) ~= true;
        else
            return p_u_35 ~= v_u_32.RewardType.Gear and true or v_u_10:playerblob_can_add_more_gear(p45) == true;
        end;
    end;
    v38.can_add_multiple = function(_) --[[ Name: can_add_multiple ]] --[[ Line: 406 ]]
        --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_32 ]]
        if p_u_35 == v_u_32.RewardType.Dance then
            return false;
        elseif p_u_35 == v_u_32.RewardType.Gear then
            return false;
        else
            return p_u_35 ~= v_u_32.RewardType.Titles;
        end;
    end;
    return v38;
end;
v_u_32.RewardInfo.from_table = function(_, p46) --[[ Name: from_table ]] --[[ Line: 422 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    return v_u_32.RewardInfo:new(p46.Type, p46.Amount, p46.ID);
end;
v_u_32.RewardInfo.copy = function(_, p47) --[[ Name: copy ]] --[[ Line: 426 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    return v_u_32.RewardInfo:from_table(p47:to_table());
end;
v_u_32.RewardInfo.add_rewards_list_from_table = function(_, p48, p49) --[[ Name: add_rewards_list_from_table ]] --[[ Line: 430 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    for _, v50 in pairs(p49) do
        p48:push_back(v_u_32.RewardInfo:new(v50.Type, v50.Amount, v50.Id))
    end;
    return p48;
end;
v_u_32.RewardInfo.list_to_table = function(_, p51) --[[ Name: list_to_table ]] --[[ Line: 437 ]]
    --[[ Upvalues: (copy 1): v_u_5 ]]
    local v52 = v_u_5:new()
    for _, v53 in p51:key_itr() do
        v52:push_back(v53:to_table())
    end;
    return v52:get_table();
end;
v_u_32.RewardInfo.table_to_list = function(_, p54) --[[ Name: table_to_list ]] --[[ Line: 445 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_32 ]]
    local v55 = v_u_5:new()
    if p54 == nil or typeof(p54) ~= "table" then
        return v55;
    end;
    for v56 = 1, #p54 do
        v55:push_back(v_u_32.RewardInfo:from_table(p54[v56]))
    end;
    return v55;
end;
v_u_32.list_copy = function(_, p57) --[[ Name: list_copy ]] --[[ Line: 456 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    return v_u_32.RewardInfo:table_to_list(v_u_32.RewardInfo:list_to_table(p57));
end;
v_u_32.generate_description_from_rewardinfo_list = function(_, p58) --[[ Name: generate_description_from_rewardinfo_list ]] --[[ Line: 474 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    return "You got: " .. v_u_32:generate_only_items_description_from_rewardinfo_list(p58) .. ".";
end;
v_u_32.claim_reward_info_to_playerblob = function(_, p59, p_u_60, p61, p62) --[[ Name: claim_reward_info_to_playerblob ]] --[[ Line: 484 ]]
    --[[ Upvalues: (copy 1): v_u_32, (copy 2): v_u_18, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_1, (copy 6): v_u_2, (copy 7): v_u_3, (copy 8): v_u_4, (copy 9): v_u_8, (copy 10): v_u_10, (ref 11): v_u_21, (copy 12): v_u_13, (ref 13): v_u_22, (copy 14): v_u_17, (copy 15): v_u_19, (ref 16): v_u_24, (copy 17): v_u_11, (copy 18): v_u_15, (ref 19): v_u_25 ]]
    local v_u_63 = p62 == nil and {} or p62
    local v_u_64 = v_u_32:reward_params_get_resolved_reward_list(v_u_63)
    local function _(p65) --[[ Name: append_to_resolved_reward_list ]] --[[ Line: 488 ]]
        --[[ Upvalues: (copy 1): v_u_64 ]]
        v_u_64:push_back(p65)
    end;
    local function _() --[[ Name: set_params_failed ]] --[[ Line: 492 ]]
        --[[ Upvalues: (ref 1): v_u_63 ]]
        v_u_63.Failed = true
    end;
    local function _() --[[ Name: set_params_push_player_info_updated ]] --[[ Line: 496 ]]
        --[[ Upvalues: (ref 1): v_u_63 ]]
        v_u_63.PushPlayerInfoUpdated = true
    end;
    local function _() --[[ Name: set_params_update_equipped_data ]] --[[ Line: 500 ]]
        --[[ Upvalues: (ref 1): v_u_63 ]]
        v_u_63.UpdateEquippedData = true
    end;
    local function _(p66) --[[ Name: append_params_message ]] --[[ Line: 504 ]]
        --[[ Upvalues: (ref 1): v_u_63 ]]
        if v_u_63.Message == nil then
            v_u_63.Message = p66
        else
            v_u_63.Message = v_u_63.Message .. " " .. p66
        end;
    end;
    local function _(p67) --[[ Name: append_params_fn_post_sync ]] --[[ Line: 512 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_5, (ref 3): v_u_63, (copy 4): p_u_60 ]]
        if v_u_18.RewardDescriptionInfoDoFnPostSync == true then
            local v68 = v_u_5:new(v_u_63.FnPostSync)
            v68:push_back(p67)
            v_u_63.FnPostSync = v68:get_table()
        else
            p67(p_u_60)
        end;
    end;
    local function f_append_crafting_material_rewards(p69) --[[ Name: append_crafting_material_rewards ]] --[[ Line: 522 ]]
        --[[ Upvalues: (ref 1): v_u_63, (ref 2): v_u_6, (ref 3): v_u_1, (ref 4): v_u_5 ]]
        if v_u_63.CraftingMaterialRewards == nil then
            v_u_63.CraftingMaterialRewards = {}
        end;
        v_u_6:is_true(v_u_1:singleton():contains_material(p69))
        v_u_5:new(v_u_63.CraftingMaterialRewards):push_back(p69)
    end;
    local function _(p70) --[[ Name: append_fn_request_extra ]] --[[ Line: 528 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_63 ]]
        local v71 = v_u_5:new(v_u_63.FnAddRequestExtra)
        v71:push_back(p70)
        v_u_63.FnAddRequestExtra = v71:get_table()
    end;
    local v72 = p61:get_type()
    local v_u_73 = p61:get_amount()
    local v_u_74 = p61:get_id()
    local v75 = true
    if v72 == v_u_32.RewardType.Coins then
        v_u_2:set_coin_currency(p_u_60, v_u_2:get_coin_currency(p_u_60) + v_u_73)
    elseif v72 == v_u_32.RewardType.Stars then
        v_u_2:set_star_currency(p_u_60, v_u_2:get_star_currency(p_u_60) + v_u_73)
    elseif v72 == v_u_32.RewardType.CraftingMaterials then
        if v_u_1:singleton():contains_material(v_u_74) then
            v_u_3:add_crafting_materials_of_id(p_u_60, v_u_74, v_u_73)
            local v76 = v_u_63
            for _ = 1, v_u_73 do
                f_append_crafting_material_rewards(v_u_74)
            end;
            local v77 = v_u_1:singleton():get_material(v_u_74)
            if v77 and v77:is_fever_icon() then
                p_u_60.FeverIcon = v77:get_fever_icon_id()
                v76.PushPlayerInfoUpdated = true
            end;
        end;
    elseif v72 == v_u_32.RewardType.Titles then
        if v_u_4:singleton():contains_title_for_id(v_u_74) then
            if v_u_2:add_title(p_u_60, v_u_74) == true then
                v_u_2:set_title_id(p_u_60, v_u_74)
                v_u_63.PushPlayerInfoUpdated = true
            end;
        else
            v_u_63.Failed = true
            if v_u_63.Message == nil then
                v_u_63.Message = "Failed: Title not found."
            else
                v_u_63.Message = v_u_63.Message .. " Failed: Title not found."
            end;
        end;
    elseif v72 == v_u_32.RewardType.Pet then
        local v78, v79, v_u_80, v81 = v_u_8:playerblob_add_pet_or_material_of_petid(p_u_60, v_u_74, false)
        if v79 and v_u_8:playerblob_any_slot_free(p_u_60) then
            local function v83(p82) --[[ Line: 572 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_80 ]]
                v_u_8:playerblob_equip_pet_ownedid(p82, v_u_80)
            end;
            if v_u_18.RewardDescriptionInfoDoFnPostSync == true then
                local v84 = v_u_5:new(v_u_63.FnPostSync)
                v84:push_back(v83)
                v_u_63.FnPostSync = v84:get_table()
            else
                v83(p_u_60)
            end;
            v_u_63.UpdateEquippedData = true
        end;
        if v81 ~= nil then
            f_append_crafting_material_rewards(v81)
            v_u_64:push_back((v_u_32.RewardInfo:new(v_u_32.RewardType.CraftingMaterials, 1, v81)))
            v75 = false
        end;
        if v_u_63.Message == nil then
            v_u_63.Message = v78
        else
            v_u_63.Message = v_u_63.Message .. " " .. v78
        end;
    elseif v72 == v_u_32.RewardType.Gear then
        if v_u_10:playerblob_can_add_more_gear(p_u_60) then
            local v_u_85 = v_u_10:playerblob_grant_equipmentid(p_u_60, v_u_74)
            local function v87(p86) --[[ Line: 590 ]]
                --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_85 ]]
                if v_u_10:playerblob_ownedid_to_equipmentid(p86, v_u_85) ~= nil then
                    v_u_10:playerblob_equip_ownedid(p86, v_u_85)
                end;
            end;
            if v_u_18.RewardDescriptionInfoDoFnPostSync == true then
                local v88 = v_u_5:new(v_u_63.FnPostSync)
                v88:push_back(v87)
                v_u_63.FnPostSync = v88:get_table()
            else
                v87(p_u_60)
            end;
            v_u_63.UpdateEquippedData = true
        else
            v_u_63.Failed = true
            if v_u_63.Message == nil then
                v_u_63.Message = "Failed: You own the max number of gear."
            else
                v_u_63.Message = v_u_63.Message .. " Failed: You own the max number of gear."
            end;
        end;
    elseif v72 == v_u_32.RewardType.Song then
        for _ = 1, v_u_73 do
            v_u_2:add_song(p_u_60, v_u_74)
        end;
    elseif v72 == v_u_32.RewardType.EventPoints then
        v_u_21:playerblob_set_event_points(p_u_60, v_u_21:playerblob_get_event_points(p_u_60) + v_u_73)
    elseif v72 == v_u_32.RewardType.Dance then
        if v_u_13:get_owned_danceid_to_equipped_dict(p_u_60):contains(v_u_74) ~= true then
            v_u_13:add_owned_danceid(p_u_60, v_u_74)
            v_u_13:validate_playerblob(p_u_60)
        end;
        local function v90(p89) --[[ Line: 615 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_74 ]]
            v_u_13:set_danceid_equipped(p89, v_u_74, true)
            v_u_13:validate_playerblob(p89)
        end;
        if v_u_18.RewardDescriptionInfoDoFnPostSync == true then
            local v91 = v_u_5:new(v_u_63.FnPostSync)
            v91:push_back(v90)
            v_u_63.FnPostSync = v91:get_table()
        else
            v90(p_u_60)
        end;
    elseif v_u_32.RewardType:is_type_team_contribution_points(v72) then
        local v92, v_u_93 = p59._guild_manager:is_player_in_guild(v_u_2:get_user_id(p_u_60))
        if v92 then
            if v72 == v_u_32.RewardType.TeamContributionPoints then
                local v94 = v_u_5:new(v_u_63.FnAddRequestExtra)
                v94:push_back(function(p95) --[[ Line: 624 ]]
                    --[[ Upvalues: (copy 1): v_u_93, (ref 2): v_u_73 ]]
                    p95:set_guild_contribution(v_u_93, v_u_73)
                end)
                v_u_63.FnAddRequestExtra = v94:get_table()
            elseif v72 == v_u_32.RewardType.TeamContributionPointsFromDailySongMission then
                local v96 = p59._api:get_day_id()
                local v97 = v_u_22:playerblob_get_current_day_team_contribution_point_amount_from_daily_song_missions(p_u_60, v96)
                if v97 + v_u_73 > v_u_22:get_max_team_contribution_point_cap_from_daily_song_missions() then
                    v_u_22:playerblob_set_current_day_team_contribution_point_amount_from_daily_song_missions(p_u_60, v_u_22:get_max_team_contribution_point_cap_from_daily_song_missions(), v96)
                    v_u_73 = v_u_22:get_max_team_contribution_point_cap_from_daily_song_missions() - v97
                    local v98 = string.format("You have earned the maximum amount of team contribution points from song missions for today.")
                    if v_u_63.Message == nil then
                        v_u_63.Message = v98
                    else
                        v_u_63.Message = v_u_63.Message .. " " .. v98
                    end;
                else
                    v_u_22:playerblob_set_current_day_team_contribution_point_amount_from_daily_song_missions(p_u_60, v97 + v_u_73, v96)
                end;
                if v_u_73 > 0 then
                    local v99 = v_u_5:new(v_u_63.FnAddRequestExtra)
                    v99:push_back(function(p100) --[[ Line: 649 ]]
                        --[[ Upvalues: (copy 1): v_u_93, (ref 2): v_u_73 ]]
                        p100:set_guild_contribution(v_u_93, v_u_73)
                    end)
                    v_u_63.FnAddRequestExtra = v99:get_table()
                end;
            end;
        else
            v75 = false
        end;
    elseif v72 == v_u_32.RewardType.VIP then
        local v101 = math.max(v_u_17:playerblob_get_vip_day(p_u_60), p59._api:get_day_id())
        local v102 = v101 + v_u_73
        v_u_6:is_int(v101)
        v_u_6:is_int(v102)
        v_u_17:playerblob_set_vip_day(p_u_60, v102)
        if v_u_2:is_default_title_equipped(p_u_60) then
            v_u_17:playerblob_set_vip_title(p_u_60)
            v_u_63.PushPlayerInfoUpdated = true
        end;
    elseif v72 == v_u_32.RewardType.ChallengePassSeasonUnlock then
        v_u_19:validate_playerblob_to_current_month_id(p_u_60, p59._api:get_month_id())
        p_u_60.ChallengePassMonthActivated = true
    elseif v72 == v_u_32.RewardType.ChallengePassComplete then
        v_u_19:validate_playerblob_to_current_month_id(p_u_60, p59._api:get_month_id())
        local v103 = 0
        local v104 = v_u_19:playerblob_get_challengepass_active_mission(p_u_60, (p59._challengepass_manager:get_cached_challengepass_mission_list()))
        local v105
        if v104 == nil then
            v105 = v103
        else
            local v106 = v104:get_point_count()
            local l_ChallengePassPoints_0 = p_u_60.ChallengePassPoints
            if l_ChallengePassPoints_0 < v106 then
                v105 = v106 - l_ChallengePassPoints_0
                if v103 >= v105 then
                    v105 = v103
                end;
            else
                v105 = v103
            end;
        end;
        p_u_60.ChallengePassPoints = p_u_60.ChallengePassPoints + v105
    elseif v72 == v_u_32.RewardType.ChallengePassV2VIPTierUnlock then
        v_u_24:validate_playerblob_to_current_day_week_month_id(p_u_60, p59._api:get_day_id(), p59._api:get_week_id(), p59._api:get_month_id())
        p_u_60.CPV2MonthUpgradeToVIP = true
    elseif v72 == v_u_32.RewardType.ChallengePassV2Points then
        v_u_24:validate_playerblob_to_current_day_week_month_id(p_u_60, p59._api:get_day_id(), p59._api:get_week_id(), p59._api:get_month_id())
        p_u_60.CPV2Points = p_u_60.CPV2Points + v_u_73
    elseif v72 == v_u_32.RewardType.EventPointPurchaseRewards then
        v75 = false
        local v107, v108 = v_u_21:is_event_active(p59._api:get_day_event_list())
        if v107 then
            local v109 = v_u_21:get_event_info(v108)
            if v109:has_event_point_purchase_rewards() then
                v_u_21:playerblob_validate_event_info(p_u_60, v108)
                local v110 = v_u_63
                for _, v111 in v109:get_event_point_purchase_rewards():key_itr() do
                    if v111:get_type() == v_u_32.RewardType.EventPointPurchaseRewards then
                        v_u_11:warnf("RewardDescriptionInfo.RewardType.EventPointPurchaseRewards event_point_purchase_rewards nested")
                        break;
                    end;
                    for _ = 1, v_u_73 do
                        v_u_32:claim_reward_info_to_playerblob(p59, p_u_60, v111, v110)
                    end;
                end;
            end;
        end;
    elseif v_u_32.RewardType:is_type_random(v72) then
        v75 = false
        for _ = 1, v_u_73 do
            local v112 = v_u_1:invalid_material_id()
            if v72 == v_u_32.RewardType.RandomToken then
                v112 = v_u_15:get_crafting_token_material_ids():random()
            elseif v72 == v_u_32.RewardType.RandomLegendaryBlueprint then
                v112 = v_u_15:get_legendary_blueprint_material_ids():random()
            elseif v72 == v_u_32.RewardType.RandomRareBlueprint then
                v112 = v_u_15:get_rare_blueprint_material_ids():random()
            elseif v72 == v_u_32.RewardType.RandomSmallNote then
                v112 = v_u_15:get_small_note_material_ids():random()
            elseif v72 == v_u_32.RewardType.RandomMediumNote then
                v112 = v_u_15:get_medium_note_material_ids():random()
            elseif v72 == v_u_32.RewardType.RandomLargeNote then
                v112 = v_u_15:get_large_note_material_ids():random()
            elseif v72 == v_u_32.RewardType.RandomGem then
                v112 = v_u_15:get_gem_material_ids():random()
            else
                v_u_11:warnf("Unknown random reward type(%s)[%s]", tostring(v72), (typeof(v72)))
            end;
            if v_u_1:singleton():contains_material(v112) then
                v_u_3:add_crafting_materials_of_id(p_u_60, v112, 1)
                f_append_crafting_material_rewards(v112)
                v_u_64:push_back((v_u_32.RewardInfo:new(v_u_32.RewardType.CraftingMaterials, 1, v112)))
            end;
        end;
    elseif v72 == v_u_32.RewardType.MissionMPReward then
        v75 = false
        if v_u_6:test_enum_member(v_u_74, v_u_25.Flag) then
            local v113 = p59._api:get_day_id()
            v_u_5:new()
            local v114
            if v_u_25:playerblob_has_flag_set(p_u_60, v_u_74, v113) == true then
                v114 = v_u_25:flag_to_claimed_reward_desc_info_list(v_u_74)
            else
                v_u_25:playerblob_set_flag(p_u_60, v_u_74, v113)
                v114 = v_u_25:flag_to_unclaimed_reward_desc_info_list(v_u_74)
            end;
            local v115 = v_u_63
            for _, v116 in v114:key_itr() do
                v_u_32:claim_reward_info_to_playerblob(p59, p_u_60, v116, v115)
            end;
        end;
    else
        v_u_11:warnf("Unknown reward_type(%s)[%s]", tostring(v72), (typeof(v72)))
    end;
    if v75 == true then
        v_u_64:push_back((v_u_32.RewardInfo:from_table(p61:to_table())))
    end;
end;
v_u_32.claim_reward_info_list_to_playerblob = function(_, p117, p118, p119, p120) --[[ Name: claim_reward_info_list_to_playerblob ]] --[[ Line: 790 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    local v121 = p120 == nil and {} or p120
    v121.Message = v_u_32:generate_description_from_rewardinfo_list(p119)
    for _, v122 in p119:key_itr() do
        v_u_32:claim_reward_info_to_playerblob(p117, p118, v122, v121)
    end;
    return v121;
end;
v_u_32.server_sync_reward_params = function(_, p_u_123, p_u_124, p_u_125, p_u_126) --[[ Name: server_sync_reward_params ]] --[[ Line: 799 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_32 ]]
    p_u_123._player_blob_manager:enqueue_blob_sync_request(p_u_124.UserId, v_u_2.PlayerBlobRequestType.Write, function(p127) --[[ Line: 814 ]]
        --[[ Upvalues: (copy 1): p_u_125, (ref 2): v_u_32, (copy 3): p_u_126, (copy 4): p_u_123, (copy 5): p_u_124, (ref 6): v_u_2 ]]
        local v_u_128 = p_u_125.Message == nil and "" or p_u_125.Message
        local function f_on_finish(p129) --[[ Name: on_finish ]] --[[ Line: 820 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): p_u_125, (ref 3): p_u_126, (ref 4): v_u_128, (ref 5): p_u_123, (ref 6): p_u_124 ]]
            p_u_126(v_u_128, p_u_125, (v_u_32:reward_params_get_resolved_reward_list(p_u_125)))
            if p_u_125.PushPlayerInfoUpdated == true then
                p_u_123._lobby_manager:push_player_info_updated(p_u_124.UserId)
            end;
            if p_u_125.UpdateEquippedData == true then
                p_u_123._lobby_manager:update_player_character_to_equipped_data(p_u_124, p129)
            end;
        end;
        if p_u_125.FnPostSync == nil then
            f_on_finish(p127)
        else
            if typeof(p_u_125.FnPostSync) == "function" then
                p_u_125.FnPostSync(p127)
            elseif typeof(p_u_125.FnPostSync) == "table" then
                for _, v130 in pairs(p_u_125.FnPostSync) do
                    v130(p127)
                end;
            end;
            p_u_123._player_blob_manager:enqueue_blob_sync_request(p_u_124.UserId, v_u_2.PlayerBlobRequestType.Write, function(p131) --[[ Line: 843 ]]
                --[[ Upvalues: (copy 1): f_on_finish ]]
                f_on_finish(p131)
            end)
        end;
    end, false, p_u_125.FnAddRequestExtra and typeof(p_u_125.FnAddRequestExtra) == "table" and function(p132) --[[ Line: 803 ]]
        --[[ Upvalues: (copy 1): p_u_125 ]]
        for _, v133 in pairs(p_u_125.FnAddRequestExtra) do
            v133(p132)
        end;
    end or nil)
end;
return v_u_32;
