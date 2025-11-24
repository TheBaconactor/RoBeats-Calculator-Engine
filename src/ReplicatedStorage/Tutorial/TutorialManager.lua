-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Tutorial.TutorialData)
local v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.NewsUI)
require(game.ReplicatedStorage.Lobby.Menus.MatchLeavePenaltyUI)
local v_u_10 = require(game.ReplicatedStorage.Tutorial.Menus.TutorialSongSelectUI)
local v_u_11 = require(game.ReplicatedStorage.Tutorial.Menus.TutorialStartUI)
local v_u_12 = require(game.ReplicatedStorage.Tutorial.Menus.TutorialSongAcquiredUI)
require(game.ReplicatedStorage.Tutorial.Menus.TutorialInfoUI)
local v_u_13 = {
    ["Mode"] = {
        ["None"] = 0,
        ["TutorialStartUI"] = 1,
        ["IngameTutorial"] = 2,
        ["TutorialSongAcquire"] = 3,
        ["SongSelect"] = 4,
        ["SongSelectWaitingForServerResponse"] = 5,
        ["ShowInfo"] = 6,
        ["Debug_WaitForTutorialServerConfirmation"] = -1,
        ["Debug_EndWaitForPlayerBlobSync"] = -2
    }
}
v_u_13.new = function(_, p_u_14) --[[ Name: new ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_4, (copy 7): v_u_8, (copy 8): v_u_11, (copy 9): v_u_1, (copy 10): v_u_12, (copy 11): v_u_5, (copy 12): v_u_10, (copy 13): v_u_9 ]]
    local v15 = {}
    local l_None_0 = v_u_13.Mode.None
    local function _(p16) --[[ Name: report_tutorial_step ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_3 ]]
        p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientReportTutorialStep, p16)
    end;
    v15.do_startup = function(p17) --[[ Name: do_startup ]] --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_2, (ref 3): v_u_6, (ref 4): v_u_7, (ref 5): v_u_4, (ref 6): v_u_13 ]]
        if p_u_14._player_blob_manager:is_synced() == false then
            v_u_2:warnf("TutorialManager:do_startup PlayerBlob NOT SYNCED")
        end;
        v_u_6:ptry(function() --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:set_local_character_visible(false)
            v_u_7:set_lobby_characters_visible(false)
        end)
        local l_TutorialStage_0 = p_u_14._player_blob_manager:get_player_blob().TutorialStage
        if l_TutorialStage_0 == v_u_4.TutorialStage.NewPlayer or l_TutorialStage_0 == v_u_4.TutorialStage.LegacyTutorialComplete then
            p17:do_tutorial_stage(v_u_13.Mode.TutorialStartUI)
            return;
        elseif l_TutorialStage_0 == v_u_4.TutorialStage.TutorialSongAcquired then
            p17:do_tutorial_stage(v_u_13.Mode.SongSelect)
        else
            p17:sync_playerblob_and_start_lobby(function() end, true)
        end;
    end;
    v15.update = function(p18, _) --[[ Name: update ]] --[[ Line: 78 ]]
        --[[ Upvalues: (ref 1): l_None_0, (ref 2): v_u_13, (copy 3): p_u_14, (ref 4): v_u_8, (ref 5): v_u_3 ]]
        if l_None_0 == v_u_13.Mode.IngameTutorial and p_u_14._game_join:is_game_finished() then
            if p_u_14._game_join:is_game_early_quit() then
                p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientReportTutorialStep, v_u_8.Step.TutorialGameEarlyQuit)
            else
                p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientReportTutorialStep, v_u_8.Step.TutorialGameFinish)
            end;
            p_u_14._game_join:teardown_game()
            p18:do_tutorial_stage(v_u_13.Mode.TutorialSongAcquire)
        end;
    end;
    v15.do_tutorial_stage = function(p19, p20) --[[ Name: do_tutorial_stage ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): l_None_0, (ref 2): v_u_13, (copy 3): p_u_14, (ref 4): v_u_11, (ref 5): v_u_8, (ref 6): v_u_3, (ref 7): v_u_1, (ref 8): v_u_12, (ref 9): v_u_5, (ref 10): v_u_10, (ref 11): v_u_2 ]]
        local v_u_21 = l_None_0
        l_None_0 = p20
        if l_None_0 == v_u_13.Mode.TutorialStartUI then
            p_u_14._chat:set_chat_visible(false)
            p_u_14._menus:push_menu(v_u_11:new(p_u_14, p_u_14._spui, p_u_14._menus))
            p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientReportTutorialStep, v_u_8.Step.TutorialBegin)
            return;
        elseif l_None_0 == v_u_13.Mode.TutorialSongAcquire then
            local v_u_22 = p_u_14._menus:push_menu(v_u_1:new(p_u_14, p_u_14._spui, p_u_14._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_14._evt:wait_on_event_once(v_u_3.EVT_Tutorial_ServerResponseTutorialSongGive, function(p_u_23) --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): p_u_14, (copy 2): v_u_22, (copy 3): v_u_21, (ref 4): v_u_13, (ref 5): v_u_12 ]]
                p_u_14._player_blob_manager:do_sync(function(_) --[[ Line: 112 ]]
                    --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_22, (ref 3): v_u_21, (ref 4): v_u_13, (ref 5): v_u_12, (copy 6): p_u_23 ]]
                    p_u_14._menus:remove_menu(v_u_22)
                    p_u_14._menus:push_menu(v_u_12:new(p_u_14, p_u_14._spui, p_u_14._menus, p_u_23, v_u_21 == v_u_13.Mode.TutorialStartUI))
                    p_u_14._player_blob_manager:add_recently_acquired_songid(p_u_23)
                end)
            end)
            p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientRequestTutorialSongGive)
            return;
        elseif l_None_0 == v_u_13.Mode.SongSelect then
            p_u_14._evt:wait_on_event_once(v_u_3.EVT_Tutorial_ServerSongSelectInfoResponse, function(p24) --[[ Line: 130 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_14, (ref 3): v_u_10 ]]
                p_u_14._menus:push_menu(v_u_10:new(p_u_14, p_u_14._spui, p_u_14._menus, (v_u_5:new():push_back_table_list(p24))))
            end)
            p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientRequestSongSelectInfo)
            return;
        elseif l_None_0 == v_u_13.Mode.ShowInfo then
            p19:sync_playerblob_and_start_lobby(function() --[[ Line: 142 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_14, (ref 3): v_u_3 ]]
                p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientReportTutorialStep, v_u_8.Step.TutorialLoadedIntoLobby)
            end)
        else
            v_u_2:warnf("do_tutorial_stage invalid state(%s)", (tostring(p20)))
            p19:do_tutorial_stage(v_u_13.Mode.ShowInfo)
        end;
    end;
    v15.tutorial_start_do_tutorial = function(p25, p26) --[[ Name: tutorial_start_do_tutorial ]] --[[ Line: 159 ]]
        --[[ Upvalues: (ref 1): l_None_0, (ref 2): v_u_13, (copy 3): p_u_14, (ref 4): v_u_8, (ref 5): v_u_3 ]]
        if p26 == true then
            l_None_0 = v_u_13.Mode.IngameTutorial
            p_u_14._game_join:start_game_tutorial_mode(p_u_14)
            p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientReportTutorialStep, v_u_8.Step.TutorialGameStart)
        else
            p25:do_tutorial_stage(v_u_13.Mode.TutorialSongAcquire)
            p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientReportTutorialStep, v_u_8.Step.TutorialSkipGame)
        end;
    end;
    v15.tutorial_after_song_acquire = function(p27) --[[ Name: tutorial_after_song_acquire ]] --[[ Line: 172 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_4, (ref 3): v_u_13, (ref 4): v_u_2 ]]
        local l_TutorialStage_1 = p_u_14._player_blob_manager:get_player_blob().TutorialStage
        if l_TutorialStage_1 == v_u_4.TutorialStage.TutorialSongAcquired then
            p27:do_tutorial_stage(v_u_13.Mode.SongSelect)
            return;
        elseif l_TutorialStage_1 == v_u_4.TutorialStage.TutorialComplete then
            p27:do_tutorial_stage(v_u_13.Mode.ShowInfo)
        else
            v_u_2:warnf("tutorial_after_song_acquire invalid state(%s)", (tostring(l_TutorialStage_1)))
            p27:do_tutorial_stage(v_u_13.Mode.ShowInfo)
        end;
    end;
    v15.song_select_notify_server = function(p_u_28, p29, p_u_30) --[[ Name: song_select_notify_server ]] --[[ Line: 184 ]]
        --[[ Upvalues: (ref 1): l_None_0, (ref 2): v_u_13, (ref 3): v_u_2, (copy 4): p_u_14, (ref 5): v_u_3 ]]
        if l_None_0 ~= v_u_13.Mode.SongSelect then
            v_u_2:warnf("TutorialManager:song_select_notify_server mode mismatch")
        end;
        p_u_14._evt:wait_on_event_once(v_u_3.EVT_Tutorial_ServerSongSelectSubmitChoicesResponse, function() --[[ Line: 187 ]]
            --[[ Upvalues: (copy 1): p_u_30, (copy 2): p_u_28, (ref 3): v_u_13 ]]
            p_u_30()
            p_u_28:do_tutorial_stage(v_u_13.Mode.ShowInfo)
        end)
        v_u_2:puts("TutorialManager:song_select_notify_server SPRemoteEvent.EVT_Tutorial_ClientSongSelectSubmitChoices")
        p_u_14._evt:fire_event_to_server(v_u_3.EVT_Tutorial_ClientSongSelectSubmitChoices, p29._table)
    end;
    v15.sync_playerblob_and_start_lobby = function(p_u_31, p_u_32, p33) --[[ Name: sync_playerblob_and_start_lobby ]] --[[ Line: 196 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_2, (ref 3): v_u_6, (ref 4): v_u_4 ]]
        if p33 == true then
            if p_u_14._player_blob_manager:is_synced() ~= true then
                v_u_2:warnf("sync_playerblob_and_start_lobby skip_sync but player_blob_manager is not synced, doing sync")
                p_u_14._player_blob_manager:do_sync()
            end;
        else
            p_u_14._player_blob_manager:do_sync()
        end;
        spawn(function() --[[ Line: 207 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_2, (ref 3): v_u_6, (ref 4): v_u_4, (copy 5): p_u_31, (copy 6): p_u_32 ]]
            while p_u_14._player_blob_manager:is_synced() == false do
                v_u_2:puts("TutorialManager.Mode.Debug_EndWaitForPlayerBlobSync wait for sync...")
                v_u_6:thread_sleep(0.1)
            end;
            p_u_14._update_enqueue_fn:enqueue_function(function() --[[ Line: 213 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_4, (ref 3): p_u_31, (ref 4): p_u_32 ]]
                local v34 = p_u_14._player_blob_manager:get_player_blob()
                if v_u_4:is_banned(v34) then
                    p_u_31:show_banned_popup()
                    return;
                elseif v_u_4:has_warning(v34) then
                    p_u_31:show_warning_popup(function() --[[ Line: 218 ]]
                        --[[ Upvalues: (ref 1): p_u_31, (ref 2): p_u_32 ]]
                        p_u_31:show_news_ui_and_start_lobby(p_u_32)
                    end)
                else
                    p_u_31:show_news_ui_and_start_lobby(p_u_32)
                end;
            end, 0)
        end)
    end;
    v15.show_banned_popup = function(_) --[[ Name: show_banned_popup ]] --[[ Line: 228 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_1, (ref 3): v_u_4 ]]
        p_u_14._menus:push_menu(v_u_1:new(p_u_14, p_u_14._spui, p_u_14._menus):set_text("Your account has been locked", v_u_4:get_warning((p_u_14._player_blob_manager:get_player_blob()))):set_close_button_visible(false))
    end;
    v15.show_warning_popup = function(_, p_u_35) --[[ Name: show_warning_popup ]] --[[ Line: 238 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_1, (ref 3): v_u_4, (ref 4): v_u_3 ]]
        p_u_14._menus:push_menu(v_u_1:new(p_u_14, p_u_14._spui, p_u_14._menus):set_text("Warning", v_u_4:get_warning((p_u_14._player_blob_manager:get_player_blob()))):set_on_close_fn(function() --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_3, (copy 3): p_u_35 ]]
            p_u_14._evt:wait_on_event_once(v_u_3.EVT_Warning_ServerAcknowledgeClientMarkAsRead, function() --[[ Line: 245 ]]
                --[[ Upvalues: (ref 1): p_u_14, (ref 2): p_u_35 ]]
                p_u_14._player_blob_manager:do_sync(function() --[[ Line: 246 ]]
                    --[[ Upvalues: (ref 1): p_u_35 ]]
                    p_u_35()
                end)
            end)
            p_u_14._evt:fire_event_to_server(v_u_3.EVT_Warning_ClientMarkAsRead)
        end))
    end;
    v15.show_news_ui_and_start_lobby = function(_, p_u_36) --[[ Name: show_news_ui_and_start_lobby ]] --[[ Line: 289 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_6, (copy 4): p_u_14, (ref 5): v_u_9, (ref 6): l_None_0, (ref 7): v_u_13 ]]
        v_u_7:setup_on_initial_load_lobby()
        v_u_8:set_camera_start()
        v_u_6:ptry(function() --[[ Line: 293 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:set_local_character_visible(false)
            v_u_7:set_lobby_characters_visible(false)
        end)
        p_u_14._menus:push_menu(v_u_9:new(p_u_14, p_u_14._spui, p_u_14._menus, function() --[[ Line: 298 ]]
            --[[ Upvalues: (ref 1): p_u_14, (copy 2): p_u_36, (ref 3): l_None_0, (ref 4): v_u_13 ]]
            p_u_14._lobby_join:setup_lobby(p_u_14)
            p_u_14._lobby_join:start_lobby()
            p_u_14._lobby_join:push_ui_to_lobby(function() --[[ Line: 302 ]]
                --[[ Upvalues: (ref 1): p_u_36, (ref 2): l_None_0, (ref 3): v_u_13 ]]
                if p_u_36 ~= nil then
                    p_u_36()
                end;
                l_None_0 = v_u_13.Mode.None
            end)
        end))
    end;
    return v15;
end;
return v_u_13;
