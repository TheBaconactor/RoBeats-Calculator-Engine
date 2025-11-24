-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.InputUtil)
local v4 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPList)
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
local v_u_13 = nil
v11:require_client(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13 ]]
    v_u_12 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_AllMySongs)
    v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
local v14 = {}
local v_u_15 = v4:new():add_table({
    [v_u_3.KEY_MENU_MATCHMAKING_CHAT_FOCUS] = v_u_1.Key.KeybindMatchmakingChat,
    [v_u_3.KEY_CHAT_WINDOW_FOCUS] = v_u_1.Key.KeybindChatWindow,
    [v_u_3.KEY_TRACK1] = v_u_1.Key.KeybindTrack1,
    [v_u_3.KEY_TRACK2] = v_u_1.Key.KeybindTrack2,
    [v_u_3.KEY_TRACK3] = v_u_1.Key.KeybindTrack3,
    [v_u_3.KEY_TRACK4] = v_u_1.Key.KeybindTrack4,
    [v_u_3.KEY_POWERBAR_TRIGGER] = v_u_1.Key.KeybindPowerbarTrigger
})
v14.new = function(_) --[[ Name: new ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_6, (copy 4): v_u_8, (copy 5): v_u_2, (copy 6): v_u_15, (copy 7): v_u_3, (ref 8): v_u_12, (ref 9): v_u_13, (copy 10): v_u_7, (copy 11): v_u_9, (copy 12): v_u_10 ]]
    local v16 = {}
    local v_u_17 = v_u_1:new()
    local v_u_18 = false
    v16.set_character_culling_mode_from_settings = function(p19) --[[ Name: set_character_culling_mode_from_settings ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_1 ]]
        local l_Medium_0 = v_u_5.Mode.Medium
        if v_u_6:is_mobile() then
            if p19:get_key(v_u_1.Key.MobileCharacterCulling) ~= nil then
                l_Medium_0 = p19:get_key(v_u_1.Key.MobileCharacterCulling)
            end;
        elseif p19:get_key(v_u_1.Key.PCCharacterCulling) ~= nil then
            l_Medium_0 = p19:get_key(v_u_1.Key.PCCharacterCulling)
        end;
        v_u_5:set_mode(l_Medium_0)
    end;
    v16.update_from_json_str = function(p20, p21, p22) --[[ Name: update_from_json_str ]] --[[ Line: 55 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        v_u_17:load_from_json_str(p22)
        p20:update_keybinds(p21)
        p20:update_controller_keybinds(p21)
        p20:set_character_culling_mode_from_settings()
    end;
    v16.get_player_settings = function(_) --[[ Name: get_player_settings ]] --[[ Line: 63 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        return v_u_17;
    end;
    v16.get_key = function(_, p23) --[[ Name: get_key ]] --[[ Line: 65 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        return v_u_17:get_key(p23);
    end;
    v16.set_key = function(_, p24, p25) --[[ Name: set_key ]] --[[ Line: 69 ]]
        --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_18 ]]
        v_u_17:set_key(p24, p25)
        v_u_18 = true
    end;
    v16.set_key_no_changes = function(_, p26, p27) --[[ Name: set_key_no_changes ]] --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        v_u_17:set_key(p26, p27)
    end;
    v16.local_write_settings_to_playerblob = function(_, p28) --[[ Name: local_write_settings_to_playerblob ]] --[[ Line: 78 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_17 ]]
        v_u_8:set_player_settings_str(p28, v_u_17:to_json())
    end;
    v16.clear_changes = function(_) --[[ Name: clear_changes ]] --[[ Line: 82 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18 = false
    end;
    v16.has_changes = function(_) --[[ Name: has_changes ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    v16.save_changes_to_playerblob = function(_, p_u_29, p_u_30) --[[ Name: save_changes_to_playerblob ]] --[[ Line: 90 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_17 ]]
        p_u_29._evt:wait_on_event_once(v_u_2.EVT_PlayerSettings_ServerAcknowledgeUpdate, function(p_u_31) --[[ Line: 91 ]]
            --[[ Upvalues: (copy 1): p_u_29, (copy 2): p_u_30 ]]
            p_u_29._player_blob_manager:do_sync(function() --[[ Line: 92 ]]
                --[[ Upvalues: (ref 1): p_u_30, (copy 2): p_u_31 ]]
                p_u_30(p_u_31)
            end)
        end)
        p_u_29._evt:fire_event_to_server(v_u_2.EVT_PlayerSettings_ClientUpdate, v_u_17:to_json())
    end;
    v16.update_keybinds = function(_, p32) --[[ Name: update_keybinds ]] --[[ Line: 99 ]]
        --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_17, (ref 3): v_u_3 ]]
        for v33, v34 in v_u_15:key_itr() do
            local v35 = v_u_17:get_key(v34)
            if typeof(v35) == "number" and v35 >= 0 then
                local v36 = v_u_3:value_to_keycode_enum(v35)
                if v36 ~= nil then
                    p32._input:set_custom_key_keycode(v33, v36)
                end;
            else
                p32._input:remove_custom_key(v33)
            end;
        end;
    end;
    v16.set_keybind = function(p37, p38, p39, p40) --[[ Name: set_keybind ]] --[[ Line: 113 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_3 ]]
        p38._input:set_custom_key_keycode(p39, p40)
        if v_u_15:contains(p39) then
            local v41 = v_u_3:keycode_enum_to_value(p40)
            if v41 ~= nil then
                p37:set_key(v_u_15:get(p39), v41)
            end;
        end;
    end;
    v16.reset_keybinds = function(p42, p43) --[[ Name: reset_keybinds ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        p43._input:reset_to_default_controls()
        for _, v44 in v_u_15:key_itr() do
            p42:set_key(v44, -1)
        end;
    end;
    v16.get_note_speed_multiplier = function(_) --[[ Name: get_note_speed_multiplier ]] --[[ Line: 130 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        return v_u_17:get_note_speed_multiplier();
    end;
    v16.initial_settings_sync_update = function(_, p45) --[[ Name: initial_settings_sync_update ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_7, (ref 4): v_u_1 ]]
        v_u_12:initial_settings_sync_update(p45)
        v_u_13:initial_settings_sync_update(p45)
        v_u_7:set_selected_mode(p45._player_settings_manager:get_key(v_u_1.Key.MatchMode))
    end;
    v16.update_controller_keybinds = function(_, p46) --[[ Name: update_controller_keybinds ]] --[[ Line: 140 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_1, (copy 3): v_u_17, (ref 4): v_u_10 ]]
        local v47 = v_u_9:new()
        local l__input_0 = p46._input
        for _, v48 in l__input_0:get_track_index_list():key_itr() do
            local v49 = v_u_17:get_key((v_u_1:track_enum_to_controller_track_setting(v48)))
            if type(v49) == "table" then
                for v50 = 1, #v49 do
                    local v51 = v49[v50]
                    if l__input_0:value_to_controller_keycode():contains(v51) then
                        v47:push_back_to(v48, (l__input_0:value_to_controller_keycode():get(v51)))
                    end;
                end;
            end;
        end;
        local v52 = v_u_10:new()
        local v53 = v_u_17:get_key(v_u_1.Key.ControllerShowCursorList)
        if type(v53) == "table" then
            for v54 = 1, #v53 do
                local v55 = v53[v54]
                if l__input_0:value_to_controller_keycode():contains(v55) then
                    v52:push_back((l__input_0:value_to_controller_keycode():get(v55)))
                end;
            end;
        end;
        l__input_0:update_controller_keybinds(v47, v52)
    end;
    v16.reset_default_controller_keybinds = function(p56, p57) --[[ Name: reset_default_controller_keybinds ]] --[[ Line: 175 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_1, (copy 3): v_u_17, (ref 4): v_u_18 ]]
        for _, v58 in v_u_3:get_track_index_list():key_itr() do
            v_u_17:set_key(v_u_1:track_enum_to_controller_track_setting(v58), {})
        end;
        v_u_17:set_key(v_u_1.Key.ControllerShowCursorList, {})
        v_u_18 = true
        p56:update_controller_keybinds(p57)
    end;
    local function f_remove_tar_keycode_enum_from_current_settings(p59) --[[ Name: remove_tar_keycode_enum_from_current_settings ]] --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_1, (copy 3): v_u_17, (ref 4): v_u_10 ]]
        for _, v60 in v_u_3:get_track_index_list():key_itr() do
            local v61 = v_u_17:get_key((v_u_1:track_enum_to_controller_track_setting(v60)))
            if type(v61) == "table" then
                v_u_10:new(v61):remove(p59.Value)
            end;
        end;
        local v62 = v_u_17:get_key(v_u_1.Key.ControllerShowCursorList)
        if type(v62) == "table" then
            v_u_10:new(v62):remove(p59.Value)
        end;
    end;
    v16.add_controller_track_index_keybind = function(p63, p64, p65, p66) --[[ Name: add_controller_track_index_keybind ]] --[[ Line: 201 ]]
        --[[ Upvalues: (copy 1): f_remove_tar_keycode_enum_from_current_settings, (ref 2): v_u_1, (copy 3): v_u_17, (ref 4): v_u_10, (ref 5): v_u_18 ]]
        f_remove_tar_keycode_enum_from_current_settings(p66)
        v_u_10:new((v_u_17:get_key((v_u_1:track_enum_to_controller_track_setting(p65))))):push_back(p66.Value)
        v_u_18 = true
        p63:update_controller_keybinds(p64)
    end;
    v16.add_controller_show_cursor_keybind = function(p67, p68, p69) --[[ Name: add_controller_show_cursor_keybind ]] --[[ Line: 214 ]]
        --[[ Upvalues: (copy 1): f_remove_tar_keycode_enum_from_current_settings, (copy 2): v_u_17, (ref 3): v_u_1, (ref 4): v_u_10, (ref 5): v_u_18 ]]
        f_remove_tar_keycode_enum_from_current_settings(p69)
        v_u_10:new((v_u_17:get_key(v_u_1.Key.ControllerShowCursorList))):push_back(p69.Value)
        v_u_18 = true
        p67:update_controller_keybinds(p68)
    end;
    return v16;
end;
return v14;
