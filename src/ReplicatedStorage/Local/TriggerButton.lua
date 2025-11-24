-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:27 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
return {
    ["new"] = function(_, p_u_3, p4, p_u_5) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v6 = {}
        local v_u_7 = p4:get_game_slot()
        local v_u_8 = nil
        local function _() --[[ Name: cons ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_3, (copy 3): v_u_7, (copy 4): p_u_5 ]]
            v_u_8 = p_u_3._world_effect_manager:create_trigger_button_asset(p_u_3, v_u_7, p_u_5)
        end;
        v6.set_position = function(_, p9) --[[ Name: set_position ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_3, (ref 3): v_u_1 ]]
            v_u_8:set_cframe(CFrame.new((Vector3.new(p9.X, p_u_3:get_game_environment_center().Y, p9.Z))) * v_u_1:part_cframe_rotation(v_u_8:get_obj().PrimaryPart))
        end;
        v6.create_control_popup = function(_) --[[ Name: create_control_popup ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_3, (copy 3): v_u_7, (copy 4): p_u_5 ]]
            local v10 = v_u_8:get_obj()
            if v10:FindFirstChild("ControlPopup") then
                if p_u_3:is_spectate() ~= true and v_u_7 == p_u_3:get_local_game_slot() then
                    p_u_3._ui_manager:add_control_popup(p_u_5, v10.ControlPopup)
                    return;
                end;
                v10.ControlPopup:Destroy()
            end;
        end;
        v6.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8:teardown()
        end;
        v6.set_note_display_mode = function(_, p11) --[[ Name: set_note_display_mode ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2, (copy 3): p_u_3, (copy 4): v_u_7 ]]
            if v_u_8 == nil then
                return v_u_2:warnf("TriggerButton:set_note_display_mode _trigger_button_asset is nil");
            end;
            if typeof(v_u_8.set_note_display_mode) ~= "function" then
                return v_u_2:warnf("TriggerButton:set_note_display_mode _trigger_button_asset.set_note_display_mode is not fn");
            end;
            if p_u_3 == nil then
                return v_u_2:warnf("TriggerButton:set_note_display_mode _game is nil");
            end;
            v_u_8:set_note_display_mode(p11, v_u_7 == p_u_3:get_local_game_slot())
        end;
        v6.press = function(_) --[[ Name: press ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8:on_press()
        end;
        v6.release = function(_) --[[ Name: release ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8:on_release()
        end;
        v6.set_game_noteskin_colors = function(_, p12, p13) --[[ Name: set_game_noteskin_colors ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8:set_game_noteskin_colors(p12, p13)
        end;
        v6.update = function(_, p14, _) --[[ Name: update ]] --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): p_u_3, (copy 2): v_u_7, (ref 3): v_u_8 ]]
            if p_u_3._players._slots:contains(v_u_7) ~= false then
                v_u_8:update(p14)
            end;
        end;
        local _ = p_u_3._world_effect_manager:create_trigger_button_asset(p_u_3, v_u_7, p_u_5)
        return v6;
    end
};
