-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = {
    ["Tier"] = {
        ["T1"] = 1,
        ["T2"] = 2,
        ["T3"] = 3,
        ["T4"] = 4,
        ["T5"] = 5
    },
    ["Type"] = {
        ["Material"] = 1,
        ["FeverIcon"] = 2,
        ["Blueprint"] = 3,
        ["Pet"] = 4,
        ["Box"] = 5,
        ["Stage"] = 6,
        ["LeaderboardTicket"] = 7
    },
    ["BoxType"] = {
        ["SmallNote"] = 1,
        ["MediumNote"] = 2,
        ["LargeNote"] = 3,
        ["Gem"] = 4,
        ["MiniOneStar"] = 5,
        ["MiniTwoStar"] = 6,
        ["VIPSongNormal"] = 7,
        ["VIPSongHard"] = 8,
        ["Token"] = 9,
        ["Dance"] = 10
    }
}
v_u_2.new = function(_) --[[ Name: new ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v3 = {
        ["is_fever_icon"] = function(_) --[[ Name: is_fever_icon ]] --[[ Line: 60 ]]
            return false;
        end,
        ["get_fever_icon_id"] = function(_) --[[ Name: get_fever_icon_id ]] --[[ Line: 61 ]]
            return 0;
        end,
        ["is_blueprint"] = function(_) --[[ Name: is_blueprint ]] --[[ Line: 62 ]]
            return false;
        end,
        ["is_pet"] = function(_) --[[ Name: is_pet ]] --[[ Line: 63 ]]
            return false;
        end,
        ["get_pet_id"] = function(_) --[[ Name: get_pet_id ]] --[[ Line: 64 ]]
            return 0;
        end,
        ["is_box"] = function(_) --[[ Name: is_box ]] --[[ Line: 65 ]]
            return false;
        end,
        ["is_stage"] = function(_) --[[ Name: is_stage ]] --[[ Line: 67 ]]
            return false;
        end,
        ["get_stage_id"] = function(_) --[[ Name: get_stage_id ]] --[[ Line: 68 ]]
            return 1;
        end,
        ["is_leaderboard_ticket"] = function(_) --[[ Name: is_leaderboard_ticket ]] --[[ Line: 69 ]]
            return false;
        end,
        ["is_tradeable"] = function(_) --[[ Name: is_tradeable ]] --[[ Line: 89 ]]
            return true;
        end
    }
    v3.get_icon = function(p4) --[[ Name: get_icon ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:warnf("CraftingMaterialBase >> (%s) has not implemented get_icon()", p4:get_name())
        return "";
    end;
    v3.get_name = function(p5) --[[ Name: get_name ]] --[[ Line: 45 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:warnf("CraftingMaterialBase >> (%s) has not implemented get_name()", p5:get_name())
        return "CraftingMaterialBase";
    end;
    v3.get_description = function(p6) --[[ Name: get_description ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        v_u_1:warnf("CraftingMaterialBase >> (%s) has not implemented get_description()", p6:get_name())
        return "";
    end;
    v3.get_tier = function(p7) --[[ Name: get_tier ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_2 ]]
        v_u_1:warnf("CraftingMaterialBase >> (%s) has not implemented get_tier()", p7:get_name())
        return v_u_2.Tier.T1;
    end;
    v3.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        return v_u_2.BoxType.SmallNote;
    end;
    v3.get_type = function(p8) --[[ Name: get_type ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        if p8:is_fever_icon() then
            return v_u_2.Type.FeverIcon;
        elseif p8:is_blueprint() then
            return v_u_2.Type.Blueprint;
        elseif p8:is_pet() then
            return v_u_2.Type.Pet;
        elseif p8:is_box() then
            return v_u_2.Type.Box;
        elseif p8:is_stage() then
            return v_u_2.Type.Stage;
        elseif p8:is_leaderboard_ticket() then
            return v_u_2.Type.LeaderboardTicket;
        else
            return v_u_2.Type.Material;
        end;
    end;
    return v3;
end;
return v_u_2;
