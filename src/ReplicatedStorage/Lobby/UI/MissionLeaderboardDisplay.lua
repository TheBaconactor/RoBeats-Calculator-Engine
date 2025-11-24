-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_8 = require(game.ReplicatedStorage.Shared.MissionType)
local v_u_9 = require(game.ReplicatedStorage.Shared.Mission.MissionLeaderboardEntry)
local v_u_10 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
local v_u_12 = require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
v14:require_client(function() --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17 ]]
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_17 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
local v18 = {}
local function f_show_leaderboard_entry_ui(p19, p_u_20, p_u_21) --[[ Name: show_leaderboard_entry_ui ]] --[[ Line: 36 ]]
    --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_1 ]]
    p19._menus:push_menu(v_u_15:new(p19, p19._spui, p19._menus, function(p22) --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_21, (copy 3): p_u_20 ]]
        p22:set_header_text(string.format("%s Place", v_u_1:num_placify(p_u_21)))
        p22:get_element_list():push_back_from_list(p_u_20:get_players_list())
    end, function(p23, p24, p_u_25, _, p26, _) --[[ Line: 45 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        p24.Text = p23:get_name()
        v_u_1:get_user_thumbnail(p23:get_id(), function(p27, _) --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): p_u_25 ]]
            if p_u_25 ~= nil then
                p_u_25.Image = p27
            end;
        end, false)
        p26:get_description_display().Text = string.format("Score: %s, Gear Power: %s", v_u_1:comma_value(p23:get_score()), v_u_1:comma_value(p23:get_gear_power()))
        p26:set_select_button_enabled(false)
    end, function() end))
end;
local function f_load_leaderboard_data_for_mission_data(p_u_28, p29, p30, p_u_31) --[[ Name: load_leaderboard_data_for_mission_data ]] --[[ Line: 58 ]]
    --[[ Upvalues: (ref 1): v_u_17, (copy 2): v_u_6, (copy 3): v_u_9 ]]
    local v_u_32 = p_u_28._menus:push_menu(v_u_17:new(p_u_28, p_u_28._spui, p_u_28._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_28._evt:wait_on_event_once(v_u_6.EVT_Mission_ServerRequestMissionLeaderboardDataResponse, function(_, p33) --[[ Line: 64 ]]
        --[[ Upvalues: (copy 1): p_u_28, (copy 2): v_u_32, (copy 3): p_u_31, (ref 4): v_u_9 ]]
        p_u_28._menus:remove_menu(v_u_32)
        p_u_31(v_u_9:table_to_list(p33))
    end)
    p_u_28._evt:fire_event_to_server(v_u_6.EVT_Mission_ClientRequestMissionLeaderboardData, p30, p29:get_target_song(), p_u_28._player_blob_manager:get_week_id())
end;
local l_TotalScore_0 = v_u_9.LeaderboardType.TotalScore
local v_u_34 = nil
local function f_list_select_ui_bind_load_data_to_filter_buttons(p_u_35, p_u_36, p_u_37) --[[ Name: list_select_ui_bind_load_data_to_filter_buttons ]] --[[ Line: 79 ]]
    --[[ Upvalues: (copy 1): v_u_2, (ref 2): l_TotalScore_0, (copy 3): v_u_3, (copy 4): v_u_9, (ref 5): v_u_34, (copy 6): v_u_4, (copy 7): v_u_13, (copy 8): v_u_12 ]]
    p_u_37:set_settings_section_visible()
    local v_u_38 = v_u_2:new()
    local function f_update_filter_toggles() --[[ Name: update_filter_toggles ]] --[[ Line: 84 ]]
        --[[ Upvalues: (copy 1): v_u_38, (ref 2): l_TotalScore_0, (copy 3): p_u_37 ]]
        for v39, v40 in v_u_38:key_itr() do
            v40:set_toggle(v39 == l_TotalScore_0)
        end;
        p_u_37:get_list_adapter():reset()
    end;
    local v45 = v_u_3:new():push_back_table_list({ function(p41) --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): l_TotalScore_0, (copy 3): p_u_35, (copy 4): p_u_37, (ref 5): v_u_34, (copy 6): p_u_36, (ref 7): v_u_4, (copy 8): v_u_38 ]]
            local l_TotalScore_1 = v_u_9.LeaderboardType.TotalScore
            p41:bind_data(function() --[[ Line: 94 ]]
                --[[ Upvalues: (ref 1): l_TotalScore_0, (copy 2): l_TotalScore_1, (ref 3): p_u_35, (ref 4): p_u_37, (ref 5): v_u_34, (ref 6): p_u_36 ]]
                l_TotalScore_0 = l_TotalScore_1
                p_u_35._menus:remove_menu(p_u_37)
                v_u_34(p_u_35, p_u_36, l_TotalScore_0)
            end)
            v_u_4:set_button_text(p41, v_u_9.LeaderboardType:type_to_name(l_TotalScore_1))
            v_u_38:add(l_TotalScore_1, v_u_4:button_bind_anim_toggle(p41, function() --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): p_u_37 ]]
                return p_u_37:get_alpha();
            end))
        end, function(p42) --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): l_TotalScore_0, (copy 3): p_u_35, (copy 4): p_u_37, (ref 5): v_u_34, (copy 6): p_u_36, (ref 7): v_u_4, (copy 8): v_u_38 ]]
            local l_GearPower_0 = v_u_9.LeaderboardType.GearPower
            p42:bind_data(function() --[[ Line: 104 ]]
                --[[ Upvalues: (ref 1): l_TotalScore_0, (copy 2): l_GearPower_0, (ref 3): p_u_35, (ref 4): p_u_37, (ref 5): v_u_34, (ref 6): p_u_36 ]]
                l_TotalScore_0 = l_GearPower_0
                p_u_35._menus:remove_menu(p_u_37)
                v_u_34(p_u_35, p_u_36, l_TotalScore_0)
            end)
            v_u_4:set_button_text(p42, v_u_9.LeaderboardType:type_to_name(l_GearPower_0))
            v_u_38:add(l_GearPower_0, v_u_4:button_bind_anim_toggle(p42, function() --[[ Line: 110 ]]
                --[[ Upvalues: (ref 1): p_u_37 ]]
                return p_u_37:get_alpha();
            end))
        end, function(p43) --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_35, (ref 3): v_u_12, (ref 4): v_u_4 ]]
            p43:bind_data(function() --[[ Line: 113 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): p_u_35, (ref 3): v_u_12 ]]
                v_u_13:show_chat_menu(p_u_35, v_u_12.Category.CurrentWeeklyMissionLeaderboard, "", function(p44, _) --[[ Line: 114 ]]
                    --[[ Upvalues: (ref 1): p_u_35 ]]
                    p44:set_header_text(string.format("Mission Leaderboard Chat (Current Week - %d)", p_u_35._player_blob_manager:get_week_id()))
                end)
            end)
            v_u_4:set_button_text(p43, "\240\159\146\172 Chat")
        end })
    for _, v46 in p_u_37:get_settings_buttons():key_itr() do
        if v45:count() > 0 then
            v46:set_visible(true)
            v45:pop_front()(v46)
        else
            v46:set_visible(false)
        end;
    end;
    f_update_filter_toggles()
end;
local function f_show_mission_leaderboard(p_u_47, p_u_48, p_u_49, p50) --[[ Name: show_mission_leaderboard ]] --[[ Line: 136 ]]
    --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_9, (ref 3): l_TotalScore_0, (copy 4): v_u_5, (copy 5): v_u_1, (copy 6): f_show_leaderboard_entry_ui ]]
    local v_u_51 = nil
    v_u_51 = p_u_47._menus:push_menu(v_u_15:new(p_u_47, p_u_47._spui, p_u_47._menus, function(p52) --[[ Line: 142 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): l_TotalScore_0, (ref 3): v_u_5, (copy 4): p_u_48, (copy 5): p_u_49 ]]
        p52:set_header_text(string.format("Leaderboard: %s", v_u_9.LeaderboardType:type_to_name(l_TotalScore_0)))
        p52:set_sub_text(string.format("Song: %s", v_u_5:singleton():get_title_for_key(p_u_48:get_target_song())))
        p52:get_list_adapter():set_do_wrap(true)
        for _, v53 in p_u_49:key_itr() do
            p52:get_element_list():push_back(v53)
        end;
    end, function(p54, p55, p_u_56, _, p57, p58) --[[ Line: 150 ]]
        --[[ Upvalues: (ref 1): l_TotalScore_0, (ref 2): v_u_9, (ref 3): v_u_1 ]]
        if l_TotalScore_0 == v_u_9.LeaderboardType.TotalScore then
            p55.Text = string.format("%s - Total Score: %s", v_u_1:num_placify(p58), v_u_1:comma_value(p54:get_calculated_total_score()))
        elseif l_TotalScore_0 == v_u_9.LeaderboardType.GearPower then
            p55.Text = string.format("%s - Total Gear Power: %s", v_u_1:num_placify(p58), v_u_1:comma_value(p54:get_calculated_total_gear_power()))
        end;
        local v59 = p54:get_players_list()
        if v59:count() > 0 then
            v_u_1:get_user_thumbnail(p54:get_top_player_by_leaderboard_type(l_TotalScore_0):get_id(), function(p60, _) --[[ Line: 159 ]]
                --[[ Upvalues: (copy 1): p_u_56 ]]
                if p_u_56 ~= nil then
                    p_u_56.Image = p60
                end;
            end, false)
        end;
        local v61 = ""
        for _, v62 in v59:key_itr() do
            if v61 ~= "" then
                v61 = v61 .. ", "
            end;
            v61 = v61 .. v62:get_name()
        end;
        p57:get_description_display().Text = string.format("%s", v61)
    end, function(p63) --[[ Line: 173 ]]
        --[[ Upvalues: (ref 1): v_u_51, (ref 2): f_show_leaderboard_entry_ui, (copy 3): p_u_47 ]]
        if p63 ~= nil then
            f_show_leaderboard_entry_ui(p_u_47, p63, (v_u_51:get_element_list():find(p63)))
        end;
    end)):set_close_on_element_select(false)
    if p50 then
        p50(p_u_47, p_u_48, v_u_51)
    end;
end;
v_u_34 = function(p_u_64, p_u_65, p66) --[[ Line: 186 ]]
    --[[ Upvalues: (copy 1): f_load_leaderboard_data_for_mission_data, (copy 2): f_show_mission_leaderboard, (copy 3): f_list_select_ui_bind_load_data_to_filter_buttons ]]
    f_load_leaderboard_data_for_mission_data(p_u_64, p_u_65, p66, function(p67) --[[ Line: 187 ]]
        --[[ Upvalues: (ref 1): f_show_mission_leaderboard, (copy 2): p_u_64, (copy 3): p_u_65, (ref 4): f_list_select_ui_bind_load_data_to_filter_buttons ]]
        f_show_mission_leaderboard(p_u_64, p_u_65, p67, f_list_select_ui_bind_load_data_to_filter_buttons)
    end)
end
local function f_show_check_previous_week_results_ui(p_u_68) --[[ Name: show_check_previous_week_results_ui ]] --[[ Line: 192 ]]
    --[[ Upvalues: (ref 1): v_u_17, (copy 2): v_u_6, (copy 3): v_u_9, (ref 4): v_u_15, (copy 5): v_u_5, (copy 6): v_u_11, (copy 7): v_u_8, (ref 8): l_TotalScore_0, (copy 9): f_show_mission_leaderboard, (copy 10): v_u_3, (copy 11): v_u_13, (copy 12): v_u_12, (copy 13): v_u_4, (ref 14): v_u_16, (copy 15): v_u_10, (copy 16): v_u_1 ]]
    local v_u_69 = p_u_68._menus:push_menu(v_u_17:new(p_u_68, p_u_68._spui, p_u_68._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_68._evt:wait_on_event_once(v_u_6.EVT_Mission_ServerClaimMissionLeaderboardRewardResponse, function(p70, p_u_71, p_u_72, p_u_73, p_u_74, p_u_75) --[[ Line: 197 ]]
        --[[ Upvalues: (copy 1): p_u_68, (copy 2): v_u_69, (ref 3): v_u_9, (ref 4): v_u_15, (ref 5): v_u_5, (ref 6): v_u_11, (ref 7): v_u_8, (ref 8): l_TotalScore_0, (ref 9): f_show_mission_leaderboard, (ref 10): v_u_3, (ref 11): v_u_13, (ref 12): v_u_12, (ref 13): v_u_4, (ref 14): v_u_16, (ref 15): v_u_10, (ref 16): v_u_1 ]]
        local function f_next() --[[ Name: next ]] --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): p_u_68, (ref 2): v_u_69, (ref 3): v_u_9, (copy 4): p_u_75, (ref 5): v_u_15, (ref 6): v_u_5, (ref 7): v_u_11, (ref 8): v_u_8, (ref 9): l_TotalScore_0, (ref 10): f_show_mission_leaderboard, (ref 11): v_u_3, (ref 12): v_u_13, (ref 13): v_u_12, (ref 14): v_u_4 ]]
            p_u_68._menus:remove_menu(v_u_69)
            local v_u_76 = v_u_9.LeaderboardInfo:table_to_list(p_u_75)
            local v84 = p_u_68._menus:push_menu(v_u_15:new(p_u_68, p_u_68._spui, p_u_68._menus, function(p77) --[[ Line: 213 ]]
                --[[ Upvalues: (copy 1): v_u_76 ]]
                p77:set_header_text("Previous Week Results")
                p77:get_element_list():push_back_from_list(v_u_76)
            end, function(p78, p79, p80, _, p81) --[[ Line: 217 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_9 ]]
                p79.Text = string.format("Leaderboard: %s", v_u_5:singleton():get_title_for_key(p78:get_song_key()))
                p81:get_description_display().Text = v_u_9.LeaderboardType:type_to_name(p78:get_leaderboard_type())
                p80.Image = v_u_5:singleton():get_coverimage_assetid_for_key(p78:get_song_key())
            end, function(p82) --[[ Line: 225 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_8, (ref 3): l_TotalScore_0, (ref 4): f_show_mission_leaderboard, (ref 5): p_u_68 ]]
                if p82 ~= nil then
                    local v83 = v_u_11.MissionData:new(-1)
                    v83:set_type(v_u_8.PointTotal)
                    v83:set_target_song(p82:get_song_key())
                    l_TotalScore_0 = p82:get_leaderboard_type()
                    f_show_mission_leaderboard(p_u_68, v83, p82:get_entry_list())
                end;
            end)):set_close_on_element_select(false)
            v84:set_settings_section_visible()
            local v88 = v_u_3:new():push_back_table_list({ function(p85) --[[ Line: 239 ]]
                    --[[ Upvalues: (ref 1): v_u_13, (ref 2): p_u_68, (ref 3): v_u_12, (ref 4): v_u_4 ]]
                    p85:bind_data(function() --[[ Line: 240 ]]
                        --[[ Upvalues: (ref 1): v_u_13, (ref 2): p_u_68, (ref 3): v_u_12 ]]
                        v_u_13:show_chat_menu(p_u_68, v_u_12.Category.LastWeeklyMissionLeaderboard, "", function(p86, p87) --[[ Line: 241 ]]
                            --[[ Upvalues: (ref 1): p_u_68 ]]
                            p86:set_header_text(string.format("Mission Leaderboard Archive (Last Week - %d)", p_u_68._player_blob_manager:get_week_id() - 1))
                            p87.NoChatButton = true
                        end)
                    end)
                    v_u_4:set_button_text(p85, "\240\159\146\172 View Messages")
                end })
            for _, v89 in v84:get_settings_buttons():key_itr() do
                if v88:count() > 0 then
                    v89:set_visible(true)
                    v88:pop_front()(v89)
                else
                    v89:set_visible(false)
                end;
            end;
        end;
        if p70 == true then
            p_u_68._player_blob_manager:do_sync(function() --[[ Line: 263 ]]
                --[[ Upvalues: (copy 1): f_next, (ref 2): p_u_68, (ref 3): v_u_16, (ref 4): v_u_10, (copy 5): p_u_74, (ref 6): v_u_1, (copy 7): p_u_71, (ref 8): v_u_9, (copy 9): p_u_73, (ref 10): v_u_5, (copy 11): p_u_72 ]]
                f_next()
                p_u_68._menus:push_menu(v_u_16:new(p_u_68, p_u_68._spui, p_u_68._menus, v_u_10.RewardInfo:table_to_list(p_u_74)):set_header_text("Rewards Acquired!"):set_sub_text(string.format("For placing %s in last week\'s \"%s\" leaderboard for \"%s\", you got...", v_u_1:num_placify(p_u_71), v_u_9.LeaderboardType:type_to_name(p_u_73), v_u_5:singleton():get_title_for_key(p_u_72))))
            end)
        else
            f_next()
        end;
    end)
    p_u_68._evt:fire_event_to_server(v_u_6.EVT_Mission_ClientClaimMissionLeaderboardReward)
end;
v18.show_mission_leaderboards_ui = function(_, p_u_90) --[[ Name: show_mission_leaderboards_ui ]] --[[ Line: 283 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_17, (copy 3): v_u_7, (copy 4): v_u_8, (copy 5): v_u_5, (copy 6): v_u_1, (copy 7): f_show_check_previous_week_results_ui, (copy 8): f_load_leaderboard_data_for_mission_data, (ref 9): l_TotalScore_0, (copy 10): f_show_mission_leaderboard, (copy 11): f_list_select_ui_bind_load_data_to_filter_buttons, (copy 12): v_u_3, (copy 13): v_u_13, (copy 14): v_u_12, (copy 15): v_u_4 ]]
    local v98 = p_u_90._menus:push_menu(v_u_15:new(p_u_90, p_u_90._spui, p_u_90._menus, function(p91) --[[ Line: 290 ]]
        --[[ Upvalues: (copy 1): p_u_90, (ref 2): v_u_17, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_5 ]]
        p91:set_header_text("Weekly Mission Leaderboards")
        p91:set_sub_text("Top performances on this week\'s missions.")
        p91:set_fn_info_button_pressed(function() --[[ Line: 293 ]]
            --[[ Upvalues: (ref 1): p_u_90, (ref 2): v_u_17 ]]
            p_u_90._menus:push_menu(v_u_17:new(p_u_90, p_u_90._spui, p_u_90._menus):set_text("Weekly Mission Leaderboards", "Top performances from groups that completed this week\'s weekly missions. Performances are ranked by highest overall score and lowest overall gear power."))
        end)
        for _, v92 in p_u_90._player_blob_manager:get_server_mission_active_data():get_mission_list_for_timeframe(v_u_7.Weekly):key_itr() do
            if v92:get_type() == v_u_8.PointTotal and v_u_5:singleton():contains_key(v92:get_target_song()) then
                p91:get_element_list():push_back(v92)
            end;
        end;
        p91:get_element_list():push_back(-1)
    end, function(p93, p94, p95, _, _) --[[ Line: 306 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_5 ]]
        if p93 == -1 then
            p94.Text = "Check Last Week\'s Results"
            p95.Image = v_u_1:important_assetid()
        else
            p94.Text = string.format("Leaderboard: %s", v_u_5:singleton():get_title_for_key(p93:get_target_song()))
            p95.Image = v_u_5:singleton():get_coverimage_assetid_for_key(p93:get_target_song())
        end;
    end, function(p_u_96) --[[ Line: 315 ]]
        --[[ Upvalues: (ref 1): f_show_check_previous_week_results_ui, (copy 2): p_u_90, (ref 3): f_load_leaderboard_data_for_mission_data, (ref 4): l_TotalScore_0, (ref 5): f_show_mission_leaderboard, (ref 6): f_list_select_ui_bind_load_data_to_filter_buttons ]]
        if p_u_96 == nil then
            return;
        elseif p_u_96 == -1 then
            f_show_check_previous_week_results_ui(p_u_90)
        else
            f_load_leaderboard_data_for_mission_data(p_u_90, p_u_96, l_TotalScore_0, function(p97) --[[ Line: 320 ]]
                --[[ Upvalues: (ref 1): f_show_mission_leaderboard, (ref 2): p_u_90, (copy 3): p_u_96, (ref 4): f_list_select_ui_bind_load_data_to_filter_buttons ]]
                f_show_mission_leaderboard(p_u_90, p_u_96, p97, f_list_select_ui_bind_load_data_to_filter_buttons)
            end)
        end;
    end)):set_close_on_element_select(false)
    v98:set_settings_section_visible()
    local v101 = v_u_3:new():push_back_table_list({ function(p99) --[[ Line: 330 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_90, (ref 3): v_u_12, (ref 4): v_u_4 ]]
            p99:bind_data(function() --[[ Line: 331 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): p_u_90, (ref 3): v_u_12 ]]
                v_u_13:show_chat_menu(p_u_90, v_u_12.Category.CurrentWeeklyMissionLeaderboard, "", function(p100, _) --[[ Line: 332 ]]
                    --[[ Upvalues: (ref 1): p_u_90 ]]
                    p100:set_header_text(string.format("Mission Leaderboard Chat (Current Week - %d)", p_u_90._player_blob_manager:get_week_id()))
                end)
            end)
            v_u_4:set_button_text(p99, "\240\159\146\172 Chat")
        end })
    for _, v102 in v98:get_settings_buttons():key_itr() do
        if v101:count() > 0 then
            v102:set_visible(true)
            v101:pop_front()(v102)
        else
            v102:set_visible(false)
        end;
    end;
end;
return v18;
