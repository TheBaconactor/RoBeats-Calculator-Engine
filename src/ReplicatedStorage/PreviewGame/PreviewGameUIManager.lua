-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:09 PM
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
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.PreviewGame.PreviewGameStartupMenu)
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v7:require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_12 ]]
    v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_9 = require(game.ReplicatedStorage.GameUI.SongTimeDisplay)
    v_u_10 = require(game.ReplicatedStorage.PreviewGame.PreviewGameSettingsListUI)
    v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_12 = require(game.ReplicatedStorage.GameUI.TouchDisplay)
end)
return {
    ["new"] = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_6, (ref 4): v_u_9, (ref 5): v_u_12, (ref 6): v_u_11, (copy 7): v_u_5, (ref 8): v_u_10, (copy 9): v_u_4, (copy 10): v_u_1 ]]
        local v15 = {
            ["add_control_popup"] = function(_, _, p14) --[[ Name: add_control_popup ]] --[[ Line: 137 ]]
                p14:Destroy()
            end
        }
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        v15.get_decal_ui_manager = function(_) --[[ Name: get_decal_ui_manager ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        local v_u_19 = nil
        local v_u_20 = nil
        v15.init = function(_, p21) --[[ Name: init ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (ref 3): v_u_18, (ref 4): v_u_2 ]]
            v_u_19 = p21
            v_u_20 = v_u_19._menus
            v_u_18 = v_u_2:new(v_u_19)
        end;
        v15.initialize_ui = function(_, p_u_22, p_u_23) --[[ Name: initialize_ui ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_16, (ref 4): v_u_9, (ref 5): v_u_17, (ref 6): v_u_12, (ref 7): v_u_20, (ref 8): v_u_11, (copy 9): p_u_13, (ref 10): v_u_5, (ref 11): v_u_10 ]]
            if v_u_3:test_enum_member(p_u_23, v_u_6) ~= true then
                p_u_23 = v_u_6.None
            end;
            v_u_16 = v_u_9:new(p_u_22)
            v_u_17 = v_u_12:new(p_u_22)
            local v_u_24 = 0
            local v_u_25 = nil
            v_u_25 = v_u_20:push_menu(v_u_11:new(p_u_22, p_u_13, v_u_20):set_text("Loading...", "Please wait..."):set_close_button_visible(false):set_update_fn(function(p26) --[[ Line: 63 ]]
                --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_5, (copy 3): p_u_22, (ref 4): v_u_20, (ref 5): v_u_25 ]]
                v_u_24 = v_u_24 + v_u_5:TimescaleToDeltaTime(p26)
                if p_u_22._world_effect_manager:is_game_stage_loaded() and v_u_24 > 1 or v_u_24 > 10 then
                    v_u_20:remove_menu(v_u_25)
                end;
            end):set_on_close_fn(function() --[[ Line: 69 ]]
                --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_10, (ref 3): v_u_20, (ref 4): v_u_11, (ref 5): p_u_13, (ref 6): p_u_23 ]]
                p_u_22._menus:push_menu(v_u_10:new(p_u_22, function() --[[ Line: 72 ]]
                    --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_20, (ref 3): v_u_11, (ref 4): p_u_13 ]]
                    local function _() --[[ Name: fn_on_finish ]] --[[ Line: 73 ]]
                        --[[ Upvalues: (ref 1): p_u_22 ]]
                        p_u_22:exit_to_lobby()
                    end;
                    if p_u_22._player_settings_manager:has_changes() then
                        local v_u_27 = v_u_20:push_menu(v_u_11:new(p_u_22, p_u_13, v_u_20):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
                        p_u_22._player_settings_manager:save_changes_to_playerblob(p_u_22, function() --[[ Line: 79 ]]
                            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_20, (copy 3): v_u_27 ]]
                            p_u_22._player_settings_manager:clear_changes()
                            v_u_20:remove_menu(v_u_27)
                            p_u_22:exit_to_lobby()
                        end)
                    else
                        p_u_22:exit_to_lobby()
                    end;
                end)):run_startup_menu(p_u_23)
            end))
        end;
        v15.is_ui_enabled = function(_) --[[ Name: is_ui_enabled ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            local v28 = v_u_19._menus:get_top_element()
            return (v28 == nil or typeof(v28.is_enabled) ~= "function") and true or v28:is_enabled();
        end;
        v15.refresh_local_tracksystem_display_mode = function(_) --[[ Name: refresh_local_tracksystem_display_mode ]] --[[ Line: 103 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_4 ]]
            local v29 = v_u_19._player_blob_manager:get_player_blob()
            local v30 = v_u_19:get_local_game_slot()
            local v31 = v_u_19:es_gamelocal_get_local_tracksystem()
            if v31 then
                local v32 = v_u_4:new()
                v32:add_playerblob_to_slot(v29, v30)
                v31:set_game_noteskin_info(v32, v30)
                v31:tracksystem_update_note_display_mode()
                v31:tracksystem_update_all_active_notes_display_mode()
            end;
            v_u_19._ui_manager:get_decal_ui_manager():calculate_screen_constants()
        end;
        v15.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18 ]]
            v_u_16:teardown()
            v_u_17:teardown()
            v_u_18:teardown()
        end;
        v15.update = function(p33, p34) --[[ Name: update ]] --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_17, (ref 3): v_u_19, (ref 4): v_u_18, (ref 5): v_u_16 ]]
            if v_u_1:is_mobile() then
                if p33:is_ui_enabled() then
                    v_u_17:set_enabled(false)
                else
                    v_u_17:set_enabled(true)
                end;
            end;
            v_u_17:update(p34, v_u_19)
            v_u_18:update(p34)
            v_u_16:update(p34, v_u_19)
        end;
        return v15;
    end
};
