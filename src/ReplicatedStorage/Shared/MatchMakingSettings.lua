-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.GameStage.GameStageUtil)
local v_u_15 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 7 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
        return {
            ["MatchMode"] = v_u_1:get_selected_mode(),
            ["AutoEquipBestLoadout"] = true,
            ["SelectedGameStage"] = v_u_3:get_recommended_stage_id()
        };
    end,
    ["update_from_table"] = function(_, p4, p5) --[[ Name: update_from_table ]] --[[ Line: 15 ]]
        if type(p5) == "table" then
            if typeof(p4.MatchMode) == typeof(p5.MatchMode) then
                p4.MatchMode = p5.MatchMode
            end;
            if typeof(p4.AutoEquipBestLoadout) == typeof(p5.AutoEquipBestLoadout) then
                p4.AutoEquipBestLoadout = p5.AutoEquipBestLoadout
            end;
            if typeof(p4.SelectedGameStage) == typeof(p5.SelectedGameStage) then
                p4.SelectedGameStage = p5.SelectedGameStage
            end;
        end;
    end,
    ["get_match_mode"] = function(_, p6) --[[ Name: get_match_mode ]] --[[ Line: 28 ]]
        return p6.MatchMode;
    end,
    ["set_match_mode"] = function(_, p7, p8) --[[ Name: set_match_mode ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        v_u_2:is_enum_member(p8, v_u_1)
        if typeof(p7.MatchMode) == typeof(p8) then
            p7.MatchMode = p8
        end;
    end,
    ["get_auto_equip_best_loadout"] = function(_, p9) --[[ Name: get_auto_equip_best_loadout ]] --[[ Line: 36 ]]
        return p9.AutoEquipBestLoadout;
    end,
    ["set_auto_equip_best_loadout"] = function(_, p10, p11) --[[ Name: set_auto_equip_best_loadout ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        v_u_2:is_bool(p11)
        if typeof(p10.AutoEquipBestLoadout) == typeof(p11) then
            p10.AutoEquipBestLoadout = p11
        end;
    end,
    ["get_selected_game_stage"] = function(_, p12) --[[ Name: get_selected_game_stage ]] --[[ Line: 48 ]]
        return p12.SelectedGameStage;
    end,
    ["set_selected_game_stage"] = function(_, p13, p14) --[[ Name: set_selected_game_stage ]] --[[ Line: 49 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3 ]]
        v_u_2:is_true(v_u_3:is_valid_stage_id(p14))
        if typeof(p13.SelectedGameStage) == typeof(p14) then
            p13.SelectedGameStage = p14
        end;
    end
}
v_u_15.should_auto_equip_best_loadout = function(_, p16) --[[ Name: should_auto_equip_best_loadout ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_1 ]]
    local v17
    if v_u_15:get_match_mode(p16) == v_u_1.Compete then
        v17 = v_u_15:get_auto_equip_best_loadout(p16)
    else
        v17 = false
    end;
    return v17;
end;
return v_u_15;
