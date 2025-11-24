-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:49 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
require(game.ReplicatedStorage.Shared.GuildMessage)
require(game.ReplicatedStorage.Shared.GuildUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.Black17EventInfo)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v_u_13 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_14 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_16 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v17 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
v17:require_client(function() --[[ Line: 41 ]]
    --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_19, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_22, (ref 6): v_u_23, (ref 7): v_u_24 ]]
    v_u_18 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.PreviewCharacterUI)
    v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
end)
local v_u_59 = {
    ["show_tasks_menu"] = function(_, p25, p_u_26) --[[ Name: show_tasks_menu ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_2, (copy 3): v_u_11 ]]
        p25._menus:push_menu(v_u_20:new(p25, p25._spui, p25._menus, function(p27) --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_11, (copy 3): p_u_26 ]]
            p27:set_header_text(string.format("Tasks"))
            local v28 = v_u_2:new()
            v28:push_back(v_u_11.TaskFlags.Song1Normal)
            v28:push_back(v_u_11.TaskFlags.Song1Hard)
            v28:push_back(v_u_11.TaskFlags.Song2Normal)
            v28:push_back(v_u_11.TaskFlags.Song2Hard)
            v28:push_back(v_u_11.TaskFlags.Song3Normal)
            v28:push_back(v_u_11.TaskFlags.Song3Hard)
            v28:push_back(v_u_11.TaskFlags.Song4Normal)
            v28:push_back(v_u_11.TaskFlags.Song4Hard)
            v28:push_back(v_u_11.TaskFlags.Song5Normal)
            v28:push_back(v_u_11.TaskFlags.Song5Hard)
            v28:push_back(v_u_11.TaskFlags.MultiplayerMatches1)
            v28:push_back(v_u_11.TaskFlags.MultiplayerMatches2)
            v28:push_back(v_u_11.TaskFlags.MultiplayerMatches3)
            v28:push_back(v_u_11.TaskFlags.NoMissNormal)
            v28:push_back(v_u_11.TaskFlags.NoMissHard)
            v28:remove_if(function(p29) --[[ Line: 76 ]]
                --[[ Upvalues: (ref 1): p_u_26 ]]
                return p_u_26:get_task_flag(p29);
            end)
            for _, v30 in v28:key_itr() do
                p27:get_element_list():push_back(v30)
            end;
        end, function(p31, p32, p33, _, p34) --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            p32.Text = v_u_11:get_task_flag_to_name():get(p31)
            p33.Image = v_u_11:get_icon_assetid()
            p34:get_description_display().Text = string.format("%d Points", v_u_11:get_task_flag_to_point_amount():get(p31))
            p34:set_select_button_enabled(false)
        end, function(_) end)):get_list_adapter():set_do_wrap(true)
    end,
    ["show_settings_menu"] = function(_, p_u_35, _, p_u_36, p_u_37) --[[ Name: show_settings_menu ]] --[[ Line: 94 ]]
        --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_1, (ref 3): v_u_18, (copy 4): v_u_7 ]]
        p_u_35._menus:push_menu(v_u_20:new(p_u_35, p_u_35._spui, p_u_35._menus, function(p38) --[[ Line: 100 ]]
            p38:set_header_text(string.format("Settings"))
            p38:get_element_list():push_back(-1)
            p38:get_element_list():push_back(-2)
            p38:get_element_list():push_back(-3)
        end, function(p39, p40, p41, _, p42) --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_36 ]]
            if p39 == -1 then
                p40.Text = "Songs Played (Server)"
                p41.Image = v_u_1:get_question_assetid()
                p42:get_description_display().Text = "Count: " .. tostring(p_u_36.SongCompleteCount)
                p42:set_select_button_enabled(false)
                return;
            elseif p39 == -2 then
                p40.Text = "Multiplayer Songs Played (Server)"
                p41.Image = v_u_1:get_question_assetid()
                p42:get_description_display().Text = "Count: " .. tostring(p_u_36.MultiplayerSongCompleteCount)
                p42:set_select_button_enabled(false)
            elseif p39 == -3 then
                p40.Text = "Reset Data"
                p41.Image = v_u_1:get_question_assetid()
                p42:get_description_display().Text = "Reset all event data."
                p42:set_select_button_text("Reset")
            end;
        end, function(p43) --[[ Line: 124 ]]
            --[[ Upvalues: (copy 1): p_u_35, (ref 2): v_u_18, (ref 3): v_u_7, (copy 4): p_u_37 ]]
            if p43 == -3 then
                p_u_35._menus:push_menu(v_u_18:new(p_u_35, p_u_35._spui, p_u_35._menus):set_text("Confirm", "Are you sure you want to reset your event data?")):set_okay_button_fn(function() --[[ Line: 128 ]]
                    --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_18, (ref 3): v_u_7, (ref 4): p_u_37 ]]
                    local v_u_44 = p_u_35._menus:push_menu(v_u_18:new(p_u_35, p_u_35._spui, p_u_35._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_35._evt:wait_on_event_once(v_u_7.EVT_SpecialEvent_RBGames_ResetData_Server, function() --[[ Line: 130 ]]
                        --[[ Upvalues: (ref 1): p_u_35, (copy 2): v_u_44, (ref 3): p_u_37, (ref 4): v_u_18 ]]
                        p_u_35._menus:remove_menu(v_u_44)
                        p_u_35._menus:remove_menu(p_u_37)
                        p_u_35._menus:push_menu(v_u_18:new(p_u_35, p_u_35._spui, p_u_35._menus):set_text("Data Reset", "Your event data has been reset."):set_close_button_visible(true))
                    end)
                    p_u_35._evt:fire_event_to_server(v_u_7.EVT_SpecialEvent_RBGames_ResetData_Client)
                end)
            end;
        end))
    end,
    ["do_claim_progress_flag"] = function(_, p_u_45, p46, p_u_47) --[[ Name: do_claim_progress_flag ]] --[[ Line: 141 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_11, (ref 3): v_u_18, (copy 4): v_u_7, (copy 5): v_u_10, (ref 6): v_u_22 ]]
        v_u_9:is_enum_member(p46, v_u_11.ProgressFlags)
        local v_u_48 = p_u_45._menus:push_menu(v_u_18:new(p_u_45, p_u_45._spui, p_u_45._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_45._evt:wait_on_event_once(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Server, function(p_u_49, p_u_50, p51) --[[ Line: 145 ]]
            --[[ Upvalues: (copy 1): p_u_47, (ref 2): v_u_10, (copy 3): p_u_45, (copy 4): v_u_48, (ref 5): v_u_22 ]]
            local function _() --[[ Name: finish ]] --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): p_u_47, (copy 2): p_u_49, (copy 3): p_u_50 ]]
                p_u_47(p_u_49, p_u_50)
            end;
            local v_u_52 = v_u_10.RewardInfo:table_to_list(p51)
            if v_u_52:count() > 0 then
                p_u_45._player_blob_manager:do_sync(function() --[[ Line: 152 ]]
                    --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_48, (ref 3): v_u_22, (copy 4): v_u_52, (ref 5): p_u_47, (copy 6): p_u_49, (copy 7): p_u_50 ]]
                    p_u_45._menus:remove_menu(v_u_48)
                    p_u_45._menus:push_menu(v_u_22:new(p_u_45, p_u_45._spui, p_u_45._menus, v_u_52, function() --[[ Line: 155 ]]
                        --[[ Upvalues: (ref 1): p_u_47, (ref 2): p_u_49, (ref 3): p_u_50 ]]
                        p_u_47(p_u_49, p_u_50)
                    end):set_header_text("Rewards"))
                end)
            else
                p_u_45._menus:remove_menu(v_u_48)
                p_u_47(p_u_49, p_u_50)
            end;
        end)
        p_u_45._evt:fire_event_to_server(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Client, p46)
    end,
    ["try_claim_web_integration_rewards"] = function(_, p_u_53) --[[ Name: try_claim_web_integration_rewards ]] --[[ Line: 169 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_7, (copy 3): v_u_10, (ref 4): v_u_22 ]]
        local v_u_54 = p_u_53._menus:push_menu(v_u_18:new(p_u_53, p_u_53._spui, p_u_53._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_53._evt:wait_on_event_once(v_u_7.EVT_SpecialEvent_RBGames_Server_Event1, function(p55, p56, p57) --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_53, (copy 3): v_u_54, (ref 4): v_u_22, (ref 5): v_u_18 ]]
            if p55 then
                local v_u_58 = v_u_10.RewardInfo:table_to_list(p57)
                p_u_53._player_blob_manager:do_sync(function() --[[ Line: 174 ]]
                    --[[ Upvalues: (ref 1): p_u_53, (ref 2): v_u_54, (ref 3): v_u_22, (copy 4): v_u_58 ]]
                    p_u_53._menus:remove_menu(v_u_54)
                    p_u_53._menus:push_menu(v_u_22:new(p_u_53, p_u_53._spui, p_u_53._menus, v_u_58):set_header_text("Rewards"))
                end)
            else
                p_u_53._menus:remove_menu(v_u_54)
                p_u_53._menus:push_menu(v_u_18:new(p_u_53, p_u_53._spui, p_u_53._menus):set_text("Error", p56))
            end;
        end)
        p_u_53._evt:fire_event_to_server(v_u_7.EVT_SpecialEvent_RBGames_Client_Event1)
    end
}
local v_u_60 = 0
local v_u_61 = v_u_11:get_all_songkeys_set():key_list()
v_u_61:sort(function(p62, p63) --[[ Line: 191 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13:singleton():get_difficulty_for_key(p63) - v_u_13:singleton():get_difficulty_for_key(p62);
end)
v_u_59.show_menu = function(_, p_u_64) --[[ Name: show_menu ]] --[[ Line: 195 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_5, (ref 3): v_u_18, (copy 4): v_u_7, (copy 5): v_u_59, (copy 6): v_u_8, (ref 7): v_u_20, (copy 8): v_u_4, (copy 9): v_u_3, (copy 10): v_u_6, (copy 11): v_u_12, (copy 12): v_u_14, (copy 13): v_u_61, (ref 14): v_u_60, (copy 15): v_u_15, (copy 16): v_u_16, (ref 17): v_u_24, (ref 18): v_u_23, (copy 19): v_u_1 ]]
    if v_u_11:day_event_list_playerblob_is_event_active(p_u_64._player_blob_manager:get_day_event_list(), (p_u_64._player_blob_manager:get_player_blob())) ~= true then
        return v_u_5:warnf("Black17EventUI:show_menu() - Event not active.");
    end;
    (function(p_u_65) --[[ Name: get_player_progress_data ]] --[[ Line: 201 ]]
        --[[ Upvalues: (copy 1): p_u_64, (ref 2): v_u_18, (ref 3): v_u_7, (ref 4): v_u_11 ]]
        local v_u_66 = p_u_64._menus:push_menu(v_u_18:new(p_u_64, p_u_64._spui, p_u_64._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_64._evt:wait_on_event_once(v_u_7.EVT_SpecialEvent_RBGames_GetData_Server, function(p67, p68) --[[ Line: 203 ]]
            --[[ Upvalues: (ref 1): p_u_64, (copy 2): v_u_66, (copy 3): p_u_65, (ref 4): v_u_11 ]]
            p_u_64._menus:remove_menu(v_u_66)
            p_u_65(v_u_11.PlayerProgress:from_table(p67), p68)
        end)
        p_u_64._evt:fire_event_to_server(v_u_7.EVT_SpecialEvent_RBGames_GetData_Client)
    end)(function(p_u_69, p_u_70) --[[ Line: 210 ]]
        --[[ Upvalues: (copy 1): p_u_64, (ref 2): v_u_59, (ref 3): v_u_11, (ref 4): v_u_8, (ref 5): v_u_20, (ref 6): v_u_4, (ref 7): v_u_3, (ref 8): v_u_6, (ref 9): v_u_12, (ref 10): v_u_14, (ref 11): v_u_61, (ref 12): v_u_60, (ref 13): v_u_15, (ref 14): v_u_16, (ref 15): v_u_24, (ref 16): v_u_23, (ref 17): v_u_1 ]]
        local v_u_71 = nil
        local function _() --[[ Name: close_and_refresh_menu ]] --[[ Line: 222 ]]
            --[[ Upvalues: (ref 1): v_u_71, (ref 2): p_u_64, (ref 3): v_u_59 ]]
            if v_u_71 then
                p_u_64._menus:remove_menu(v_u_71)
            end;
            v_u_59:show_menu(p_u_64)
        end;
        local function f_opt_quest_ui_helper(p72, _, p73, p74, _, p75) --[[ Name: opt_quest_ui_helper ]] --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_69 ]]
            p73.Text = string.format("Mission #%d", p72 + 1)
            p74.Image = v_u_11:get_icon_assetid()
            if p_u_69:get_progress_flag(p72) == true then
                p75:get_description_display().Text = "Mission Complete!"
                p75:set_select_button_text("Claimed")
            else
                p75:get_description_display().Text = v_u_11:get_progress_flag_to_description():get(p72)
                p75:set_select_button_text("Claim")
            end;
            return v_u_11:player_progress_can_claim_event_flag(p_u_69, p72);
        end;
        local v_u_76 = nil
        p_u_64:set_character_random_position_around_anchors_fn(function() --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8:get_lobby_anchors().Event.StandAnchor, v_u_8:get_lobby_anchors().Event.LookAnchor;
        end)
        p_u_64:transition_local_camera_to_anchors_fn(function() --[[ Line: 248 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8:get_lobby_anchors().Event.CameraAnchor, v_u_8:get_lobby_anchors().Event.LookAnchor;
        end)
        local _ = p_u_64._menus:push_menu(v_u_20:new(p_u_64, p_u_64._spui, p_u_64._menus, function(p77) --[[ Line: 254 ]]
            --[[ Upvalues: (copy 1): p_u_69, (ref 2): v_u_11, (ref 3): v_u_76, (ref 4): p_u_64, (ref 5): v_u_4, (ref 6): v_u_3, (ref 7): v_u_6, (ref 8): v_u_12, (ref 9): v_u_14, (ref 10): v_u_61, (ref 11): v_u_60, (ref 12): v_u_15, (ref 13): v_u_16, (ref 14): v_u_24, (ref 15): v_u_23 ]]
            p77:set_sub_text("Complete missions and earn limited-time rewards!")
            p77:get_element_list():push_back(-7)
            p77:get_element_list():push_back(-1)
            if p_u_69:get_progress_flag(v_u_11.ProgressFlags.PlayAnySong) == true then
                p77:get_element_list():push_back(-2)
                if p_u_69:get_progress_flag(v_u_11.ProgressFlags.EarnPoints1) == true then
                    p77:get_element_list():push_back(-3)
                    if p_u_69:get_progress_flag(v_u_11.ProgressFlags.EarnPoints2) == true then
                        p77:get_element_list():push_back(-4)
                        if p_u_69:get_progress_flag(v_u_11.ProgressFlags.EarnPoints3) == true then
                            p77:get_element_list():push_back(-5)
                            if p_u_69:get_progress_flag(v_u_11.ProgressFlags.EarnPoints4) == true then
                                p77:get_element_list():push_back(-6)
                            end;
                        end;
                    end;
                end;
            end;
            p77:get_element_list():push_back(-8)
            if v_u_76 == nil then
                local v78 = p77:get_obj()
                local v_u_79 = p77:add_cycle_element(p_u_64, 1, v_u_4:new(v_u_3:new(p77, v78.PrimaryPart, v78.ArrowLeft), p_u_64._spui, function() --[[ Line: 283 ]]
                    --[[ Upvalues: (ref 1): p_u_64, (ref 2): v_u_6, (ref 3): v_u_76 ]]
                    p_u_64._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    v_u_76:prev_page()
                end))
                local v_u_80 = p77:add_cycle_element(p_u_64, 1, v_u_4:new(v_u_3:new(p77, v78.PrimaryPart, v78.ArrowRight), p_u_64._spui, function() --[[ Line: 292 ]]
                    --[[ Upvalues: (ref 1): p_u_64, (ref 2): v_u_6, (ref 3): v_u_76 ]]
                    p_u_64._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    v_u_76:next_page()
                end))
                local v_u_81 = v_u_12:new(p_u_64, v78.SongElementDisplay, v_u_3:new(p77, v78.PrimaryPart, v78.SongElementDisplay.PrimaryPart))
                v_u_76 = v_u_14:new():set_fn_get_data_list(function() --[[ Line: 305 ]]
                    --[[ Upvalues: (ref 1): v_u_61 ]]
                    return v_u_61;
                end):set_fn_set_element_data(function(p82, p83) --[[ Line: 308 ]]
                    --[[ Upvalues: (ref 1): p_u_64 ]]
                    p82:display_song(p83)
                    p_u_64._bgm_manager:preview_songkey(p83)
                end):set_fn_next_prev_visible(function(p84, p85) --[[ Line: 312 ]]
                    --[[ Upvalues: (copy 1): v_u_80, (copy 2): v_u_79 ]]
                    v_u_80:set_visible(p84)
                    v_u_79:set_visible(p85)
                end):set_fn_update_page_display(function(_, _) end):set_do_wrap(true):set_i_offset(v_u_60):set_fn_store_i_offset(function(p86) --[[ Line: 320 ]]
                    --[[ Upvalues: (ref 1): v_u_60 ]]
                    v_u_60 = p86
                end)
                v_u_76:push_display_element(v_u_81)
                v_u_76:page_update()
                p77:add_fn_on_layout(function() --[[ Line: 326 ]]
                    --[[ Upvalues: (ref 1): v_u_76 ]]
                    v_u_76:layout()
                end)
                p77:set_fn_on_remove(function() --[[ Line: 329 ]]
                    --[[ Upvalues: (ref 1): p_u_64 ]]
                    p_u_64._bgm_manager:stop_song_preview()
                end)
                p77:add_cycle_element(p_u_64, 1, v_u_4:new(v_u_3:new(p77, v78.PrimaryPart, v78.PlayButton), p_u_64._spui, function() --[[ Line: 336 ]]
                    --[[ Upvalues: (ref 1): p_u_64, (ref 2): v_u_6, (ref 3): v_u_15, (ref 4): v_u_16, (ref 5): v_u_24, (ref 6): v_u_11, (ref 7): v_u_23, (copy 8): v_u_81 ]]
                    p_u_64._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                    p_u_64._game_join_protocol:set_event_info(v_u_15.EventMission.Black17Event)
                    if p_u_64._player_settings_manager:get_key(v_u_16.Key.ArtistEventUseStage) == true then
                        v_u_24:artist_event_set_custom_stage_id(v_u_11:get_stage_id())
                    end;
                    p_u_64._menus:push_menu(v_u_23:new(p_u_64, p_u_64._spui, p_u_64._menus, v_u_81:get_element_data()))
                end))
                p77:add_cycle_element(p_u_64, 1, v_u_4:new(v_u_3:new(p77, v78.PrimaryPart, v78.SongInfoButton), p_u_64._spui, function() --[[ Line: 354 ]]
                    --[[ Upvalues: (ref 1): p_u_64, (ref 2): v_u_6, (ref 3): v_u_12, (copy 4): v_u_81 ]]
                    p_u_64._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    v_u_12:show_song_info_popup(p_u_64, v_u_81:get_element_data())
                end))
            end;
        end, function(p87, p88, p89, p90, p91) --[[ Line: 364 ]]
            --[[ Upvalues: (copy 1): f_opt_quest_ui_helper, (ref 2): v_u_11, (copy 3): p_u_69, (ref 4): v_u_1 ]]
            p89.ImageRectOffset = Vector2.new(0, 0)
            p89.ImageRectSize = Vector2.new(0, 0)
            local v92 = true
            if p87 == -1 then
                v92 = f_opt_quest_ui_helper(v_u_11.ProgressFlags.PlayAnySong, p87, p88, p89, p90, p91)
            elseif p87 == -2 then
                v92 = f_opt_quest_ui_helper(v_u_11.ProgressFlags.EarnPoints1, p87, p88, p89, p90, p91)
            elseif p87 == -3 then
                v92 = f_opt_quest_ui_helper(v_u_11.ProgressFlags.EarnPoints2, p87, p88, p89, p90, p91)
            elseif p87 == -4 then
                v92 = f_opt_quest_ui_helper(v_u_11.ProgressFlags.EarnPoints3, p87, p88, p89, p90, p91)
            elseif p87 == -5 then
                v92 = f_opt_quest_ui_helper(v_u_11.ProgressFlags.EarnPoints4, p87, p88, p89, p90, p91)
            elseif p87 == -6 then
                v92 = f_opt_quest_ui_helper(v_u_11.ProgressFlags.PlayEverySong, p87, p88, p89, p90, p91)
            elseif p87 == -7 then
                p88.Text = string.format("Tasks (Points: %d)", p_u_69:calculate_task_points())
                p89.Image = v_u_1:important_assetid()
                p91:get_description_display().Text = "Complete tasks to earn points!"
                p91:set_select_button_text("View")
            elseif p87 == -9 then
                p88.Text = "Claim rewards for following!"
                p89.Image = "rbxassetid://92570997520575"
                p91:get_description_display().Text = "Earn rewards by following the artists! Check our social media for more info."
                p91:set_select_button_text("Check")
            elseif p87 == -8 then
                p88.Text = "Settings"
                p89.Image = v_u_1:gear_assetid()
                p91:get_description_display().Text = ""
                p91:set_select_button_text("View")
            end;
            p91:set_select_button_enabled(v92)
        end, function(p93) --[[ Line: 408 ]]
            --[[ Upvalues: (ref 1): v_u_59, (ref 2): p_u_64, (ref 3): v_u_11, (ref 4): v_u_71, (copy 5): p_u_69, (copy 6): p_u_70 ]]
            if p93 == -1 then
                v_u_59:do_claim_progress_flag(p_u_64, v_u_11.ProgressFlags.PlayAnySong, function() --[[ Line: 410 ]]
                    --[[ Upvalues: (ref 1): v_u_71, (ref 2): p_u_64, (ref 3): v_u_59 ]]
                    if v_u_71 then
                        p_u_64._menus:remove_menu(v_u_71)
                    end;
                    v_u_59:show_menu(p_u_64)
                end)
                return;
            elseif p93 == -2 then
                v_u_59:do_claim_progress_flag(p_u_64, v_u_11.ProgressFlags.EarnPoints1, function() --[[ Line: 412 ]]
                    --[[ Upvalues: (ref 1): v_u_71, (ref 2): p_u_64, (ref 3): v_u_59 ]]
                    if v_u_71 then
                        p_u_64._menus:remove_menu(v_u_71)
                    end;
                    v_u_59:show_menu(p_u_64)
                end)
                return;
            elseif p93 == -3 then
                v_u_59:do_claim_progress_flag(p_u_64, v_u_11.ProgressFlags.EarnPoints2, function() --[[ Line: 414 ]]
                    --[[ Upvalues: (ref 1): v_u_71, (ref 2): p_u_64, (ref 3): v_u_59 ]]
                    if v_u_71 then
                        p_u_64._menus:remove_menu(v_u_71)
                    end;
                    v_u_59:show_menu(p_u_64)
                end)
                return;
            elseif p93 == -4 then
                v_u_59:do_claim_progress_flag(p_u_64, v_u_11.ProgressFlags.EarnPoints3, function() --[[ Line: 416 ]]
                    --[[ Upvalues: (ref 1): v_u_71, (ref 2): p_u_64, (ref 3): v_u_59 ]]
                    if v_u_71 then
                        p_u_64._menus:remove_menu(v_u_71)
                    end;
                    v_u_59:show_menu(p_u_64)
                end)
                return;
            elseif p93 == -5 then
                v_u_59:do_claim_progress_flag(p_u_64, v_u_11.ProgressFlags.EarnPoints4, function() --[[ Line: 418 ]]
                    --[[ Upvalues: (ref 1): v_u_71, (ref 2): p_u_64, (ref 3): v_u_59 ]]
                    if v_u_71 then
                        p_u_64._menus:remove_menu(v_u_71)
                    end;
                    v_u_59:show_menu(p_u_64)
                end)
                return;
            elseif p93 == -6 then
                v_u_59:do_claim_progress_flag(p_u_64, v_u_11.ProgressFlags.PlayEverySong, function() --[[ Line: 420 ]]
                    --[[ Upvalues: (ref 1): v_u_71, (ref 2): p_u_64, (ref 3): v_u_59 ]]
                    if v_u_71 then
                        p_u_64._menus:remove_menu(v_u_71)
                    end;
                    v_u_59:show_menu(p_u_64)
                end)
                return;
            elseif p93 == -7 then
                v_u_59:show_tasks_menu(p_u_64, p_u_69)
                return;
            elseif p93 == -9 then
                v_u_59:try_claim_web_integration_rewards(p_u_64)
            elseif p93 == -8 then
                v_u_59:show_settings_menu(p_u_64, p_u_69, p_u_70, v_u_71)
            end;
        end, function(_, _, _) end, game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.Black17EventUI:Clone()):set_close_on_element_select(false):use_r_set_alpha_v2(true):set_do_not_update_while_camera_transitioning(true))
    end)
end;
return v_u_59;
