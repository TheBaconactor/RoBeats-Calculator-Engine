-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_2 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_3 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.PreviewGame.PreviewGameStartupMenu)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.EditorGame.Data.EditorGamePlayInfo)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
v9:require_client(function() --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_10 ]]
    v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.SongSelectV3UI)
end)
local v_u_11 = {
    ["get_song_select_preview_menu_restore_name"] = function(_) --[[ Name: get_song_select_preview_menu_restore_name ]] --[[ Line: 19 ]]
        return "SongSelectV3UI_PreviewGame";
    end
}
local v_u_12 = nil
v_u_11.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_3, (copy 5): v_u_5, (copy 6): v_u_6, (ref 7): v_u_12, (ref 8): v_u_10, (copy 9): v_u_7, (copy 10): v_u_11, (copy 11): v_u_8 ]]
    local v14 = {}
    v14.try_spectate_userid = function(_, p15, p_u_16) --[[ Name: try_spectate_userid ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_1, (ref 3): v_u_4, (ref 4): v_u_2, (ref 5): v_u_3 ]]
        p_u_13._evt:wait_on_event_once(v_u_1.EVT_LobbySpectate_ServerResponseRequestJoinPlayerId, function(p17, p18, p_u_19, p_u_20, p_u_21, p22, p23) --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_16, (ref 3): v_u_2, (ref 4): v_u_3, (ref 5): p_u_13, (ref 6): v_u_1 ]]
            v_u_4:puts("Received EVT_LobbySpectate_ServerResponseRequestJoinPlayerId (%s,%s)", tostring(p17), (tostring(p18)))
            if p17 == true then
                local v_u_24 = v_u_2:from_table(p22)
                local v_u_25 = v_u_3:from_table(p23)
                p_u_16(true, p18, function() --[[ Line: 34 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_1, (copy 3): p_u_19, (copy 4): p_u_20, (copy 5): p_u_21, (copy 6): v_u_24, (copy 7): v_u_25 ]]
                    p_u_13._menus:remove_all_menus()
                    p_u_13._lobby_join:teardown_lobby()
                    p_u_13._evt:fire_event_to_server(v_u_1.EVT_Lobby_ClientNotifyLeavingLobby)
                    p_u_13._game_join:start_game_spectate(p_u_13, p_u_19.SelectedSongKey, p_u_20, p_u_19.FocusedSlot, p_u_21, p_u_19.GameId, v_u_24, v_u_25)
                end)
            else
                p_u_16(false, p18, function() end)
            end;
        end)
        p_u_13._lobby_join:save_camera_position()
        p_u_13._evt:fire_event_to_server(v_u_1.EVT_LobbySpectate_ClientRequestJoinPlayerId, p15)
        v_u_4:puts("Sending EVT_LobbySpectate_ClientRequestJoinPlayerId userid(%d)", p15)
    end;
    local function f_save_lobby_state_and_teardown() --[[ Name: save_lobby_state_and_teardown ]] --[[ Line: 55 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_1 ]]
        local v26 = p_u_13._lobby_join:get_lobby()
        if v26 then
            v26._chat:store_chat_visible()
            v26._chat:set_chat_visible(false)
        end;
        p_u_13._lobby_join:save_restore_menu_names()
        p_u_13._lobby_join:save_camera_position()
        p_u_13._menus:remove_all_menus()
        p_u_13._lobby_join:teardown_lobby()
        p_u_13._evt:fire_event_to_server(v_u_1.EVT_Lobby_ClientNotifyLeavingLobby)
    end;
    v14.start_preview_game = function(_, p27) --[[ Name: start_preview_game ]] --[[ Line: 70 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (copy 3): f_save_lobby_state_and_teardown, (copy 4): p_u_13, (ref 5): v_u_1 ]]
        if v_u_5:test_enum_member(p27, v_u_6) ~= true then
            p27 = v_u_6.None
        end;
        f_save_lobby_state_and_teardown()
        p_u_13._evt:fire_event_to_server(v_u_1.EVT_Lobby_ClientNotifyEnterSettings, (p_u_13._game_join:start_preview_game(p27)))
    end;
    v14.show_song_select_preview_menu = function(_) --[[ Name: show_song_select_preview_menu ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_10, (copy 3): p_u_13, (ref 4): v_u_7, (ref 5): v_u_11 ]]
        if v_u_12 == nil then
            v_u_12 = v_u_10:create_info_state()
        end;
        local v_u_28 = p_u_13._lobby_join:get_lobby()
        if v_u_28 then
            local v30 = v_u_10:new(v_u_28, v_u_12, function(_) --[[ Line: 91 ]]
                return true;
            end, function(p29) --[[ Line: 94 ]]
                --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_28 ]]
                if v_u_7:singleton():contains_key(p29) then
                    v_u_28._game_join:set_last_loaded_songkey(p29)
                    v_u_28._spectate_manager:start_preview_game()
                end;
            end)
            v30.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): v_u_11 ]]
                return v_u_11:get_song_select_preview_menu_restore_name();
            end;
            v_u_28._menus:push_menu(v30)
        end;
    end;
    v14.start_editor_custom_map_game = function(_, p31, p32, p33) --[[ Name: start_editor_custom_map_game ]] --[[ Line: 106 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_4, (ref 3): v_u_8, (ref 4): v_u_1, (copy 5): f_save_lobby_state_and_teardown ]]
        local v34 = p_u_13._lobby_join:get_lobby()
        if v34 == nil then
            return v_u_4:warnf("LobbySpectateManager:start_editor_custom_map_game() - _lobby is nil");
        end;
        if p33 == nil then
            p33 = v_u_8:new()
            p33:set_rewarded_play(false)
        end;
        if p33:is_rewarded_play() then
            v34._evt:fire_event_to_server(v_u_1.EVT_EditorGame_ClientNotifyPlayStart, p31:to_table())
        end;
        f_save_lobby_state_and_teardown()
        v34._game_join:start_editor_custom_map_game(p31, p32, p33)
        p_u_13._evt:fire_event_to_server(v_u_1.EVT_Lobby_ClientNotifyEnterSettings, p31:get_source_songkey())
    end;
    return v14;
end;
return v_u_11;
