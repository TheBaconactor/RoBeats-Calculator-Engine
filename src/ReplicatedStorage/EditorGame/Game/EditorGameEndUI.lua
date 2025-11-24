-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.AudioRank)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.BGMManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v_u_9 = require(game.ReplicatedStorage.EditorGame.Data.EditorGamePlayInfo)
local v10 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
v10:require_client(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_16 ]]
    v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_12 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_14 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI)
    v_u_15 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
    v_u_16 = require(game.ReplicatedStorage.EditorGame.UI.CustomMapPreviewUI_Util)
end)
local v17 = {}
local function f_create_game_end_ui(p_u_18, p_u_19, p_u_20, p_u_21) --[[ Name: create_game_end_ui ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_5, (ref 4): v_u_13, (copy 5): v_u_4, (copy 6): v_u_9, (ref 7): v_u_11, (copy 8): v_u_7, (copy 9): v_u_8, (ref 10): v_u_16, (copy 11): v_u_1, (copy 12): v_u_6 ]]
    local _, v22 = p_u_18:es_gamelocal_get_scoremanager():get_score_objs()
    local v_u_23 = v22:get_accuracy()
    if v_u_2:is_dev_build() then
        v_u_3:puts("EditorGameLocal:create_game_end_ui accuracy: %.2f", v_u_23)
    end;
    local v_u_24 = v_u_5:accuracy_to_rank_value(v_u_23)
    local v_u_25, v_u_26, v_u_27, v_u_28, v_u_29 = v22:get_stat_counts()
    local v_u_30 = 0
    return p_u_18._menus:push_menu(v_u_13:new(p_u_18, p_u_18._spui, p_u_18._menus, function(p31) --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): p_u_21 ]]
        p31:set_header_text("Song Finished")
        p31:get_element_list():push_back(1)
        p31:get_element_list():push_back(2)
        if p_u_21:is_rewarded_play() then
            p31:get_element_list():push_back(4)
            p31:get_element_list():push_back(5)
            p31:get_element_list():push_back(6)
            p31:get_element_list():push_back(7)
        end;
    end, function(p32, p33, p34, _, p35) --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_24, (copy 3): v_u_23, (copy 4): v_u_29, (ref 5): v_u_2, (copy 6): v_u_25, (copy 7): v_u_26, (copy 8): v_u_27, (copy 9): v_u_28, (copy 10): p_u_21, (ref 11): v_u_4, (ref 12): v_u_9, (copy 13): p_u_18 ]]
        if p32 == 1 then
            p33.Text = string.format("Rank: %s", v_u_5:get_rank_value_name(v_u_24))
            p34.Image = v_u_5:get_rank_value_icon(v_u_24)
            p35:get_description_display().Text = string.format("Accuracy: %.2f%%", v_u_23 * 100)
            p35:set_select_button_enabled(false)
            return;
        elseif p32 == 2 then
            p33.Text = string.format("Max Combo: %d", v_u_29)
            p34.Image = v_u_2:important_assetid()
            p35:get_description_display().Text = string.format("Perfect: %d - Great: %d - Okay: %d - Miss: %d", v_u_25, v_u_26, v_u_27, v_u_28)
            p35:set_select_button_enabled(false)
            return;
        elseif p32 == 4 then
            p33.Text = "Like Map"
            p34.Image = v_u_2:thumbs_up_assetid()
            if p_u_21:get_load_custom_map_additional_info():has_player_already_liked() then
                p35:get_description_display().Text = "You have already liked this map."
                p35:set_select_button_enabled(false)
            elseif v_u_4.LikeMapMissionPerformAllChecks == true and p_u_21:get_time_played_sec() < v_u_9:get_minimum_reward_time_play_sec() then
                p35:get_description_display().Text = string.format("Must play for at least %d seconds in order to like.", v_u_9:get_minimum_reward_time_play_sec())
                p35:set_select_button_enabled(false)
            else
                p35:get_description_display().Text = "Like this map?"
                p35:set_select_button_enabled(true)
            end;
            p35:set_select_button_text("Like")
            return;
        elseif p32 == 5 then
            p33.Text = "Comment on Map"
            p34.Image = v_u_2:get_hud_button_chat_assetid()
            p35:get_description_display().Text = "Comment on this map."
            p35:set_select_button_enabled(true)
            p35:set_select_button_text("Comment")
            return;
        elseif p32 == 6 then
            p33.Text = "Share Code"
            p34.Image = v_u_2:plus_add_icon_assetid()
            p35:get_description_display().Text = "Share the code for this map."
            p35:set_select_button_enabled(true)
            p35:set_select_button_text("Share")
        elseif p32 == 7 then
            p33.Text = "Play Time"
            p34.Image = v_u_2:get_iconhd_mission()
            local v36 = p_u_21:get_time_played_sec() * 1000
            local v37 = p_u_18:es_gamelocal_get_audiomanager():get_song_length_ms()
            if v37 < v36 then
                v36 = v37
            end;
            p35:get_description_display().Text = string.format("%s / %s", v_u_2:format_ms_time(v36), v_u_2:format_ms_time(v37))
            p35:set_select_button_enabled(false)
            p35:set_select_button_text("View")
        end;
    end, function(p38) --[[ Line: 141 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_18, (ref 3): v_u_7, (ref 4): v_u_8, (copy 5): p_u_21, (copy 6): p_u_19, (ref 7): v_u_16 ]]
        if p38 == nil then
            return;
        elseif p38 == 4 then
            local v_u_39 = v_u_11:loading_menu(p_u_18)
            p_u_18._evt:wait_on_event_once(v_u_7.EVT_Editor_LikeMap_Server, function(p40, p41, p_u_42, p43) --[[ Line: 145 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_11, (copy 3): v_u_39, (ref 4): v_u_8, (ref 5): p_u_21, (ref 6): p_u_19 ]]
                if p40 then
                    local function f_finish() --[[ Name: finish ]] --[[ Line: 152 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_18, (ref 3): v_u_39, (ref 4): v_u_8, (copy 5): p_u_42, (ref 6): p_u_21, (ref 7): p_u_19 ]]
                        v_u_11:remove_loading_menu(p_u_18, v_u_39)
                        local v44 = v_u_8.SavedMapInfo:from_table(p_u_42)
                        p_u_18._menus:push_menu(v_u_11:new(p_u_18, p_u_18._spui, p_u_18._menus):set_text("Success", string.format("Current Like Count: %d", v44:get_like_count())))
                        p_u_21:get_load_custom_map_additional_info():set_player_already_liked(true)
                        p_u_19:set_like_count(v44:get_like_count())
                    end;
                    if p43 then
                        p_u_18._player_blob_manager:do_sync(function(_) --[[ Line: 165 ]]
                            --[[ Upvalues: (copy 1): f_finish ]]
                            f_finish()
                        end)
                    else
                        f_finish()
                    end;
                else
                    p_u_18._menus:push_menu(v_u_11:new(p_u_18, p_u_18._spui, p_u_18._menus):set_text("Error", p41))
                    return;
                end;
            end)
            p_u_18._evt:fire_event_to_server(v_u_7.EVT_Editor_LikeMap_Client, p_u_19:get_custom_map_data_key())
            return;
        elseif p38 == 5 then
            v_u_16:show_map_chat_menu(p_u_18, p_u_19)
        elseif p38 == 6 then
            v_u_16:show_map_share_code_menu(p_u_18, p_u_19)
        end;
    end)):set_close_on_element_select(false):set_refresh_on_refocus(true):add_fn_behaviour_update(function(p45) --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_1, (copy 3): p_u_18, (ref 4): v_u_6 ]]
        local v46 = v_u_30
        v_u_30 = v_u_30 + v_u_1:TimescaleToDeltaTime(p45)
        if v46 < 3.5 and v_u_30 > 3.5 then
            p_u_18._bgm_manager:play_bgm(v_u_6.BGM_SONGEND)
        end;
    end):set_fn_on_remove(function() --[[ Line: 192 ]]
        --[[ Upvalues: (copy 1): p_u_18 ]]
        p_u_18:exit_to_lobby()
    end):set_fn_info_button_pressed(function() --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_18, (copy 3): p_u_19, (copy 4): p_u_20 ]]
        v_u_16:show_map_info_ui(p_u_18, p_u_19, p_u_20)
    end);
end;
v17.load_game_end_ui = function(_, p_u_47, p_u_48, p_u_49, p_u_50) --[[ Name: load_game_end_ui ]] --[[ Line: 203 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_7, (copy 3): v_u_2, (copy 4): v_u_3, (copy 5): v_u_9, (copy 6): f_create_game_end_ui ]]
    if p_u_50:is_rewarded_play() then
        local v_u_51 = v_u_11:loading_menu(p_u_47)
        p_u_47._evt:wait_on_event_once(v_u_7.EVT_EditorGame_ServerResponsePlayEnd, function(p52, p53) --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3, (ref 3): v_u_9, (ref 4): p_u_50, (ref 5): v_u_11, (copy 6): p_u_47, (copy 7): v_u_51, (ref 8): f_create_game_end_ui, (copy 9): p_u_48, (copy 10): p_u_49 ]]
            if v_u_2:is_dev_build() then
                v_u_3:puts("EVT_EditorGame_ClientNotifyPlayStart success(%s) updated_editor_game_play_info_tab(%s)", tostring(p52), v_u_2:table_to_string(p53))
            end;
            local v54 = v_u_9:from_table(p53)
            v_u_9:copy_over_unserialized_data(p_u_50, v54)
            p_u_50 = v54
            v_u_11:remove_loading_menu(p_u_47, v_u_51)
            f_create_game_end_ui(p_u_47, p_u_48, p_u_49, p_u_50)
        end)
        p_u_47._evt:fire_event_to_server(v_u_7.EVT_EditorGame_ClientRequestPlayEnd, p_u_48:to_table())
    else
        f_create_game_end_ui(p_u_47, p_u_48, p_u_49, p_u_50)
    end;
end;
return v17;
