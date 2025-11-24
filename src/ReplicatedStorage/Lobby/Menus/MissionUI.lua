-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.MissionDisplayElement)
local v_u_11 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
local v_u_12 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.MissionCompleteUI)
local v_u_14 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_15 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_16 = require(game.ReplicatedStorage.Lobby.Dialogue.MissionDialogue)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_17 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_19 = require(game.ReplicatedStorage.Tutorial.GearCraftingTutorialInfo)
local v_u_20 = require(game.ReplicatedStorage.Tutorial.Menus.GearCraftingTutorialUI)
local v_u_21 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_22 = require(game.ReplicatedStorage.Shared.HUDNotification)
require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
local v_u_23 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_24 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_25 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
local v_u_26 = require(game.ReplicatedStorage.Lobby.UI.MissionLeaderboardDisplay)
local v_u_27 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_28 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
local v29 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_30 = nil
local v_u_31 = nil
v29:require_client(function() --[[ Line: 39 ]]
    --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_31 ]]
    v_u_30 = require(game.ReplicatedStorage.Lobby.Menus.ChallengePassUI)
    v_u_31 = require(game.ReplicatedStorage.Lobby.Menus.ChallengePassV2UI)
end)
local l_Daily_0 = v_u_11.Daily
local v_u_32 = v_u_2:new()
local v_u_33 = v_u_31
local v_u_34 = v_u_30
local v35 = {}
for _, v36 in v_u_11:get_all():key_itr() do
    v_u_32:add(v36, 0)
end;
local v_u_37 = true
v35.new = function(_, p_u_38, p_u_39, p_u_40) --[[ Name: new ]] --[[ Line: 54 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_12, (ref 6): l_Daily_0, (copy 7): v_u_15, (copy 8): v_u_6, (copy 9): v_u_5, (copy 10): v_u_8, (copy 11): v_u_16, (copy 12): v_u_22, (copy 13): v_u_32, (copy 14): v_u_11, (copy 15): v_u_17, (ref 16): v_u_33, (ref 17): v_u_34, (copy 18): v_u_20, (ref 19): v_u_37, (copy 20): v_u_26, (copy 21): v_u_21, (copy 22): v_u_23, (copy 23): v_u_28, (copy 24): v_u_27, (copy 25): v_u_18, (copy 26): v_u_19, (copy 27): v_u_10, (copy 28): v_u_14, (copy 29): v_u_13, (copy 30): v_u_25, (copy 31): v_u_24, (copy 32): v_u_9, (copy 33): v_u_7 ]]
    local v_u_41 = v_u_4:new(p_u_39, p_u_40)
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = nil
    local function _() --[[ Name: test_time_to_next_day_and_update ]] --[[ Line: 61 ]]
        --[[ Upvalues: (copy 1): p_u_38 ]]
        p_u_38._player_blob_manager:test_time_to_next_day_and_update()
    end;
    local v_u_45 = v_u_3:new()
    local function f_updated_selected_mission_list() --[[ Name: updated_selected_mission_list ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (copy 3): p_u_38, (ref 4): v_u_2, (ref 5): v_u_12, (ref 6): l_Daily_0, (ref 7): v_u_45 ]]
        v_u_1:profilebegin("MissionUI updated_selected_mission_list")
        local v_u_46 = v_u_3:new()
        local v_u_47 = p_u_38._player_blob_manager:get_player_blob()
        local v_u_48 = p_u_38._player_blob_manager:get_server_mission_data()
        local v_u_49 = v_u_2:new()
        v_u_12:playerblob_missiondata_available_foreach(v_u_47, v_u_48, l_Daily_0, function(p50) --[[ Line: 76 ]]
            --[[ Upvalues: (copy 1): v_u_46, (copy 2): v_u_49, (ref 3): v_u_12, (copy 4): v_u_47, (copy 5): v_u_48, (ref 6): l_Daily_0 ]]
            v_u_46:push_back(p50)
            v_u_49:add(v_u_12:mission_get_id(p50), v_u_12:playerblob_missiondata_missionid_is_completeable(v_u_47, v_u_48, l_Daily_0, v_u_12:mission_get_id(p50)))
        end)
        v_u_1:profilebegin("sort")
        v_u_46:sort(function(p51, p52) --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_49 ]]
            local v53 = v_u_12:mission_get_id(p51)
            local v54 = v_u_12:mission_get_id(p52)
            local v55 = v_u_49:get(v53)
            local v56 = v_u_49:get(v54)
            if v55 and v56 then
                return v53 - v54;
            else
                return v55 and 1 or (v56 and -1 or v53 - v54);
            end;
        end)
        v_u_1:profileend()
        v_u_1:profileend()
        v_u_45 = v_u_46
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_1, (ref 3): v_u_15, (copy 4): v_u_41, (copy 5): p_u_38, (ref 6): v_u_6, (ref 7): v_u_5, (copy 8): p_u_39, (ref 9): v_u_8, (copy 10): p_u_40, (ref 11): v_u_44, (ref 12): v_u_16, (ref 13): v_u_22, (ref 14): v_u_2, (ref 15): l_Daily_0, (copy 16): f_updated_selected_mission_list, (ref 17): v_u_43, (ref 18): v_u_32, (ref 19): v_u_11, (ref 20): v_u_17, (ref 21): v_u_33, (ref 22): v_u_34, (ref 23): v_u_20, (ref 24): v_u_37, (ref 25): v_u_26, (ref 26): v_u_12, (ref 27): v_u_21, (ref 28): v_u_45, (ref 29): v_u_23, (ref 30): v_u_28, (ref 31): v_u_27, (ref 32): v_u_18, (ref 33): v_u_19, (ref 34): v_u_10 ]]
        v_u_42 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.MissionUI:Clone()
        v_u_42.Name = v_u_1:gen_name(v_u_42.Name)
        v_u_42.Parent = v_u_15:get_world_ui_folder()
        v_u_41._native_size = v_u_42.PrimaryPart.Size
        v_u_41._size = v_u_41._native_size
        v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, v_u_42.BackButtonSurface), p_u_39, function() --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): p_u_40, (ref 4): v_u_41 ]]
            p_u_38._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            p_u_40:remove_menu(v_u_41)
        end))
        local l_Frame_0 = v_u_42.MainSurface.SurfaceGui.Frame
        local l_DifficultyIcon_0 = l_Frame_0.DifficultySection.DifficultyIcon
        local l_Sub_0 = l_Frame_0.DifficultySection.Sub
        l_Sub_0.Text = ""
        v_u_44 = v_u_16:new(p_u_38, v_u_41, v_u_41, v_u_42)
        local v_u_57 = v_u_22:create_display_wrapper(v_u_42.DailyButton.SurfaceGui.Notification, v_u_42.DailyButton.SurfaceGui.Notification.Display)
        local v_u_58 = v_u_22:create_display_wrapper(v_u_42.WeeklyButton.SurfaceGui.Notification, v_u_42.WeeklyButton.SurfaceGui.Notification.Display)
        local v_u_59 = v_u_22:create_display_wrapper(v_u_42.ChallengePassButton.SurfaceGui.Frame.Notification, v_u_42.ChallengePassButton.SurfaceGui.Frame.Notification.Display)
        local v_u_60 = v_u_22:create_display_wrapper(v_u_42.TutorialButton.SurfaceGui.Frame.Notification, v_u_42.TutorialButton.SurfaceGui.Frame.Notification.Display)
        local v_u_61 = v_u_2:new()
        local function f_bind_mission_timeframe_to_button(p_u_62, p63) --[[ Name: bind_mission_timeframe_to_button ]] --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_41, (ref 3): p_u_38, (ref 4): v_u_5, (ref 5): v_u_42, (ref 6): p_u_39, (ref 7): v_u_8, (ref 8): l_Daily_0, (ref 9): f_updated_selected_mission_list, (ref 10): v_u_43, (ref 11): v_u_32, (copy 12): v_u_61 ]]
            v_u_61:add(p_u_62, (v_u_6:button_bind_anim_toggle(v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, p63), p_u_39, function() --[[ Line: 139 ]]
                --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): l_Daily_0, (copy 4): p_u_62, (ref 5): f_updated_selected_mission_list, (ref 6): v_u_43, (ref 7): v_u_32 ]]
                p_u_38._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                l_Daily_0 = p_u_62
                f_updated_selected_mission_list()
                v_u_43:set_i_offset(v_u_32:get(l_Daily_0))
                v_u_43:page_update()
            end):set_auto_zoffset_behaviour(true)), function() --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): v_u_41 ]]
                return v_u_41:get_alpha();
            end)))
        end;
        f_bind_mission_timeframe_to_button(v_u_11.Daily, v_u_42.DailyButton)
        f_bind_mission_timeframe_to_button(v_u_11.Weekly, v_u_42.WeeklyButton)
        v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, v_u_42.ChallengePassButton), p_u_39, function() --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): v_u_17, (ref 4): v_u_33, (ref 5): p_u_40, (ref 6): v_u_34, (ref 7): p_u_39 ]]
            p_u_38._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            if v_u_17.UseChallengePassV2 == true then
                v_u_33:show_challengepass_menu(p_u_38)
            else
                p_u_40:push_menu(v_u_34:new(p_u_38, p_u_39, p_u_40))
            end;
        end))
        local v_u_64 = v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, v_u_42.TutorialButton), p_u_39, function() --[[ Line: 168 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): p_u_40, (ref 4): v_u_20, (ref 5): p_u_39, (ref 6): v_u_37 ]]
            p_u_38._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_40:push_menu(v_u_20:new(p_u_38, p_u_39, p_u_40))
            v_u_37 = false
        end))
        local v_u_65 = v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, v_u_42.LeaderboardsButton), p_u_39, function() --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): v_u_26 ]]
            p_u_38._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_26:show_mission_leaderboards_ui(p_u_38)
        end):set_auto_zoffset_behaviour(true))
        local v_u_66 = v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, v_u_42.ClaimAllButton), p_u_39, function() --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): v_u_41 ]]
            p_u_38._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_41:claim_all_mission_rewards_pressed()
        end)):set_auto_zoffset_behaviour(true)
        v_u_66:set_visible(false)
        local v_u_67 = v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, v_u_42.TopArrowSurface), p_u_39, function() --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): v_u_43 ]]
            p_u_38._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_43:prev_page()
        end)):set_visible(false)
        local v_u_68 = v_u_41:add_cycle_element(p_u_38, 1, v_u_6:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, v_u_42.BottomArrowSurface), p_u_39, function() --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_8, (ref 3): v_u_43 ]]
            p_u_38._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_43:next_page()
        end)):set_visible(false)
        local function _() --[[ Name: get_daily_mission_completable_count ]] --[[ Line: 212 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_12, (ref 3): v_u_11 ]]
            local v_u_69 = p_u_38._player_blob_manager:get_player_blob()
            local v_u_70 = p_u_38._player_blob_manager:get_server_mission_data()
            local v_u_71 = 0
            v_u_12:playerblob_missiondata_available_foreach(v_u_69, v_u_70, v_u_11.Daily, function(p72) --[[ Line: 216 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_69, (copy 3): v_u_70, (ref 4): v_u_11, (ref 5): v_u_71 ]]
                if v_u_12:playerblob_missiondata_missionid_is_completeable(v_u_69, v_u_70, v_u_11.Daily, v_u_12:mission_get_id(p72)) then
                    v_u_71 = v_u_71 + 1
                end;
            end)
            return v_u_71;
        end;
        local function _() --[[ Name: get_weekly_mission_completable_count ]] --[[ Line: 224 ]]
            --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_12, (ref 3): v_u_11 ]]
            local v_u_73 = p_u_38._player_blob_manager:get_player_blob()
            local v_u_74 = p_u_38._player_blob_manager:get_server_mission_data()
            local v_u_75 = 0
            v_u_12:playerblob_missiondata_available_foreach(v_u_73, v_u_74, v_u_11.Weekly, function(p76) --[[ Line: 228 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_73, (copy 3): v_u_74, (ref 4): v_u_11, (ref 5): v_u_75 ]]
                if v_u_12:playerblob_missiondata_missionid_is_completeable(v_u_73, v_u_74, v_u_11.Weekly, v_u_12:mission_get_id(p76)) then
                    v_u_75 = v_u_75 + 1
                end;
            end)
            return v_u_75;
        end;
        local v_u_77 = p_u_38._player_blob_manager:get_player_blob()
        local v_u_78 = p_u_38._player_blob_manager:get_server_mission_data()
        local v_u_79 = 0
        v_u_12:playerblob_missiondata_available_foreach(v_u_77, v_u_78, v_u_11.Daily, function(p80) --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_77, (copy 3): v_u_78, (ref 4): v_u_11, (ref 5): v_u_79 ]]
            if v_u_12:playerblob_missiondata_missionid_is_completeable(v_u_77, v_u_78, v_u_11.Daily, v_u_12:mission_get_id(p80)) then
                v_u_79 = v_u_79 + 1
            end;
        end)
        if v_u_79 > 0 then
            v_u_32:add(v_u_11.Daily, 0)
        end;
        local v_u_81 = p_u_38._player_blob_manager:get_player_blob()
        local v_u_82 = p_u_38._player_blob_manager:get_server_mission_data()
        local v_u_83 = 0
        v_u_12:playerblob_missiondata_available_foreach(v_u_81, v_u_82, v_u_11.Weekly, function(p84) --[[ Line: 228 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_81, (copy 3): v_u_82, (ref 4): v_u_11, (ref 5): v_u_83 ]]
            if v_u_12:playerblob_missiondata_missionid_is_completeable(v_u_81, v_u_82, v_u_11.Weekly, v_u_12:mission_get_id(p84)) then
                v_u_83 = v_u_83 + 1
            end;
        end)
        if v_u_83 > 0 then
            v_u_32:add(v_u_11.Weekly, 0)
        end;
        f_updated_selected_mission_list()
        local l_PageDisplay_0 = l_Frame_0.PageDisplay
        local l_EmptyListDisplay_0 = l_Frame_0.EmptyListDisplay
        v_u_43 = v_u_21:new():set_fn_get_data_list(function() --[[ Line: 248 ]]
            --[[ Upvalues: (ref 1): v_u_45 ]]
            return v_u_45;
        end):set_fn_set_element_data(function(p85, p86) --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): l_Daily_0, (ref 3): v_u_11, (ref 4): p_u_38, (ref 5): v_u_12 ]]
            v_u_1:profilebegin("MissionUI fn_set_element_data")
            local v87
            if l_Daily_0 == v_u_11.Daily then
                v87 = p_u_38._player_blob_manager:get_time_to_next_day_sec()
            else
                v87 = p_u_38._player_blob_manager:get_time_to_next_week_sec()
            end;
            if p86 then
                p85:set_mission_data(p_u_38._player_blob_manager:get_server_mission_data(), v_u_12:mission_get_id(p86), l_Daily_0, v87)
            else
                p85:set_visible(false)
            end;
            v_u_1:profileend()
        end):set_fn_next_prev_visible(function(p88, p89) --[[ Line: 273 ]]
            --[[ Upvalues: (copy 1): v_u_68, (copy 2): v_u_67 ]]
            v_u_68:set_visible(p88)
            v_u_67:set_visible(p89)
        end):set_fn_is_empty(function(p90) --[[ Line: 277 ]]
            --[[ Upvalues: (copy 1): l_EmptyListDisplay_0 ]]
            l_EmptyListDisplay_0.Visible = p90
        end):set_fn_update_page_display(function(p91, p92) --[[ Line: 280 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): l_PageDisplay_0, (ref 3): p_u_38, (ref 4): v_u_12, (copy 5): l_DifficultyIcon_0, (ref 6): v_u_23, (ref 7): l_Daily_0, (ref 8): v_u_11, (copy 9): l_Sub_0, (ref 10): v_u_28, (copy 11): v_u_57, (copy 12): v_u_58, (copy 13): v_u_59, (ref 14): v_u_17, (ref 15): v_u_27, (ref 16): v_u_18, (copy 17): v_u_66, (copy 18): v_u_61, (copy 19): v_u_64, (ref 20): v_u_19, (copy 21): v_u_60, (ref 22): v_u_37, (copy 23): v_u_65 ]]
            v_u_1:profilebegin("MissionUI fn_update_page_display")
            l_PageDisplay_0.Text = string.format("Page %d of %d", p91, p92)
            local v_u_93 = p_u_38._player_blob_manager:get_player_blob()
            v_u_12:render_difficulty_image(l_DifficultyIcon_0, v_u_12:playerblob_get_mission_difficulty(v_u_93))
            if v_u_23:is_max_difficulty(v_u_12:playerblob_get_mission_difficulty(v_u_93)) == true or l_Daily_0 ~= v_u_11.Daily then
                l_Sub_0.Text = ""
            else
                l_Sub_0.Visible = true
                v_u_1:ptry(function() --[[ Line: 290 ]]
                    --[[ Upvalues: (ref 1): v_u_28, (ref 2): p_u_38, (copy 3): v_u_93, (ref 4): l_Sub_0, (ref 5): v_u_23, (ref 6): v_u_12 ]]
                    local v94 = v_u_28:playerblob_get_remaining_missions_of_playerblob_difficulty_to_rank_upgrade(p_u_38._player_blob_manager:get_server_mission_active_data(), v_u_93)
                    if v94 > 0 then
                        l_Sub_0.Text = string.format("Complete %d more \'%s\' mission(s) to reach the next rank!", v94, v_u_23:difficulty_to_string(v_u_12:playerblob_get_mission_difficulty(v_u_93)))
                    else
                        l_Sub_0.Text = ""
                    end;
                end)
            end;
            local v_u_95 = p_u_38._player_blob_manager:get_player_blob()
            local v_u_96 = p_u_38._player_blob_manager:get_server_mission_data()
            local v_u_97 = 0
            v_u_12:playerblob_missiondata_available_foreach(v_u_95, v_u_96, v_u_11.Daily, function(p98) --[[ Line: 216 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_95, (copy 3): v_u_96, (ref 4): v_u_11, (ref 5): v_u_97 ]]
                if v_u_12:playerblob_missiondata_missionid_is_completeable(v_u_95, v_u_96, v_u_11.Daily, v_u_12:mission_get_id(p98)) then
                    v_u_97 = v_u_97 + 1
                end;
            end)
            local v99 = v_u_97
            v_u_57:update_state(v99 > 0, v99)
            local v_u_100 = p_u_38._player_blob_manager:get_player_blob()
            local v_u_101 = p_u_38._player_blob_manager:get_server_mission_data()
            local v_u_102 = 0
            v_u_12:playerblob_missiondata_available_foreach(v_u_100, v_u_101, v_u_11.Weekly, function(p103) --[[ Line: 228 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_100, (copy 3): v_u_101, (ref 4): v_u_11, (ref 5): v_u_102 ]]
                if v_u_12:playerblob_missiondata_missionid_is_completeable(v_u_100, v_u_101, v_u_11.Weekly, v_u_12:mission_get_id(p103)) then
                    v_u_102 = v_u_102 + 1
                end;
            end)
            local v104 = v_u_102
            v_u_58:update_state(v104 > 0, v104)
            v_u_59:update_state(false)
            if v_u_17.UseChallengePassV2 == true then
                p_u_38._shop_local_protocol:request_challengepassv2_entry_list(function(p105) --[[ Line: 315 ]]
                    --[[ Upvalues: (ref 1): v_u_27, (copy 2): v_u_93, (ref 3): p_u_38, (ref 4): v_u_59 ]]
                    if v_u_27:playerblob_has_any_claimable_rewards_for_day_month(v_u_93, p105, p_u_38._player_blob_manager:get_day_id(), p_u_38._player_blob_manager:get_month_id()) then
                        v_u_59:update_state(true, 1)
                    end;
                end)
            else
                p_u_38._shop_local_protocol:request_challengepass_info_cached(function(p106) --[[ Line: 321 ]]
                    --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_93, (ref 3): p_u_38, (ref 4): v_u_59 ]]
                    local v107 = v_u_18:playerblob_get_challengepass_active_mission(v_u_93, p106)
                    if v107 ~= nil and v_u_18:playerblob_get_challengepass_mission_state(v_u_93, v107, p_u_38:get_current_dayid()) == v_u_18.ChallengePassMissionState.CurrentClaimable then
                        v_u_59:update_state(true, 1)
                    end;
                end)
            end;
            if v_u_17.ClaimAllMissionRewardsEnabled == true then
                if v99 > 0 or v104 > 0 then
                    v_u_66:set_visible(true)
                else
                    v_u_66:set_visible(false)
                end;
            else
                v_u_66:set_visible(false)
            end;
            for _, v108 in v_u_11:get_all():key_itr() do
                v_u_61:get(v108):set_toggle(v108 == l_Daily_0)
            end;
            v_u_64:set_visible(v_u_19:playerblob_is_gear_tutorial_active(v_u_93))
            v_u_60:update_state(v_u_37, 1)
            if l_Daily_0 == v_u_11.Weekly then
                v_u_65:set_visible(true)
            else
                v_u_65:set_visible(false)
            end;
            v_u_1:profileend()
        end):set_fn_store_i_offset(function(p109) --[[ Line: 353 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): l_Daily_0 ]]
            v_u_32:add(l_Daily_0, p109)
        end):set_i_offset(v_u_32:get(l_Daily_0)):set_do_wrap(true)
        local l_MissionDisplayProto_0 = v_u_42.MissionDisplayProto
        l_MissionDisplayProto_0.Parent = nil
        v_u_43:create_list_elements_from_anchors_and_proto({ v_u_42.Anchors.Anchor1, v_u_42.Anchors.Anchor2, v_u_42.Anchors.Anchor3 }, l_MissionDisplayProto_0, v_u_42, function(p110) --[[ Line: 369 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_5, (ref 3): v_u_41, (ref 4): v_u_42, (ref 5): p_u_38, (ref 6): p_u_39 ]]
            return v_u_10:new(v_u_5:new(v_u_41, v_u_42.PrimaryPart, p110.PrimaryPart), p_u_38, p_u_39, v_u_41):set_visible(false);
        end)
        v_u_41:set_alpha(0)
        v_u_41:layout()
        v_u_43:page_update()
        p_u_38._player_blob_manager:test_time_to_next_day_and_update()
    end;
    local function f_generate_description_string_from_server_params(p111) --[[ Name: generate_description_string_from_server_params ]] --[[ Line: 387 ]]
        return p111.MissionCompletedCount == 1 and "Rewards from completing mission..." or string.format("Rewards from completing %d mission(s)...", p111.MissionCompletedCount);
    end;
    v_u_41.claim_mission_complete_reward = function(_, p112) --[[ Name: claim_mission_complete_reward ]] --[[ Line: 395 ]]
        --[[ Upvalues: (copy 1): p_u_40, (ref 2): v_u_14, (copy 3): p_u_38, (copy 4): p_u_39, (ref 5): l_Daily_0, (copy 6): f_updated_selected_mission_list, (ref 7): v_u_43, (ref 8): v_u_13, (ref 9): v_u_25, (ref 10): v_u_24, (copy 11): f_generate_description_string_from_server_params, (ref 12): v_u_44 ]]
        local v_u_113 = p_u_40:push_menu(v_u_14:new(p_u_38, p_u_39, p_u_40):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_38._shop_local_protocol:claim_mission_complete(p112, l_Daily_0, function(p114, p_u_115) --[[ Line: 405 ]]
            --[[ Upvalues: (ref 1): p_u_40, (copy 2): v_u_113, (ref 3): v_u_14, (ref 4): p_u_38, (ref 5): p_u_39, (ref 6): f_updated_selected_mission_list, (ref 7): v_u_43, (ref 8): v_u_13, (ref 9): v_u_25, (ref 10): v_u_24, (ref 11): f_generate_description_string_from_server_params, (ref 12): v_u_44 ]]
            if p114 == false then
                p_u_40:remove_menu(v_u_113)
                p_u_40:push_menu(v_u_14:new(p_u_38, p_u_39, p_u_40):set_text("Mission complete failed", "Error"))
                return;
            else
                p_u_38._player_blob_manager:do_sync(function() --[[ Line: 412 ]]
                    --[[ Upvalues: (ref 1): p_u_38, (ref 2): f_updated_selected_mission_list, (ref 3): v_u_43, (copy 4): p_u_115, (ref 5): p_u_40, (ref 6): v_u_113, (ref 7): v_u_13, (ref 8): p_u_39, (ref 9): v_u_25, (ref 10): v_u_24, (ref 11): f_generate_description_string_from_server_params ]]
                    local v_u_116 = p_u_38._player_blob_manager:get_server_mission_data()
                    f_updated_selected_mission_list()
                    v_u_43:page_update()
                    if p_u_115.DidPlayerBlobUpgradeDifficulty ~= true then
                        p_u_40:remove_menu(v_u_113)
                    end;
                    local function _() --[[ Name: opt_show_mission_complete_ui ]] --[[ Line: 420 ]]
                        --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_113, (ref 3): p_u_115, (ref 4): v_u_13, (ref 5): p_u_38, (ref 6): p_u_39, (copy 7): v_u_116 ]]
                        p_u_40:remove_menu(v_u_113)
                        if p_u_115.DidPlayerBlobUpgradeDifficulty == true then
                            p_u_40:push_menu(v_u_13:new(p_u_38, p_u_39, p_u_40, v_u_116, p_u_115.RankupMissionID, p_u_115.RankupMissionTimeframe, p_u_115))
                        end;
                    end;
                    if typeof(p_u_115.RewardDescriptionInfoTable) == "table" and #p_u_115.RewardDescriptionInfoTable > 0 then
                        p_u_40:push_menu(v_u_25:new(p_u_38, p_u_39, p_u_40, v_u_24.RewardInfo:table_to_list(p_u_115.RewardDescriptionInfoTable), function() --[[ Line: 431 ]]
                            --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_113, (ref 3): p_u_115, (ref 4): v_u_13, (ref 5): p_u_38, (ref 6): p_u_39, (copy 7): v_u_116 ]]
                            p_u_40:remove_menu(v_u_113)
                            if p_u_115.DidPlayerBlobUpgradeDifficulty == true then
                                p_u_40:push_menu(v_u_13:new(p_u_38, p_u_39, p_u_40, v_u_116, p_u_115.RankupMissionID, p_u_115.RankupMissionTimeframe, p_u_115))
                            end;
                        end):set_header_text("Mission Rewards!"):set_sub_text(f_generate_description_string_from_server_params(p_u_115)))
                    else
                        p_u_40:remove_menu(v_u_113)
                        if p_u_115.DidPlayerBlobUpgradeDifficulty == true then
                            p_u_40:push_menu(v_u_13:new(p_u_38, p_u_39, p_u_40, v_u_116, p_u_115.RankupMissionID, p_u_115.RankupMissionTimeframe, p_u_115))
                        end;
                    end;
                end)
                if p_u_115.DidPlayerBlobUpgradeDifficulty == true then
                    v_u_44:rankup()
                else
                    v_u_44:item_completed()
                end;
            end;
        end)
    end;
    v_u_41.claim_all_mission_rewards_pressed = function(_) --[[ Name: claim_all_mission_rewards_pressed ]] --[[ Line: 453 ]]
        --[[ Upvalues: (ref 1): v_u_17, (copy 2): p_u_38, (ref 3): v_u_14, (ref 4): v_u_9, (copy 5): p_u_40, (copy 6): p_u_39, (copy 7): f_updated_selected_mission_list, (ref 8): v_u_43, (ref 9): v_u_13, (ref 10): v_u_25, (ref 11): v_u_24, (copy 12): f_generate_description_string_from_server_params, (ref 13): v_u_44 ]]
        if v_u_17.ClaimAllMissionRewardsEnabled == true then
            local v_u_117 = p_u_38._menus:push_menu(v_u_14:new(p_u_38, p_u_38._spui, p_u_38._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_38._evt:wait_on_event_once(v_u_9.EVT_Mission_ServerClaimAllMissionCompleteResponse, function(p118, p_u_119) --[[ Line: 457 ]]
                --[[ Upvalues: (ref 1): p_u_40, (copy 2): v_u_117, (ref 3): v_u_14, (ref 4): p_u_38, (ref 5): p_u_39, (ref 6): f_updated_selected_mission_list, (ref 7): v_u_43, (ref 8): v_u_13, (ref 9): v_u_25, (ref 10): v_u_24, (ref 11): f_generate_description_string_from_server_params, (ref 12): v_u_44 ]]
                if p118 == false then
                    p_u_40:remove_menu(v_u_117)
                    p_u_40:push_menu(v_u_14:new(p_u_38, p_u_39, p_u_40):set_text("Mission claim all failed", "Error"))
                    return;
                else
                    p_u_38._player_blob_manager:do_sync(function() --[[ Line: 464 ]]
                        --[[ Upvalues: (ref 1): p_u_38, (ref 2): f_updated_selected_mission_list, (ref 3): v_u_43, (copy 4): p_u_119, (ref 5): p_u_40, (ref 6): v_u_117, (ref 7): v_u_13, (ref 8): p_u_39, (ref 9): v_u_25, (ref 10): v_u_24, (ref 11): f_generate_description_string_from_server_params ]]
                        local v_u_120 = p_u_38._player_blob_manager:get_server_mission_data()
                        f_updated_selected_mission_list()
                        v_u_43:page_update()
                        if p_u_119.DidPlayerBlobUpgradeDifficulty ~= true then
                            p_u_40:remove_menu(v_u_117)
                        end;
                        local function _() --[[ Name: opt_show_mission_complete_ui ]] --[[ Line: 472 ]]
                            --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_117, (ref 3): p_u_119, (ref 4): v_u_13, (ref 5): p_u_38, (ref 6): p_u_39, (copy 7): v_u_120 ]]
                            p_u_40:remove_menu(v_u_117)
                            if p_u_119.DidPlayerBlobUpgradeDifficulty == true then
                                p_u_40:push_menu(v_u_13:new(p_u_38, p_u_39, p_u_40, v_u_120, p_u_119.RankupMissionID, p_u_119.RankupMissionTimeframe, p_u_119))
                            end;
                        end;
                        if typeof(p_u_119.RewardDescriptionInfoTable) == "table" and #p_u_119.RewardDescriptionInfoTable > 0 then
                            p_u_40:push_menu(v_u_25:new(p_u_38, p_u_39, p_u_40, v_u_24.RewardInfo:table_to_list(p_u_119.RewardDescriptionInfoTable), function() --[[ Line: 483 ]]
                                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_117, (ref 3): p_u_119, (ref 4): v_u_13, (ref 5): p_u_38, (ref 6): p_u_39, (copy 7): v_u_120 ]]
                                p_u_40:remove_menu(v_u_117)
                                if p_u_119.DidPlayerBlobUpgradeDifficulty == true then
                                    p_u_40:push_menu(v_u_13:new(p_u_38, p_u_39, p_u_40, v_u_120, p_u_119.RankupMissionID, p_u_119.RankupMissionTimeframe, p_u_119))
                                end;
                            end):set_header_text("Mission Rewards!"):set_sub_text(f_generate_description_string_from_server_params(p_u_119)))
                        else
                            p_u_40:remove_menu(v_u_117)
                            if p_u_119.DidPlayerBlobUpgradeDifficulty == true then
                                p_u_40:push_menu(v_u_13:new(p_u_38, p_u_39, p_u_40, v_u_120, p_u_119.RankupMissionID, p_u_119.RankupMissionTimeframe, p_u_119))
                            end;
                        end;
                    end)
                    if p_u_119.DidPlayerBlobUpgradeDifficulty == true then
                        v_u_44:rankup()
                    else
                        v_u_44:item_completed()
                    end;
                end;
            end)
            p_u_38._evt:fire_event_to_server(v_u_9.EVT_Mission_ClientClaimAllMissionComplete)
        end;
    end;
    v_u_41.on_refocus = function(_) --[[ Name: on_refocus ]] --[[ Line: 505 ]]
        --[[ Upvalues: (copy 1): f_updated_selected_mission_list, (ref 2): v_u_43 ]]
        f_updated_selected_mission_list()
        v_u_43:page_update()
    end;
    v_u_41.behaviour_update = function(p121, p122, p123) --[[ Name: behaviour_update ]] --[[ Line: 510 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_44, (ref 3): v_u_43, (copy 4): p_u_38 ]]
        p121:behaviour_update_base(p122, p123)
        if p121._current_mode == v_u_7.MODE_OPEN then
            v_u_44:update(p122)
            for _, v124 in v_u_43:get_display_elements():key_itr() do
                v124:behaviour_update(p122)
            end;
            p_u_38._player_blob_manager:test_time_to_next_day_and_update()
        end;
    end;
    v_u_41.layout = function(p125) --[[ Name: layout ]] --[[ Line: 523 ]]
        --[[ Upvalues: (copy 1): p_u_39, (ref 2): v_u_42, (ref 3): v_u_43, (ref 4): v_u_44 ]]
        p_u_39:uiobj_rescale_to_max_nxy(p125, 0.8, 0.85, p125:get_scale())
        v_u_42:SetPrimaryPartCFrame(p_u_39:get_cframe({
            ["PositionNXY"] = Vector2.new(0.575, 0.5),
            ["OffsetXYZ"] = p125:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        for _, v126 in v_u_43:get_display_elements():key_itr() do
            v126:layout()
        end;
        v_u_44:layout()
    end;
    v_u_41.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 536 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        v_u_42:Destroy()
    end;
    local v_u_127 = 1
    local v_u_128 = -1
    v_u_41.set_alpha = function(_, p129, p130) --[[ Name: set_alpha ]] --[[ Line: 542 ]]
        --[[ Upvalues: (ref 1): v_u_128, (ref 2): v_u_1, (ref 3): v_u_42 ]]
        if v_u_128 ~= p129 or p130 == true then
            v_u_128 = p129
            v_u_1:r_set_alpha(v_u_42, v_u_128)
        end;
    end;
    v_u_41.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 549 ]]
        --[[ Upvalues: (ref 1): v_u_128 ]]
        return v_u_128;
    end;
    v_u_41.set_scale = function(_, p131) --[[ Name: set_scale ]] --[[ Line: 550 ]]
        --[[ Upvalues: (ref 1): v_u_127 ]]
        v_u_127 = p131
    end;
    v_u_41.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 551 ]]
        --[[ Upvalues: (ref 1): v_u_127 ]]
        return v_u_127;
    end;
    v_u_41.get_native_size = function(p132) --[[ Name: get_native_size ]] --[[ Line: 552 ]]
        return p132._native_size;
    end;
    v_u_41.get_size = function(p133) --[[ Name: get_size ]] --[[ Line: 553 ]]
        return p133._size;
    end;
    v_u_41.set_size = function(p134, p135) --[[ Name: set_size ]] --[[ Line: 554 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        p134._size = p135
        v_u_42.PrimaryPart.Size = Vector3.new(p135.X, p135.Y, 0)
    end;
    v_u_41.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 558 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42.PrimaryPart.Position;
    end;
    v_u_41.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 559 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42.PrimaryPart.SurfaceGui;
    end;
    v_u_41.set_showing = function(_, p136) --[[ Name: set_showing ]] --[[ Line: 560 ]]
        --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_15 ]]
        if p136 then
            v_u_42.Parent = v_u_15:get_world_ui_folder()
        else
            v_u_42.Parent = nil
        end;
    end;
    f_cons()
    return v_u_41;
end;
return v35;
