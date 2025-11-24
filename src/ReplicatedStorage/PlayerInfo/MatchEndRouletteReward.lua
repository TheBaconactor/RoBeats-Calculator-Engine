-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_4 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_9 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_10 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_13 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_45 = {
    ["RewardType"] = {
        ["Coin"] = 1,
        ["Material"] = 2,
        ["Song"] = 3
    },
    ["RewardEntry"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): v_u_46, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_7, (copy 6): v_u_10, (copy 7): v_u_9 ]]
            local v47 = {}
            local l_Coin_1 = v_u_46.Coin
            local v_u_48 = 1
            local v_u_49 = -1
            local v_u_50 = 0
            v47.set_coin_reward = function(p51, p52) --[[ Name: set_coin_reward ]] --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): l_Coin_1, (ref 3): v_u_46, (ref 4): v_u_48 ]]
                v_u_1:is_int(p52)
                l_Coin_1 = v_u_46.Coin
                v_u_48 = p52
                return p51;
            end;
            v47.set_material_reward = function(p53, p54, _) --[[ Name: set_material_reward ]] --[[ Line: 44 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_4, (ref 3): l_Coin_1, (ref 4): v_u_46, (ref 5): v_u_48, (ref 6): v_u_49 ]]
                v_u_1:is_true(v_u_4:singleton():contains_material(p54))
                l_Coin_1 = v_u_46.Material
                v_u_48 = 1
                v_u_49 = p54
                return p53;
            end;
            v47.set_song_reward = function(p55, p56) --[[ Name: set_song_reward ]] --[[ Line: 51 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_2, (ref 3): l_Coin_1, (ref 4): v_u_46, (ref 5): v_u_48, (ref 6): v_u_49 ]]
                v_u_1:is_true(v_u_2:singleton():contains_key(p56))
                l_Coin_1 = v_u_46.Song
                v_u_48 = 1
                v_u_49 = p56
                return p55;
            end;
            v47.get_reward_type = function(_) --[[ Name: get_reward_type ]] --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): l_Coin_1 ]]
                return l_Coin_1;
            end;
            v47.get_reward_count = function(_) --[[ Name: get_reward_count ]] --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): v_u_48 ]]
                return v_u_48;
            end;
            v47.set_reward_count = function(_, p57) --[[ Name: set_reward_count ]] --[[ Line: 61 ]]
                --[[ Upvalues: (ref 1): v_u_48 ]]
                v_u_48 = p57
            end;
            v47.get_reward_id = function(_) --[[ Name: get_reward_id ]] --[[ Line: 62 ]]
                --[[ Upvalues: (ref 1): v_u_49 ]]
                return v_u_49;
            end;
            v47.get_weight = function(_) --[[ Name: get_weight ]] --[[ Line: 63 ]]
                --[[ Upvalues: (ref 1): v_u_50 ]]
                return v_u_50;
            end;
            v47.set_weight = function(p58, p59) --[[ Name: set_weight ]] --[[ Line: 64 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_50 ]]
                v_u_1:is_number(p59)
                v_u_1:is_true(p59 > 0)
                v_u_50 = p59
                return p58;
            end;
            v47.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 71 ]]
                --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_48, (ref 3): v_u_49, (ref 4): v_u_50 ]]
                return {
                    ["RewardType"] = l_Coin_1,
                    ["RewardCount"] = v_u_48,
                    ["RewardID"] = v_u_49,
                    ["Weight"] = v_u_50
                };
            end;
            v47.load_table = function(p60, p61) --[[ Name: load_table ]] --[[ Line: 80 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_46, (ref 3): l_Coin_1, (ref 4): v_u_48, (ref 5): v_u_49, (ref 6): v_u_50 ]]
                v_u_1:is_enum_member(p61.RewardType, v_u_46)
                l_Coin_1 = p61.RewardType
                v_u_48 = p61.RewardCount
                v_u_49 = p61.RewardID
                v_u_50 = p61.Weight
                return p60;
            end;
            v47.apply_to_playerblob = function(_, p62) --[[ Name: apply_to_playerblob ]] --[[ Line: 89 ]]
                --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_7, (ref 4): v_u_48, (ref 5): v_u_10, (ref 6): v_u_49 ]]
                if l_Coin_1 == v_u_46.Coin then
                    v_u_7:set_coin_currency(p62, v_u_7:get_coin_currency(p62) + v_u_48)
                    return;
                elseif l_Coin_1 == v_u_46.Material then
                    v_u_10:add_crafting_materials_of_id(p62, v_u_49, v_u_48)
                elseif l_Coin_1 == v_u_46.Song then
                    for _ = 1, v_u_48 do
                        v_u_7:add_song(p62, v_u_49)
                    end;
                end;
            end;
            v47.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_48, (ref 4): v_u_4, (ref 5): v_u_49, (ref 6): v_u_2 ]]
                if l_Coin_1 == v_u_46.Coin then
                    return string.format("%d Coins", v_u_48);
                end;
                if l_Coin_1 == v_u_46.Material then
                    local v63 = v_u_4:singleton():get_material_name(v_u_49)
                    if v_u_48 > 1 then
                        v63 = string.format("%s x%d", v63, v_u_48)
                    end;
                    return v63;
                end;
                if l_Coin_1 == v_u_46.Song then
                    local v64 = string.format("Copy of \"%s\"", v_u_2:singleton():get_title_for_key(v_u_49))
                    if v_u_48 > 1 then
                        v64 = string.format("%s x%d", v64, v_u_48)
                    end;
                    return v64;
                end;
            end;
            v47.get_name_color = function(_) --[[ Name: get_name_color ]] --[[ Line: 119 ]]
                --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_48, (ref 4): v_u_4, (ref 5): v_u_9, (ref 6): v_u_49 ]]
                if l_Coin_1 == v_u_46.Coin then
                    if v_u_48 <= 10 then
                        return v_u_4:singleton():tier_get_color(v_u_9.Tier.T1);
                    elseif v_u_48 <= 50 then
                        return v_u_4:singleton():tier_get_color(v_u_9.Tier.T2);
                    else
                        return v_u_4:singleton():tier_get_color(v_u_9.Tier.T3);
                    end;
                else
                    if l_Coin_1 == v_u_46.Material then
                        return v_u_4:singleton():tier_get_color(v_u_4:singleton():get_material_tier(v_u_49));
                    end;
                    if l_Coin_1 == v_u_46.Song then
                        return v_u_4:singleton():tier_get_color(v_u_9.Tier.T4);
                    end;
                    return;
                end;
            end;
            v47.render_image = function(_, p65, p66) --[[ Name: render_image ]] --[[ Line: 135 ]]
                --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_48, (ref 4): v_u_4, (ref 5): v_u_49, (ref 6): v_u_2 ]]
                if l_Coin_1 == v_u_46.Coin then
                    if v_u_48 <= 10 then
                        p65.Image = "http://www.roblox.com/asset/?id=7118280950"
                    elseif v_u_48 <= 50 then
                        p65.Image = "http://www.roblox.com/asset/?id=7118281323"
                    else
                        p65.Image = "http://www.roblox.com/asset/?id=7118281658"
                    end;
                    p66.Visible = false
                    return;
                elseif l_Coin_1 == v_u_46.Material then
                    p65.Image = v_u_4:singleton():get_material_icon(v_u_49)
                    p66.Visible = false
                elseif l_Coin_1 == v_u_46.Song then
                    v_u_2:singleton():render_coverimage_for_key(p65, p66, v_u_49)
                end;
            end;
            return v47;
        end
    },
    ["color_and_tier_to_material_id"] = function(_, p34, p35) --[[ Name: color_and_tier_to_material_id ]] --[[ Line: 162 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:color_and_tier_to_material_id(p34, p35);
    end,
    ["reward_list_roll"] = function(_, p36) --[[ Name: reward_list_roll ]] --[[ Line: 270 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_8 ]]
        if p36:count() <= 0 then
            return nil, -1;
        end;
        local v37 = 0
        for v38 = 1, p36:count() do
            v37 = v37 + p36:get(v38):get_weight()
        end;
        local v39 = v_u_6:rand_rangef(0, v37)
        local v40 = 1
        while v39 > 0 do
            local v41 = p36:get(v40)
            if v39 <= v41:get_weight() then
                break;
            end;
            v39 = v39 - v41:get_weight()
            v40 = v_u_8:wrap_val(v40 + 1, 1, p36:count() + 1)
        end;
        return p36:get(v40), v40;
    end,
    ["reward_list_to_table"] = function(_, p42) --[[ Name: reward_list_to_table ]] --[[ Line: 287 ]]
        local v43 = {}
        for v44 = 1, p42:count() do
            v43[#v43 + 1] = p42:get(v44):to_table()
        end;
        return v43;
    end
}
local v_u_46 = {
    ["Coin"] = 1,
    ["Material"] = 2,
    ["Song"] = 3
}
local v_u_67 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_46, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_7, (copy 6): v_u_10, (copy 7): v_u_9 ]]
        local v47 = {}
        local l_Coin_1 = v_u_46.Coin
        local v_u_48 = 1
        local v_u_49 = -1
        local v_u_50 = 0
        v47.set_coin_reward = function(p51, p52) --[[ Name: set_coin_reward ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): l_Coin_1, (ref 3): v_u_46, (ref 4): v_u_48 ]]
            v_u_1:is_int(p52)
            l_Coin_1 = v_u_46.Coin
            v_u_48 = p52
            return p51;
        end;
        v47.set_material_reward = function(p53, p54, _) --[[ Name: set_material_reward ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_4, (ref 3): l_Coin_1, (ref 4): v_u_46, (ref 5): v_u_48, (ref 6): v_u_49 ]]
            v_u_1:is_true(v_u_4:singleton():contains_material(p54))
            l_Coin_1 = v_u_46.Material
            v_u_48 = 1
            v_u_49 = p54
            return p53;
        end;
        v47.set_song_reward = function(p55, p56) --[[ Name: set_song_reward ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_2, (ref 3): l_Coin_1, (ref 4): v_u_46, (ref 5): v_u_48, (ref 6): v_u_49 ]]
            v_u_1:is_true(v_u_2:singleton():contains_key(p56))
            l_Coin_1 = v_u_46.Song
            v_u_48 = 1
            v_u_49 = p56
            return p55;
        end;
        v47.get_reward_type = function(_) --[[ Name: get_reward_type ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): l_Coin_1 ]]
            return l_Coin_1;
        end;
        v47.get_reward_count = function(_) --[[ Name: get_reward_count ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_48 ]]
            return v_u_48;
        end;
        v47.set_reward_count = function(_, p57) --[[ Name: set_reward_count ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_48 ]]
            v_u_48 = p57
        end;
        v47.get_reward_id = function(_) --[[ Name: get_reward_id ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_49 ]]
            return v_u_49;
        end;
        v47.get_weight = function(_) --[[ Name: get_weight ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_50 ]]
            return v_u_50;
        end;
        v47.set_weight = function(p58, p59) --[[ Name: set_weight ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_50 ]]
            v_u_1:is_number(p59)
            v_u_1:is_true(p59 > 0)
            v_u_50 = p59
            return p58;
        end;
        v47.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_48, (ref 3): v_u_49, (ref 4): v_u_50 ]]
            return {
                ["RewardType"] = l_Coin_1,
                ["RewardCount"] = v_u_48,
                ["RewardID"] = v_u_49,
                ["Weight"] = v_u_50
            };
        end;
        v47.load_table = function(p60, p61) --[[ Name: load_table ]] --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_46, (ref 3): l_Coin_1, (ref 4): v_u_48, (ref 5): v_u_49, (ref 6): v_u_50 ]]
            v_u_1:is_enum_member(p61.RewardType, v_u_46)
            l_Coin_1 = p61.RewardType
            v_u_48 = p61.RewardCount
            v_u_49 = p61.RewardID
            v_u_50 = p61.Weight
            return p60;
        end;
        v47.apply_to_playerblob = function(_, p62) --[[ Name: apply_to_playerblob ]] --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_7, (ref 4): v_u_48, (ref 5): v_u_10, (ref 6): v_u_49 ]]
            if l_Coin_1 == v_u_46.Coin then
                v_u_7:set_coin_currency(p62, v_u_7:get_coin_currency(p62) + v_u_48)
                return;
            elseif l_Coin_1 == v_u_46.Material then
                v_u_10:add_crafting_materials_of_id(p62, v_u_49, v_u_48)
            elseif l_Coin_1 == v_u_46.Song then
                for _ = 1, v_u_48 do
                    v_u_7:add_song(p62, v_u_49)
                end;
            end;
        end;
        v47.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_48, (ref 4): v_u_4, (ref 5): v_u_49, (ref 6): v_u_2 ]]
            if l_Coin_1 == v_u_46.Coin then
                return string.format("%d Coins", v_u_48);
            end;
            if l_Coin_1 == v_u_46.Material then
                local v63 = v_u_4:singleton():get_material_name(v_u_49)
                if v_u_48 > 1 then
                    v63 = string.format("%s x%d", v63, v_u_48)
                end;
                return v63;
            end;
            if l_Coin_1 == v_u_46.Song then
                local v64 = string.format("Copy of \"%s\"", v_u_2:singleton():get_title_for_key(v_u_49))
                if v_u_48 > 1 then
                    v64 = string.format("%s x%d", v64, v_u_48)
                end;
                return v64;
            end;
        end;
        v47.get_name_color = function(_) --[[ Name: get_name_color ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_48, (ref 4): v_u_4, (ref 5): v_u_9, (ref 6): v_u_49 ]]
            if l_Coin_1 == v_u_46.Coin then
                if v_u_48 <= 10 then
                    return v_u_4:singleton():tier_get_color(v_u_9.Tier.T1);
                elseif v_u_48 <= 50 then
                    return v_u_4:singleton():tier_get_color(v_u_9.Tier.T2);
                else
                    return v_u_4:singleton():tier_get_color(v_u_9.Tier.T3);
                end;
            else
                if l_Coin_1 == v_u_46.Material then
                    return v_u_4:singleton():tier_get_color(v_u_4:singleton():get_material_tier(v_u_49));
                end;
                if l_Coin_1 == v_u_46.Song then
                    return v_u_4:singleton():tier_get_color(v_u_9.Tier.T4);
                end;
                return;
            end;
        end;
        v47.render_image = function(_, p65, p66) --[[ Name: render_image ]] --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): l_Coin_1, (ref 2): v_u_46, (ref 3): v_u_48, (ref 4): v_u_4, (ref 5): v_u_49, (ref 6): v_u_2 ]]
            if l_Coin_1 == v_u_46.Coin then
                if v_u_48 <= 10 then
                    p65.Image = "http://www.roblox.com/asset/?id=7118280950"
                elseif v_u_48 <= 50 then
                    p65.Image = "http://www.roblox.com/asset/?id=7118281323"
                else
                    p65.Image = "http://www.roblox.com/asset/?id=7118281658"
                end;
                p66.Visible = false
                return;
            elseif l_Coin_1 == v_u_46.Material then
                p65.Image = v_u_4:singleton():get_material_icon(v_u_49)
                p66.Visible = false
            elseif l_Coin_1 == v_u_46.Song then
                v_u_2:singleton():render_coverimage_for_key(p65, p66, v_u_49)
            end;
        end;
        return v47;
    end
}
v_u_67.from_table = function(_, p68) --[[ Name: from_table ]] --[[ Line: 156 ]]
    --[[ Upvalues: (copy 1): v_u_67 ]]
    return v_u_67:new():load_table(p68);
end;
local function f_reward_list_add_material_of_color_and_tier(p69, p70, p71, p72) --[[ Name: reward_list_add_material_of_color_and_tier ]] --[[ Line: 166 ]]
    --[[ Upvalues: (copy 1): v_u_45, (copy 2): v_u_4, (copy 3): v_u_67 ]]
    local v73 = v_u_45:color_and_tier_to_material_id(p70, p71)
    if v_u_4:singleton():contains_material(v73) then
        p69:push_back(v_u_67:new():set_material_reward(v73, 1):set_weight(p72))
    end;
end;
local function _(p74) --[[ Name: player_count_multiplier ]] --[[ Line: 173 ]]
    return p74 == 4 and 4 or (p74 == 3 and 3 or (p74 == 2 and 2 or 1));
end;
local function _(p75) --[[ Name: difficulty_count_multiplier ]] --[[ Line: 185 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_2, (copy 3): v_u_8 ]]
    return v_u_8:YForPointOf2PtLineP1P2X(0, 1, 24, 3, (v_u_6:clamp(v_u_2:singleton():get_difficulty_for_key(p75), 1, 24)));
end;
v_u_45.get_reward_list_for_match = function(_, p76, p77, p78, p79, p80) --[[ Name: get_reward_list_for_match ]] --[[ Line: 190 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_11, (copy 3): v_u_13, (copy 4): v_u_6, (copy 5): v_u_2, (copy 6): v_u_8, (copy 7): v_u_67, (copy 8): v_u_3, (copy 9): f_reward_list_add_material_of_color_and_tier, (copy 10): v_u_9, (copy 11): v_u_7 ]]
    local v81 = v_u_5:new()
    if v_u_11.DebugRewardOnSoloLeave == true then
        p78 = p78 < 0.5 and 1 or p78
    elseif p78 <= v_u_13.MIN_ACCURACY_FOR_REWARDS_PCT then
        return v81;
    end;
    local v82 = (p77 == 4 and 4 or (p77 == 3 and 3 or (p77 == 2 and 2 or 1))) * v_u_8:YForPointOf2PtLineP1P2X(0, 1, 24, 3, (v_u_6:clamp(v_u_2:singleton():get_difficulty_for_key(p76), 1, 24)))
    local v83 = p80 <= 0 and 0 or v_u_8:YForPointOf2PtLineP1P2X(1, 0, 4, 2, p80)
    v81:push_back(v_u_67:new():set_coin_reward(5):set_weight(35 * v_u_6:clamp(v82 * 0.15, 1, 10) + v83 * 30))
    v81:push_back(v_u_67:new():set_coin_reward(10):set_weight(25 * v_u_6:clamp(v82 * 0.2, 1, 10) + v83 * 15))
    if p78 >= 0.5 and p80 < 30 then
        v81:push_back(v_u_67:new():set_coin_reward(25):set_weight(10 * v_u_6:clamp(v82 * 0.5, 1, 10)))
    end;
    if p78 >= 0.7 and p80 < 20 then
        v81:push_back(v_u_67:new():set_coin_reward(50):set_weight(7 * v_u_6:clamp(v82 * 0.55, 1, 10)))
    end;
    if p78 >= 0.85 and p80 < 15 then
        v81:push_back(v_u_67:new():set_coin_reward(100):set_weight(3 * v_u_6:clamp(v82 * 0.65, 1, 10)))
    end;
    if p78 >= 0.95 and p80 < 10 then
        v81:push_back(v_u_67:new():set_coin_reward(200):set_weight(1 * v_u_6:clamp(v82 * 0.75, 1, 10)))
    end;
    local v84 = v_u_3:songkey_primary_color(p76)
    local v85 = v_u_3:songkey_has_secondary_color(p76)
    local v86 = v_u_3:songkey_secondary_color(p76)
    if p78 >= 0.5 then
        if v85 then
            f_reward_list_add_material_of_color_and_tier(v81, v84, v_u_9.Tier.T1, 50 * v_u_6:clamp(v82 * 0.5, 1, 10))
            f_reward_list_add_material_of_color_and_tier(v81, v86, v_u_9.Tier.T1, 35 * v_u_6:clamp(v82 * 0.5, 1, 10))
        else
            f_reward_list_add_material_of_color_and_tier(v81, v84, v_u_9.Tier.T1, 85 * v_u_6:clamp(v82 * 0.5, 1, 10))
        end;
    end;
    if p78 >= 0.775 and p80 < 15 then
        if v85 then
            f_reward_list_add_material_of_color_and_tier(v81, v84, v_u_9.Tier.T2, 12.5 * v_u_6:clamp(v82 * 0.75, 1, 10))
            f_reward_list_add_material_of_color_and_tier(v81, v86, v_u_9.Tier.T2, 7.5 * v_u_6:clamp(v82 * 0.75, 1, 10))
        else
            f_reward_list_add_material_of_color_and_tier(v81, v84, v_u_9.Tier.T2, 20 * v_u_6:clamp(v82 * 0.75, 1, 10))
        end;
    end;
    if p78 >= 0.9 and p80 < 10 then
        if v85 then
            f_reward_list_add_material_of_color_and_tier(v81, v84, v_u_9.Tier.T3, 3 * v_u_6:clamp(v82 * 1, 1, 10))
            f_reward_list_add_material_of_color_and_tier(v81, v86, v_u_9.Tier.T3, 2 * v_u_6:clamp(v82 * 1, 1, 10))
        else
            f_reward_list_add_material_of_color_and_tier(v81, v84, v_u_9.Tier.T3, 5 * v_u_6:clamp(v82 * 1, 1, 10))
        end;
    end;
    local v87 = v_u_7:get_song_key_owned_count(p79, p76) > 0
    local v88 = v_u_2:singleton():get_songkey_should_grant(p76)
    local v89 = v_u_2:singleton():key_get_audiomod(p76) == v_u_2.MOD_HARDMODE
    if v88 and (v_u_2:singleton():key_get_audiomod(p76) ~= v_u_2.MOD_EASY and (p78 > 0.75 and p80 < 10)) then
        if v87 then
            if v89 then
                v81:push_back(v_u_67:new():set_song_reward(p76):set_weight(1 * v_u_6:clamp(v82 * 0.5, 1, 10)))
                return v81;
            else
                v81:push_back(v_u_67:new():set_song_reward(p76):set_weight(5 * v_u_6:clamp(v82 * 0.5, 1, 10)))
                return v81;
            end;
        end;
        if v89 then
            v81:push_back(v_u_67:new():set_song_reward(p76):set_weight(4 * v_u_6:clamp(v82 * 0.5, 1, 10)))
            return v81;
        end;
        v81:push_back(v_u_67:new():set_song_reward(p76):set_weight(20 * v_u_6:clamp(v82 * 0.5, 1, 10)))
    end;
    return v81;
end;
v_u_45.reward_table_to_list = function(_, p90) --[[ Name: reward_table_to_list ]] --[[ Line: 295 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_67 ]]
    local v91 = v_u_5:new()
    for v92 = 1, #p90 do
        v91:push_back(v_u_67:from_table(p90[v92]))
    end;
    return v91;
end;
return v_u_45;
