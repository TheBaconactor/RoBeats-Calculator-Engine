-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_2 = require(game.ReplicatedStorage.Local.DecalUIManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
v5:require_client(function() --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_11, (ref 7): v_u_12, (ref 8): v_u_13, (ref 9): v_u_14 ]]
    v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_6 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_7 = require(game.ReplicatedStorage.GameUI.SongTimeDisplay)
    v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_9 = require(game.ReplicatedStorage.GameUI.TouchDisplay)
    v_u_10 = require(game.ReplicatedStorage.GameUI.PreStartCountdown)
    v_u_11 = require(game.ReplicatedStorage.GameUI.RankBar)
    v_u_12 = require(game.ReplicatedStorage.GameUI.QuitDisplayV2)
    v_u_13 = require(game.ReplicatedStorage.GameUI.ControlPopupManager)
    v_u_14 = require(game.ReplicatedStorage.GameUI.ComboNotifManager)
end)
return {
    ["new"] = function(_, _) --[[ Name: new ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_12, (ref 7): v_u_13, (ref 8): v_u_14, (copy 9): v_u_3, (copy 10): v_u_4, (copy 11): v_u_1 ]]
        local v15 = {
            ["is_ui_enabled"] = function(_) --[[ Name: is_ui_enabled ]] --[[ Line: 76 ]]
                return false;
            end
        }
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        v15.get_decal_ui_manager = function(_) --[[ Name: get_decal_ui_manager ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        local v_u_24 = nil
        local v_u_25 = nil
        v15.init = function(_, p26) --[[ Name: init ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_23, (ref 4): v_u_2 ]]
            v_u_24 = p26
            v_u_25 = v_u_24._menus
            v_u_23 = v_u_2:new(v_u_24)
        end;
        v15.initialize_ui = function(_, p_u_27) --[[ Name: initialize_ui ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_7, (ref 3): v_u_17, (ref 4): v_u_9, (ref 5): v_u_18, (ref 6): v_u_10, (ref 7): v_u_19, (ref 8): v_u_11, (ref 9): v_u_20, (ref 10): v_u_12, (ref 11): v_u_21, (ref 12): v_u_13, (ref 13): v_u_22, (ref 14): v_u_14 ]]
            v_u_16 = v_u_7:new(p_u_27)
            v_u_17 = v_u_9:new(p_u_27)
            v_u_18 = v_u_10:new(p_u_27)
            v_u_19 = v_u_11:new(p_u_27)
            v_u_20 = v_u_12:new(p_u_27, function() --[[ Line: 69 ]]
                --[[ Upvalues: (copy 1): p_u_27 ]]
                p_u_27:early_quit()
            end)
            v_u_21 = v_u_13:new(p_u_27)
            v_u_22 = v_u_14:new(p_u_27)
        end;
        v15.refresh_local_tracksystem_display_mode = function(_) --[[ Name: refresh_local_tracksystem_display_mode ]] --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_3 ]]
            local v28 = v_u_24._player_blob_manager:get_player_blob()
            local v29 = v_u_24:get_local_game_slot()
            local v30 = v_u_24:es_gamelocal_get_local_tracksystem()
            if v30 then
                local v31 = v_u_3:new()
                v31:add_playerblob_to_slot(v28, v29)
                v30:set_game_noteskin_info(v31, v29)
                v30:tracksystem_update_note_display_mode()
                v30:tracksystem_update_all_active_notes_display_mode()
            end;
            v_u_24._ui_manager:get_decal_ui_manager():calculate_screen_constants()
        end;
        v15.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_23, (ref 4): v_u_18, (ref 5): v_u_19, (ref 6): v_u_20, (ref 7): v_u_21, (ref 8): v_u_22 ]]
            if v_u_16 ~= nil then
                v_u_16:teardown()
                v_u_17:teardown()
                v_u_23:teardown()
                v_u_18:teardown()
                v_u_19:teardown()
                v_u_20:teardown()
                v_u_21:teardown()
                v_u_22:teardown()
                v_u_16 = nil
                v_u_17 = nil
                v_u_23 = nil
                v_u_18 = nil
                v_u_19 = nil
                v_u_20 = nil
                v_u_21 = nil
                v_u_22 = nil
            end;
        end;
        local l_GameQuitDisplay_0 = v_u_4.Test.GameQuitDisplay
        v_u_4:register_ui_needs_refresh_should_run_test_type(l_GameQuitDisplay_0)
        v15.update = function(p32, p33) --[[ Name: update ]] --[[ Line: 118 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_1, (ref 3): v_u_17, (ref 4): v_u_24, (ref 5): v_u_23, (ref 6): v_u_18, (ref 7): v_u_19, (ref 8): v_u_4, (copy 9): l_GameQuitDisplay_0, (ref 10): v_u_20, (ref 11): v_u_21, (ref 12): v_u_22 ]]
            if v_u_16 ~= nil then
                if v_u_1:is_mobile() then
                    if p32:is_ui_enabled() then
                        v_u_17:set_enabled(false)
                    else
                        v_u_17:set_enabled(true)
                    end;
                end;
                v_u_17:update(p33, v_u_24)
                v_u_23:update(p33)
                v_u_16:update(p33, v_u_24)
                v_u_18:update(p33, v_u_24)
                v_u_19:update(p33, v_u_24)
                local v34 = v_u_4:singleton()
                if v34:should_run(l_GameQuitDisplay_0) then
                    local v35 = v34:get_test_state(l_GameQuitDisplay_0)
                    local v36 = v35:get_dt_scale()
                    v_u_24._input:set_frame_index_state(v35)
                    v_u_20:update(v36, v_u_24)
                    v_u_21:update(v36, v_u_24)
                    v_u_24._input:set_frame_index_state(nil)
                end;
                v_u_22:update(p33, v_u_24)
            end;
        end;
        v15.add_control_popup = function(_, p37, p38) --[[ Name: add_control_popup ]] --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21:add_control_popup(p37, p38)
        end;
        return v15;
    end
};
