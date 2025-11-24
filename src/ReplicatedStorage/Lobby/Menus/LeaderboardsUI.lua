-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:42 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_12 = require(game.ReplicatedStorage.Lobby.Dialogue.LeaderboardsDialogue)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.Leaderboards.LeaderboardScoreDisplayElement)
local v_u_14 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_15 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_16 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardSongPurchaseInfo)
local v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.SongAcquiredV2UI)
local v_u_21 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_22 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_23 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_24 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_25 = require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_26 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_27 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_28 = require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
local v_u_29 = require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
local v30 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_31 = nil
local v_u_32 = nil
local v_u_33 = nil
v30:require_client(function() --[[ Line: 38 ]]
    --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_33 ]]
    v_u_31 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_32 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_33 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
end)
local v_u_78 = {
    ["Mode"] = {
        ["Loading"] = 1,
        ["Loaded"] = 2
    },
    ["show_last_week_leaderboard"] = function(_, p_u_34) --[[ Name: show_last_week_leaderboard ]] --[[ Line: 645 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_14, (copy 3): v_u_25, (ref 4): v_u_33, (copy 5): v_u_15, (copy 6): v_u_1, (copy 7): v_u_3, (copy 8): v_u_6, (copy 9): v_u_2, (copy 10): v_u_29, (copy 11): v_u_28 ]]
        local function f_show_personal_place_for_leaderboard_song_info(p_u_35) --[[ Name: show_personal_place_for_leaderboard_song_info ]] --[[ Line: 646 ]]
            --[[ Upvalues: (copy 1): p_u_34, (ref 2): v_u_11, (ref 3): v_u_14, (ref 4): v_u_25, (ref 5): v_u_33, (ref 6): v_u_15, (ref 7): v_u_1 ]]
            local v_u_36 = p_u_34._menus:push_menu(v_u_11:new(p_u_34, p_u_34._spui, p_u_34._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_34._evt:wait_on_event_once(v_u_14.EVT_Leaderboard_ViewLastWeekSongPersonalServer, function(p37) --[[ Line: 648 ]]
                --[[ Upvalues: (ref 1): p_u_34, (copy 2): v_u_36, (ref 3): v_u_25, (copy 4): p_u_35, (ref 5): v_u_33, (ref 6): v_u_15, (ref 7): v_u_1, (ref 8): v_u_11 ]]
                p_u_34._menus:remove_menu(v_u_36)
                v_u_25:leaderboard_song_info_apply_player_leaderboard_info(p_u_35, p37)
                if p_u_35.IsEntered then
                    p_u_34._menus:push_menu(v_u_33:new(p_u_34, p_u_34._spui, p_u_34._menus, function(p38) --[[ Line: 656 ]]
                        --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_35, (ref 3): v_u_1 ]]
                        p38:set_header_text(string.format("Leaderboard: %s", v_u_15:singleton():get_title_for_key(p_u_35.SongKey)))
                        p38:set_sub_text(string.format("Place: %s - Attempts: %d", v_u_1:num_placify(p_u_35.YouDisplay.Place), p_u_35.YouDisplay.Attempts))
                        p38:get_element_list():push_back(p_u_35.YouDisplayAbove)
                        p38:get_element_list():push_back(p_u_35.YouDisplay)
                        p38:get_element_list():push_back(p_u_35.YouDisplayBelow)
                    end, function(p39, p40, p_u_41, _, p42) --[[ Line: 663 ]]
                        --[[ Upvalues: (ref 1): v_u_1 ]]
                        if v_u_1:get_local_userid() == p39.RbxID then
                            p40.Text = string.format("(You) [%s] %s - %s", v_u_1:num_placify(p39.Place), p39.PlayerName, v_u_1:comma_value(p39.Score))
                        else
                            p40.Text = string.format("[%s] %s - %s", v_u_1:num_placify(p39.Place), p39.PlayerName, v_u_1:comma_value(p39.Score))
                        end;
                        p42:get_description_display().Text = string.format("Multiplier: %.2f", p39.GearMult)
                        v_u_1:get_user_thumbnail(p39.RbxID, function(p43, _) --[[ Line: 670 ]]
                            --[[ Upvalues: (copy 1): p_u_41 ]]
                            if p_u_41 ~= nil then
                                p_u_41.Image = p43
                            end;
                        end, false)
                        p42:set_select_button_enabled(false)
                    end, function(_) end))
                else
                    p_u_34._menus:push_menu(v_u_11:new(p_u_34, p_u_34._spui, p_u_34._menus):set_text("Not Entered", "You did not enter this leaderboard."))
                end;
            end)
            p_u_34._evt:fire_event_to_server(v_u_14.EVT_Leaderboard_ViewLastWeekSongPersonalClient, p_u_35.SongIndex)
        end;
        local function f_show_leaderboard_song_info(p_u_44, p45) --[[ Name: show_leaderboard_song_info ]] --[[ Line: 688 ]]
            --[[ Upvalues: (copy 1): p_u_34, (ref 2): v_u_33, (ref 3): v_u_15, (ref 4): v_u_1, (ref 5): v_u_3, (ref 6): v_u_6, (copy 7): f_show_personal_place_for_leaderboard_song_info ]]
            local v53 = p_u_34._menus:push_menu(v_u_33:new(p_u_34, p_u_34._spui, p_u_34._menus, function(p46) --[[ Line: 693 ]]
                --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_44 ]]
                p46:set_header_text(string.format("Leaderboard: %s", v_u_15:singleton():get_title_for_key(p_u_44.SongKey)))
                p46:set_sub_text(string.format("Total Participants: %d", p_u_44.TotalParticipants))
                for v47 = 1, #p_u_44.LeaderboardPlaces do
                    p46:get_element_list():push_back(p_u_44.LeaderboardPlaces[v47])
                end;
            end, function(p48, p49, p_u_50, _, p51) --[[ Line: 700 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                if v_u_1:get_local_userid() == p48.RbxID then
                    p49.Text = string.format("(You) [%s] %s - %s", v_u_1:num_placify(p48.Place), p48.PlayerName, v_u_1:comma_value(p48.Score))
                else
                    p49.Text = string.format("[%s] %s - %s", v_u_1:num_placify(p48.Place), p48.PlayerName, v_u_1:comma_value(p48.Score))
                end;
                p51:get_description_display().Text = string.format("Multiplier: %.2f", p48.GearMult)
                v_u_1:get_user_thumbnail(p48.RbxID, function(p52, _) --[[ Line: 707 ]]
                    --[[ Upvalues: (copy 1): p_u_50 ]]
                    if p_u_50 ~= nil then
                        p_u_50.Image = p52
                    end;
                end, false)
                p51:set_select_button_enabled(false)
            end, function(_) end))
            v53:get_list_adapter():set_do_wrap(true)
            if p45:contains(p_u_44.SongIndex) then
                v53:set_settings_section_visible()
                local v54 = v_u_3:new()
                v54:push_back(function(p55) --[[ Line: 720 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): f_show_personal_place_for_leaderboard_song_info, (copy 3): p_u_44 ]]
                    v_u_6:set_button_text(p55, "\240\159\165\135 Your Place")
                    p55:bind_data(function() --[[ Line: 722 ]]
                        --[[ Upvalues: (ref 1): f_show_personal_place_for_leaderboard_song_info, (ref 2): p_u_44 ]]
                        f_show_personal_place_for_leaderboard_song_info(p_u_44)
                    end)
                end)
                for _, v56 in v53:get_settings_buttons():key_itr() do
                    if v54:count() > 0 then
                        v56:set_visible(true)
                        v54:pop_front()(v56)
                    else
                        v56:set_visible(false)
                    end;
                end;
            end;
        end;
        local v_u_57 = p_u_34._menus:push_menu(v_u_11:new(p_u_34, p_u_34._spui, p_u_34._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_34._evt:wait_on_event_once(v_u_14.EVT_Leaderboard_ViewLastWeekInfoServer, function(p58, p59) --[[ Line: 741 ]]
            --[[ Upvalues: (copy 1): p_u_34, (copy 2): v_u_57, (ref 3): v_u_2, (ref 4): v_u_3, (ref 5): v_u_25, (ref 6): v_u_15, (ref 7): v_u_33, (copy 8): f_show_leaderboard_song_info, (ref 9): v_u_6, (ref 10): v_u_29, (ref 11): v_u_28 ]]
            p_u_34._menus:remove_menu(v_u_57)
            local v_u_60 = v_u_2:new()
            for _, v61 in v_u_3:new(p59):key_itr() do
                v_u_60:add_set(v61.SongIndex)
            end;
            local v_u_62 = v_u_3:new()
            for v63 = 1, #p58 do
                v_u_62:push_back(v_u_25:from_leaderboard_info_table(p58[v63]))
            end;
            v_u_62:sort(function(p64, p65) --[[ Line: 753 ]]
                --[[ Upvalues: (ref 1): v_u_15 ]]
                return v_u_15:singleton():get_difficulty_for_key(p64.SongKey) < v_u_15:singleton():get_difficulty_for_key(p65.SongKey);
            end)
            local v72 = p_u_34._menus:push_menu(v_u_33:new(p_u_34, p_u_34._spui, p_u_34._menus, function(p66) --[[ Line: 761 ]]
                --[[ Upvalues: (copy 1): v_u_62 ]]
                p66:set_header_text("Last Week\'s Leaderboards")
                p66:get_element_list():push_back_from_list(v_u_62)
            end, function(p67, p68, p69, _, p70) --[[ Line: 765 ]]
                --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_60 ]]
                local l_SongKey_0 = p67.SongKey
                local l_TotalParticipants_0 = p67.TotalParticipants
                p68.Text = string.format("Leaderboard: %s", v_u_15:singleton():get_title_for_key(l_SongKey_0))
                if v_u_60:contains(p67.SongIndex) then
                    p70:get_description_display().Text = string.format("(Entered) Difficulty: %d - Total Participants: %d", v_u_15:singleton():get_difficulty_for_key(l_SongKey_0), l_TotalParticipants_0)
                else
                    p70:get_description_display().Text = string.format("Difficulty: %d - Total Participants: %d", v_u_15:singleton():get_difficulty_for_key(l_SongKey_0), l_TotalParticipants_0)
                end;
                p69.Image = v_u_15:singleton():get_coverimage_assetid_for_key(l_SongKey_0)
            end, function(p71) --[[ Line: 788 ]]
                --[[ Upvalues: (ref 1): f_show_leaderboard_song_info, (copy 2): v_u_60 ]]
                if p71 ~= nil then
                    f_show_leaderboard_song_info(p71, v_u_60)
                end;
            end)):set_close_on_element_select(false)
            v72:get_list_adapter():set_do_wrap(true)
            v72:set_settings_section_visible()
            local v76 = v_u_3:new():push_back_table_list({ function(p73) --[[ Line: 798 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_29, (ref 3): p_u_34, (ref 4): v_u_28 ]]
                    v_u_6:set_button_text(p73, "\240\159\146\172 View Messages")
                    p73:bind_data(function() --[[ Line: 800 ]]
                        --[[ Upvalues: (ref 1): v_u_29, (ref 2): p_u_34, (ref 3): v_u_28 ]]
                        v_u_29:show_chat_menu(p_u_34, v_u_28.Category.LastWeeklyLeaderboard, "", function(p74, p75) --[[ Line: 801 ]]
                            --[[ Upvalues: (ref 1): p_u_34 ]]
                            p74:set_header_text(string.format("Leaderboard Chat Archive (Last Week - %d)", p_u_34._player_blob_manager:get_week_id() - 1))
                            p75.NoChatButton = true
                        end)
                    end)
                end })
            for _, v77 in v72:get_settings_buttons():key_itr() do
                if v76:count() > 0 then
                    v77:set_visible(true)
                    v76:pop_front()(v77)
                else
                    v77:set_visible(false)
                end;
            end;
        end)
        p_u_34._evt:fire_event_to_server(v_u_14.EVT_Leaderboard_ViewLastWeekInfoClient)
    end
}
local v_u_79 = 0
v_u_78.new = function(_, p_u_80, p_u_81, p_u_82, p_u_83) --[[ Name: new ]] --[[ Line: 54 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_10, (copy 4): v_u_78, (copy 5): v_u_1, (copy 6): v_u_9, (copy 7): v_u_6, (copy 8): v_u_5, (copy 9): v_u_8, (ref 10): v_u_79, (copy 11): v_u_27, (ref 12): v_u_32, (copy 13): v_u_18, (ref 14): v_u_31, (copy 15): v_u_12, (copy 16): v_u_22, (copy 17): v_u_29, (copy 18): v_u_28, (copy 19): v_u_11, (copy 20): v_u_14, (copy 21): v_u_24, (copy 22): v_u_26, (copy 23): v_u_17, (copy 24): v_u_20, (copy 25): v_u_19, (copy 26): v_u_21, (copy 27): v_u_7, (copy 28): v_u_15, (copy 29): v_u_23, (copy 30): v_u_25, (copy 31): v_u_13, (copy 32): v_u_16 ]]
    local v_u_84 = v_u_4:new(p_u_81, p_u_82)
    local v_u_85 = nil
    local v_u_86 = 1
    local v_u_87 = 1
    local v_u_88 = nil
    local v_u_89 = v_u_3:new()
    local v_u_90 = nil
    local v_u_91 = nil
    local v_u_92 = nil
    local v_u_93 = nil
    local v_u_94 = nil
    local v_u_95 = nil
    local v_u_96 = nil
    local v_u_97 = nil
    local v_u_98 = nil
    local v_u_99 = nil
    local v_u_100 = nil
    local v_u_101 = v_u_3:new()
    local v_u_102 = nil
    local v_u_103 = nil
    local v_u_104 = nil
    local v_u_105 = 0
    local v_u_106 = -1
    local l_Coins_0 = v_u_10.CurrencyType.Coins
    local v_u_107 = 500
    local l_Loading_0 = v_u_78.Mode.Loading
    local v_u_108 = 0
    local v_u_109 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 88 ]]
        --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_1, (ref 3): v_u_9, (copy 4): v_u_84, (ref 5): v_u_90, (ref 6): v_u_91, (ref 7): v_u_109, (copy 8): p_u_80, (ref 9): v_u_100, (ref 10): v_u_6, (ref 11): v_u_5, (copy 12): p_u_81, (copy 13): p_u_82, (ref 14): v_u_8, (ref 15): v_u_92, (ref 16): v_u_79, (ref 17): v_u_105, (ref 18): v_u_93, (ref 19): v_u_94, (ref 20): v_u_95, (ref 21): v_u_96, (ref 22): v_u_97, (ref 23): v_u_27, (ref 24): v_u_32, (ref 25): v_u_18, (ref 26): v_u_31, (ref 27): v_u_88, (ref 28): v_u_12, (copy 29): p_u_83, (ref 30): v_u_22, (ref 31): v_u_98, (ref 32): v_u_78, (ref 33): v_u_99, (ref 34): v_u_29, (ref 35): v_u_28, (ref 36): v_u_108 ]]
        v_u_85 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.LeaderboardsUI:Clone()
        v_u_85.Name = v_u_1:gen_name(v_u_85.Name)
        v_u_85.Parent = v_u_9:get_world_ui_folder()
        v_u_84._native_size = v_u_85.PrimaryPart.Size
        v_u_84._size = v_u_84._native_size
        local l_Frame_0 = v_u_85.MainSurface.SurfaceGui.Frame
        v_u_90 = l_Frame_0.LoadingFrame
        v_u_91 = l_Frame_0.LoadedFrame
        v_u_109 = p_u_80._bgm_manager:begin_preview_songkey()
        p_u_80:set_character_random_position_around_anchors_fn(function() --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9:get_lobby_anchors().CompeteBuilding.Leaderboards.StandAnchor, v_u_9:get_lobby_anchors().CompeteBuilding.Leaderboards.LookAnchor;
        end)
        p_u_80:transition_local_camera_to_anchors_fn(function() --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9:get_lobby_anchors().CompeteBuilding.Leaderboards.CameraAnchor, v_u_9:get_lobby_anchors().CompeteBuilding.Leaderboards.LookAnchor;
        end)
        v_u_100 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.BackButtonSurface), p_u_81, function() --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): p_u_82, (ref 2): v_u_84, (ref 3): p_u_80, (ref 4): v_u_8 ]]
            p_u_82:remove_menu(v_u_84)
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
        end))
        v_u_92 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.NextButton), p_u_81, function() --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_79, (ref 4): v_u_105, (ref 5): v_u_84 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_79 = v_u_79 + 1
            if v_u_105 < v_u_79 then
                v_u_79 = 0
            end;
            v_u_84:load_current_song_index()
        end))
        v_u_93 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.PrevButton), p_u_81, function() --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_79, (ref 4): v_u_105, (ref 5): v_u_84 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_79 = v_u_79 - 1
            if v_u_79 < 0 then
                v_u_79 = v_u_105
            end;
            v_u_84:load_current_song_index()
        end))
        v_u_94 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.EnterButton), p_u_81, function() --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_84 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_84:enter_button_pressed()
        end))
        v_u_6:button_add_enabled_anim(v_u_94, function() --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): v_u_84 ]]
            return v_u_84:get_alpha();
        end)
        v_u_95 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.PlayButtonSurface), p_u_81, function() --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_84 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_84:play_button_pressed()
        end):set_passive_anim())
        v_u_95:set_visible(false)
        v_u_96 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.BuySongButton), p_u_81, function() --[[ Line: 168 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_84 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_84:buy_song_button_pressed()
        end))
        v_u_96:set_visible(false)
        v_u_97 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.CurrentRewardsButton), p_u_81, function() --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_27, (ref 4): p_u_82, (ref 5): v_u_32, (ref 6): p_u_81, (ref 7): v_u_18, (ref 8): v_u_97, (ref 9): v_u_31 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            if v_u_27.UseRewardDescriptionInfoAcquiredUI == true then
                p_u_82:push_menu(v_u_32:new(p_u_80, p_u_81, p_u_82, v_u_18:get_reward_list_for_tier(v_u_97:get_bound_data())):set_header_text("Current Rewards"):set_sub_text("Leaderboard rewards at your current rank. These will be claimable after the week ends."):finish_animation():show_description_extra_text(false))
            else
                p_u_82:push_menu(v_u_31:new(p_u_80, p_u_81, p_u_82, v_u_18:get_reward_list_for_tier(v_u_97:get_bound_data())):set_text_display("Current Rewards", "Leaderboard rewards at your current rank. These will be claimable after the week ends.")):finish_animation()
            end;
        end))
        v_u_97:bind_data(v_u_18.Tier.Tier6)
        v_u_97:set_visible(false)
        v_u_84:create_leaderboard_elements()
        v_u_84:create_selfposition_elements()
        v_u_88 = v_u_12:new(p_u_80, v_u_84, v_u_84, v_u_85)
        if p_u_83 ~= nil then
            v_u_22:is_int(p_u_83)
            v_u_79 = p_u_83
        end;
        v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.ClaimRewardsButton), p_u_81, function() --[[ Line: 217 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_84 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_84:request_claim_rewards()
        end))
        v_u_98 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.ViewLastWeekButton), p_u_81, function() --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_78 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_78:show_last_week_leaderboard(p_u_80)
        end))
        v_u_99 = v_u_84:add_cycle_element(p_u_80, 1, v_u_6:new(v_u_5:new(v_u_84, v_u_85.PrimaryPart, v_u_85.ChatButton), p_u_81, function() --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (ref 3): v_u_29, (ref 4): v_u_28, (ref 5): v_u_108 ]]
            p_u_80._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_29:show_chat_menu(p_u_80, v_u_28.Category.CurrentWeeklyLeaderboard, "", function(p110, p111) --[[ Line: 237 ]]
                --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_108 ]]
                p110:set_header_text(string.format("Leaderboard Chat (Current Week - %d)", p_u_80._player_blob_manager:get_week_id()))
                if v_u_108 == 0 then
                    p111.NoChatButton = true
                    p110:set_sub_text("Enter any leaderboard to be able to chat here.")
                end;
            end)
        end))
        v_u_84:load_current_song_index()
        v_u_84:reset_selected_item()
        v_u_84:transition_update_visual(0)
        v_u_84:layout()
    end;
    v_u_84.request_claim_rewards = function(_, p_u_112) --[[ Name: request_claim_rewards ]] --[[ Line: 255 ]]
        --[[ Upvalues: (copy 1): p_u_82, (ref 2): v_u_11, (copy 3): p_u_80, (copy 4): p_u_81, (ref 5): v_u_100, (ref 6): v_u_14, (ref 7): v_u_8, (ref 8): v_u_24, (ref 9): v_u_27, (ref 10): v_u_32, (ref 11): v_u_31 ]]
        local v_u_113 = p_u_82:push_menu(v_u_11:new(p_u_80, p_u_81, p_u_82):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        v_u_100:set_visible(false)
        p_u_80._evt:wait_on_event_once(v_u_14.EVT_Leaderboard_ServerRequestClaimRewardsResponse, function(p_u_114, p_u_115, p_u_116) --[[ Line: 259 ]]
            --[[ Upvalues: (ref 1): p_u_82, (ref 2): v_u_11, (ref 3): p_u_80, (ref 4): p_u_81, (copy 5): v_u_113, (ref 6): v_u_100, (copy 7): p_u_112, (ref 8): v_u_8, (ref 9): v_u_24, (ref 10): v_u_27, (ref 11): v_u_32, (ref 12): v_u_31 ]]
            local function f_finished_callback() --[[ Name: finished_callback ]] --[[ Line: 260 ]]
                --[[ Upvalues: (copy 1): p_u_114, (ref 2): p_u_82, (ref 3): v_u_11, (ref 4): p_u_80, (ref 5): p_u_81, (copy 6): p_u_115, (ref 7): v_u_113, (ref 8): v_u_100, (ref 9): p_u_112 ]]
                if p_u_114 ~= true then
                    p_u_82:push_menu(v_u_11:new(p_u_80, p_u_81, p_u_82):set_text("Reward Claim", p_u_115))
                end;
                p_u_82:remove_menu(v_u_113)
                v_u_100:set_visible(true)
                if p_u_112 then
                    p_u_112()
                end;
            end;
            if #p_u_116 == 0 then
                f_finished_callback()
            else
                p_u_80._player_blob_manager:do_sync(function() --[[ Line: 277 ]]
                    --[[ Upvalues: (ref 1): p_u_80, (ref 2): v_u_8, (copy 3): p_u_116, (ref 4): v_u_24, (ref 5): v_u_27, (ref 6): p_u_82, (ref 7): v_u_32, (ref 8): p_u_81, (ref 9): v_u_31, (copy 10): f_finished_callback ]]
                    p_u_80._sfx_manager:play_sfx(v_u_8.SFX_FANFARE)
                    for v117 = 1, #p_u_116 do
                        local l_Message_0 = p_u_116[v117].Message
                        local v118 = v_u_24.RewardInfo:table_to_list(p_u_116[v117].RewardListTable)
                        if v_u_27.UseRewardDescriptionInfoAcquiredUI == true then
                            p_u_82:push_menu(v_u_32:new(p_u_80, p_u_81, p_u_82, v118):set_header_text("Reward Claimed!"):set_sub_text(l_Message_0))
                        else
                            p_u_82:push_menu(v_u_31:new(p_u_80, p_u_81, p_u_82, v118):set_text_display("Reward Claimed!", l_Message_0))
                        end;
                    end;
                    f_finished_callback()
                end)
            end;
        end)
        p_u_80._evt:fire_event_to_server(v_u_14.EVT_Leaderboard_ClientRequestClaimRewards)
    end;
    local function _() --[[ Name: can_access_selected_song_key ]] --[[ Line: 298 ]]
        --[[ Upvalues: (copy 1): p_u_80, (ref 2): v_u_26, (ref 3): v_u_106 ]]
        return v_u_26:playerblob_has_access_to_song(p_u_80._player_blob_manager:get_player_blob(), v_u_106, p_u_80._player_blob_manager:get_day_id(), p_u_80._player_blob_manager:get_cached_collection_info());
    end;
    v_u_84.play_button_pressed = function(_) --[[ Name: play_button_pressed ]] --[[ Line: 303 ]]
        --[[ Upvalues: (copy 1): p_u_80, (ref 2): v_u_26, (ref 3): v_u_106, (copy 4): p_u_82, (ref 5): v_u_17, (copy 6): p_u_81 ]]
        if v_u_26:playerblob_has_access_to_song(p_u_80._player_blob_manager:get_player_blob(), v_u_106, p_u_80._player_blob_manager:get_day_id(), p_u_80._player_blob_manager:get_cached_collection_info()) then
            p_u_82:push_menu(v_u_17:new(p_u_80, p_u_81, p_u_82, v_u_106, nil))
        end;
    end;
    v_u_84.buy_song_button_pressed = function(p_u_119) --[[ Name: buy_song_button_pressed ]] --[[ Line: 312 ]]
        --[[ Upvalues: (copy 1): p_u_82, (ref 2): v_u_11, (copy 3): p_u_80, (copy 4): p_u_81, (ref 5): v_u_14, (ref 6): v_u_20, (ref 7): v_u_79, (ref 8): v_u_19, (ref 9): v_u_106, (ref 10): v_u_21 ]]
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 313 ]]
            --[[ Upvalues: (ref 1): p_u_82, (ref 2): v_u_11, (ref 3): p_u_80, (ref 4): p_u_81, (ref 5): v_u_14, (copy 6): p_u_119, (ref 7): v_u_20, (ref 8): v_u_79 ]]
            local v_u_120 = p_u_82:push_menu(v_u_11:new(p_u_80, p_u_81, p_u_82):set_text("Buying...", "Please wait..."):set_close_button_visible(false))
            p_u_80._evt:wait_on_event_once(v_u_14.EVT_Leaderboard_ServerSongBuyResponse, function(p121, p122, p_u_123) --[[ Line: 315 ]]
                --[[ Upvalues: (ref 1): p_u_82, (copy 2): v_u_120, (ref 3): v_u_11, (ref 4): p_u_80, (ref 5): p_u_81, (ref 6): p_u_119, (ref 7): v_u_20 ]]
                if p121 == true then
                    p_u_80._player_blob_manager:do_sync(function(_) --[[ Line: 322 ]]
                        --[[ Upvalues: (ref 1): p_u_80, (copy 2): p_u_123, (ref 3): p_u_119, (ref 4): p_u_82, (ref 5): v_u_120, (ref 6): v_u_20, (ref 7): p_u_81 ]]
                        p_u_80._player_blob_manager:add_recently_acquired_songid(p_u_123)
                        p_u_119:load_current_song_index()
                        p_u_82:remove_menu(v_u_120)
                        p_u_82:push_menu(v_u_20:new(p_u_80, p_u_81, p_u_82, p_u_123))
                    end)
                else
                    p_u_82:remove_menu(v_u_120)
                    p_u_82:push_menu(v_u_11:new(p_u_80, p_u_81, p_u_82):set_text("Purchase Failed", p122))
                end;
            end)
            p_u_80._evt:fire_event_to_server(v_u_14.EVT_Leaderboard_ClientSongBuy, v_u_79)
        end;
        local v124, v125 = v_u_19:get_price_for_song(v_u_106)
        local v126 = v_u_21:playerblob_purchase_needs_redirect(p_u_80._player_blob_manager:get_player_blob(), v124, v125)
        if v126:is_valid() then
            v_u_21:show_purchase_redirect(p_u_80, v126, function(p127) --[[ Line: 336 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p127 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    v_u_84.enter_button_pressed = function(p_u_128) --[[ Name: enter_button_pressed ]] --[[ Line: 346 ]]
        --[[ Upvalues: (copy 1): p_u_82, (ref 2): v_u_11, (copy 3): p_u_80, (copy 4): p_u_81, (ref 5): v_u_14, (ref 6): v_u_108, (ref 7): v_u_8, (ref 8): v_u_79, (ref 9): v_u_21, (ref 10): l_Coins_0, (ref 11): v_u_107 ]]
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 347 ]]
            --[[ Upvalues: (ref 1): p_u_82, (ref 2): v_u_11, (ref 3): p_u_80, (ref 4): p_u_81, (ref 5): v_u_14, (ref 6): v_u_108, (ref 7): v_u_8, (copy 8): p_u_128, (ref 9): v_u_79 ]]
            local v_u_129 = p_u_82:push_menu(v_u_11:new(p_u_80, p_u_81, p_u_82):set_text("Entering...", "Please wait..."):set_close_button_visible(false))
            p_u_80._evt:wait_on_event_once(v_u_14.EVT_Leaderboard_ServerRequestEnterLeaderboardResponse, function(p130, p131, p_u_132) --[[ Line: 349 ]]
                --[[ Upvalues: (ref 1): p_u_82, (copy 2): v_u_129, (ref 3): v_u_11, (ref 4): p_u_80, (ref 5): p_u_81, (ref 6): v_u_108, (ref 7): v_u_8, (ref 8): p_u_128 ]]
                if p130 == true then
                    v_u_108 = v_u_108 + 1
                    p_u_80._player_blob_manager:do_sync(function(_) --[[ Line: 356 ]]
                        --[[ Upvalues: (ref 1): p_u_82, (ref 2): v_u_129, (ref 3): p_u_80, (ref 4): v_u_8, (ref 5): p_u_128, (copy 6): p_u_132 ]]
                        p_u_82:remove_menu(v_u_129)
                        p_u_80._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                        p_u_128:render_leaderboard_song_info(p_u_132)
                    end)
                else
                    p_u_82:remove_menu(v_u_129)
                    p_u_82:push_menu(v_u_11:new(p_u_80, p_u_81, p_u_82):set_text("Purchase Failed", p131))
                end;
            end)
            p_u_80._evt:fire_event_to_server(v_u_14.EVT_Leaderboard_ClientRequestEnterLeaderboard, v_u_79)
        end;
        local v133 = v_u_21:playerblob_purchase_needs_redirect(p_u_80._player_blob_manager:get_player_blob(), l_Coins_0, v_u_107)
        if v133:is_valid() then
            v_u_21:show_purchase_redirect(p_u_80, v133, function(p134) --[[ Line: 368 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p134 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    v_u_84.load_current_song_index = function(p_u_135) --[[ Name: load_current_song_index ]] --[[ Line: 378 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_78, (copy 3): p_u_80, (ref 4): v_u_79, (ref 5): v_u_85, (ref 6): v_u_7, (ref 7): v_u_108 ]]
        l_Loading_0 = v_u_78.Mode.Loading
        p_u_135:update_mode()
        p_u_80._shop_local_protocol:leaderboard_query_song_index(v_u_79, function(p136, p137) --[[ Line: 383 ]]
            --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_7, (ref 3): l_Loading_0, (ref 4): v_u_78, (ref 5): v_u_108, (copy 6): p_u_135 ]]
            if v_u_85 == nil or v_u_85.Parent == nil then
                return v_u_7:warnf("LeaderboardsUI:load_current_song_index ui destroyed");
            end;
            l_Loading_0 = v_u_78.Mode.Loaded
            v_u_108 = typeof(p137) ~= "number" and 0 or p137
            p_u_135:update_mode()
            p_u_135:render_leaderboard_song_info(p136)
        end)
    end;
    local v_u_138 = 0
    v_u_84.render_leaderboard_song_info = function(p139, p140) --[[ Name: render_leaderboard_song_info ]] --[[ Line: 401 ]]
        --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_7, (ref 3): v_u_15, (ref 4): v_u_106, (copy 5): p_u_80, (ref 6): v_u_23, (ref 7): v_u_138, (ref 8): v_u_26, (ref 9): v_u_96, (ref 10): v_u_19, (ref 11): v_u_10, (ref 12): v_u_105, (copy 13): v_u_101, (ref 14): v_u_1, (ref 15): v_u_97, (ref 16): v_u_18, (ref 17): v_u_104, (ref 18): v_u_103, (ref 19): v_u_102, (ref 20): v_u_94, (ref 21): v_u_95, (ref 22): l_Coins_0, (ref 23): v_u_107, (ref 24): v_u_108, (ref 25): v_u_25 ]]
        if v_u_91:FindFirstChild("SongTitle") == nil then
            return v_u_7:warnf("LeaderboardsUI:render_leaderboard_song_info _loaded_frame.SongTitle nil");
        else
            local l_SongKey_1 = p140.SongKey
            if v_u_15:singleton():contains_key(l_SongKey_1) == true then
                v_u_106 = l_SongKey_1
                v_u_91.SongTitle.Text = v_u_15:singleton():get_title_for_key(l_SongKey_1)
                v_u_91.DifficultyDisplay.Text = v_u_15:singleton():get_difficulty_for_key(l_SongKey_1)
                p_u_80._bgm_manager:preview_songkey(l_SongKey_1)
                v_u_15:singleton():render_coverimage_for_key(v_u_91.IconFrame.Icon, v_u_91.IconFrame.IconOverlay, l_SongKey_1)
                v_u_23:render_songkey_colorsection(l_SongKey_1, v_u_91.IconFrame.ColorSection)
                v_u_138 = p140.TimeRemaining
                p139:render_time_remaining()
                v_u_91.TotalEntrantsDisplay.Text = tostring(p140.TotalParticipants)
                v_u_91.PageDisplay.Text = string.format("Song %d of %d", p140.SongIndex + 1, p140.MaxSongIndex + 1)
                p_u_80._player_blob_manager:get_player_blob()
                if v_u_26:playerblob_has_access_to_song(p_u_80._player_blob_manager:get_player_blob(), v_u_106, p_u_80._player_blob_manager:get_day_id(), p_u_80._player_blob_manager:get_cached_collection_info()) then
                    v_u_91.SongOwnedDisplay.Visible = true
                    v_u_91.SongNotOwnedDisplay.Visible = false
                    v_u_96:set_visible(false)
                else
                    v_u_91.SongOwnedDisplay.Visible = false
                    v_u_91.SongNotOwnedDisplay.Visible = true
                    local v141, v142 = v_u_19:get_price_for_song(l_SongKey_1)
                    v_u_10:currency_type_render_icon(v141, v_u_91.SongNotOwnedDisplay.PriceSection.Icon)
                    v_u_91.SongNotOwnedDisplay.PriceSection.Display.Text = tostring(v142)
                    v_u_96:set_visible(true)
                end;
                v_u_105 = p140.MaxSongIndex
                for v143 = 1, v_u_101:count() do
                    local v144
                    if v143 <= #p140.LeaderboardPlaces then
                        v144 = p140.LeaderboardPlaces[v143]
                    else
                        v144 = nil
                    end;
                    local v145 = v_u_101:get(v143)
                    if v144 == nil then
                        v145:set_ui_visible(false)
                    else
                        v145:set_info(v144)
                    end;
                end;
                if p140.IsEntered == true then
                    v_u_91.YouEntryDisplay.Visible = true
                    v_u_91.NoEntryDisplay.Visible = false
                    if p140.YouDisplay.Attempts == 0 then
                        v_u_91.YouEntryDisplay.RankDisplay.Text = "n/a"
                    else
                        v_u_91.YouEntryDisplay.RankDisplay.Text = v_u_1:num_placify(p140.YouDisplay.Place)
                    end;
                    v_u_91.YouEntryDisplay.AttemptsDisplay.Text = p140.YouDisplay.Attempts
                    if p140.YouDisplay.Attempts > 0 then
                        v_u_97:set_visible(true)
                        v_u_97:bind_data(v_u_18:get_tier_for_rank(p140.YouDisplay.Place))
                        v_u_91.YouEntryDisplay.NextRewardTierDisplay.Text = v_u_1:num_placify(v_u_18:next_reward_tier_for_rank(p140.YouDisplay.Place))
                    else
                        v_u_97:set_visible(false)
                        v_u_91.YouEntryDisplay.NextRewardTierDisplay.Text = "n/a"
                    end;
                    v_u_104:set_info(p140.YouDisplayAbove)
                    v_u_103:set_info(p140.YouDisplay)
                    v_u_102:set_info(p140.YouDisplayBelow)
                    v_u_94:set_visible(false)
                    if v_u_26:playerblob_has_access_to_song(p_u_80._player_blob_manager:get_player_blob(), v_u_106, p_u_80._player_blob_manager:get_day_id(), p_u_80._player_blob_manager:get_cached_collection_info()) then
                        v_u_95:set_visible(true)
                        v_u_96:set_visible(false)
                    else
                        v_u_95:set_visible(false)
                    end;
                else
                    v_u_91.YouEntryDisplay.Visible = false
                    v_u_91.NoEntryDisplay.Visible = true
                    v_u_91.NoEntryDisplay.CurrencyDisplay.Text = v_u_1:comma_value(p140.EntryPrice)
                    v_u_10:currency_type_render_icon(p140.EntryPriceType, v_u_91.NoEntryDisplay.CurrencyIcon)
                    l_Coins_0 = p140.EntryPriceType
                    v_u_107 = p140.EntryPrice
                    v_u_91.NoEntryDisplay.EnterCountDisplay.Text = string.format("You have entered %d of %d leaderboards for this week.", v_u_108, v_u_25:get_max_weekly_entries())
                    v_u_94:set_visible(true)
                    if v_u_108 < v_u_25:get_max_weekly_entries() then
                        v_u_94:set_enabled(true)
                    else
                        v_u_94:set_enabled(false)
                    end;
                    v_u_104:set_ui_visible(false)
                    v_u_103:set_ui_visible(false)
                    v_u_102:set_ui_visible(false)
                    v_u_95:set_visible(false)
                    v_u_97:set_visible(false)
                    return;
                end;
            else
                return v_u_7:warnf("LeaderboardsUI:render_leaderboard_song_info songkey is not in SongDatabase");
            end;
        end;
    end;
    v_u_84.render_time_remaining = function(_) --[[ Name: render_time_remaining ]] --[[ Line: 513 ]]
        --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_1, (ref 3): v_u_138 ]]
        v_u_91.TimeRemainingDisplay.Text = v_u_1:format_sec_time(v_u_138)
    end;
    v_u_84.update_mode = function(_) --[[ Name: update_mode ]] --[[ Line: 517 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_78, (copy 3): v_u_89, (ref 4): v_u_92, (ref 5): v_u_93, (ref 6): v_u_90, (ref 7): v_u_91, (ref 8): v_u_94, (ref 9): v_u_95, (ref 10): v_u_96, (ref 11): v_u_97, (ref 12): v_u_99 ]]
        if l_Loading_0 == v_u_78.Mode.Loading then
            for v146 = 1, v_u_89:count() do
                v_u_89:get(v146):set_visible(false)
            end;
            v_u_92:set_visible(false)
            v_u_93:set_visible(false)
            v_u_90.Visible = true
            v_u_91.Visible = false
            v_u_94:set_visible(false)
            v_u_95:set_visible(false)
            v_u_96:set_visible(false)
            v_u_97:set_visible(false)
            v_u_99:set_visible(false)
        elseif l_Loading_0 == v_u_78.Mode.Loaded then
            for v147 = 1, v_u_89:count() do
                v_u_89:get(v147):set_visible(true)
            end;
            v_u_92:set_visible(true)
            v_u_93:set_visible(true)
            v_u_90.Visible = false
            v_u_91.Visible = true
            v_u_95:set_visible(false)
            v_u_97:set_visible(false)
            v_u_99:set_visible(true)
        end;
    end;
    v_u_84.create_leaderboard_elements = function(p148) --[[ Name: create_leaderboard_elements ]] --[[ Line: 547 ]]
        --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_85, (copy 3): v_u_89, (copy 4): v_u_101 ]]
        local v149 = v_u_13:new(p148, v_u_85.PrimaryPart, v_u_85.LeaderboardTopProto)
        v_u_89:push_back(v149)
        v_u_101:push_back(v149)
        local l_LeaderboardElementProto_0 = v_u_85.LeaderboardElementProto
        l_LeaderboardElementProto_0.Parent = nil
        for v150 = 2, 9 do
            local l_Anchors_0 = v_u_85.Anchors[tostring(v150)]
            local v151 = l_LeaderboardElementProto_0:Clone()
            v151.Position = l_Anchors_0.Position
            v151.Parent = v_u_85
            v151.Name = string.format("sub_display_element_proto(%d)", v150)
            local v152 = v_u_13:new(p148, v_u_85.PrimaryPart, v151)
            v_u_89:push_back(v152)
            v_u_101:push_back(v152)
        end;
    end;
    v_u_84.create_selfposition_elements = function(p153) --[[ Name: create_selfposition_elements ]] --[[ Line: 568 ]]
        --[[ Upvalues: (ref 1): v_u_102, (ref 2): v_u_13, (ref 3): v_u_85, (copy 4): v_u_89, (ref 5): v_u_103, (ref 6): v_u_104 ]]
        v_u_102 = v_u_13:new(p153, v_u_85.PrimaryPart, v_u_85.YouInfo.YouBelow)
        v_u_89:push_back(v_u_102)
        v_u_103 = v_u_13:new(p153, v_u_85.PrimaryPart, v_u_85.YouInfo.YouDisplay)
        v_u_89:push_back(v_u_103)
        v_u_104 = v_u_13:new(p153, v_u_85.PrimaryPart, v_u_85.YouInfo.YouAbove)
        v_u_89:push_back(v_u_104)
    end;
    v_u_84.behaviour_update = function(p154, p155, p156) --[[ Name: behaviour_update ]] --[[ Line: 577 ]]
        --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_138, (ref 3): v_u_16 ]]
        p154:behaviour_update_base(p155, p156)
        v_u_88:update(p155)
        v_u_138 = math.max(v_u_138 - v_u_16:TimescaleToDeltaTime(p155), 0)
        p154:render_time_remaining()
    end;
    v_u_84.visual_update = function(p157, p158, p159) --[[ Name: visual_update ]] --[[ Line: 586 ]]
        --[[ Upvalues: (copy 1): p_u_80 ]]
        if p_u_80:transition_local_camera_cframe_finished() ~= false then
            p157:visual_update_base(p158, p159)
        end;
    end;
    v_u_84.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 593 ]]
        --[[ Upvalues: (ref 1): v_u_85, (copy 2): p_u_80, (ref 3): v_u_109 ]]
        v_u_85:Destroy()
        p_u_80._bgm_manager:stop_song_preview(v_u_109)
    end;
    v_u_84.layout = function(p160) --[[ Name: layout ]] --[[ Line: 598 ]]
        --[[ Upvalues: (copy 1): p_u_81, (ref 2): v_u_87, (ref 3): v_u_85, (ref 4): v_u_88, (copy 5): v_u_89 ]]
        p160:opt_rescale_to_max_nxy(p_u_81, 0.775, 0.925, v_u_87)
        local v161, v162 = p160:opt_update_cframe_params(p_u_81, {
            ["PositionNXY"] = Vector2.new(0.55, 0.45),
            ["OffsetXYZ"] = p160:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v161 == true then
            v_u_85:SetPrimaryPartCFrame(v162)
        end;
        v_u_88:layout()
        for v163 = 1, v_u_89:count() do
            v_u_89:get(v163):layout()
        end;
    end;
    v_u_84.set_alpha = function(_, p164) --[[ Name: set_alpha ]] --[[ Line: 614 ]]
        --[[ Upvalues: (ref 1): v_u_86, (ref 2): v_u_1, (ref 3): v_u_85 ]]
        if v_u_86 ~= p164 then
            v_u_86 = p164
            v_u_1:r_set_alpha(v_u_85, v_u_86)
        end;
    end;
    v_u_84.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 620 ]]
        --[[ Upvalues: (ref 1): v_u_86 ]]
        return v_u_86;
    end;
    v_u_84.set_scale = function(_, p165) --[[ Name: set_scale ]] --[[ Line: 621 ]]
        --[[ Upvalues: (ref 1): v_u_87 ]]
        v_u_87 = p165
    end;
    v_u_84.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 622 ]]
        --[[ Upvalues: (ref 1): v_u_87 ]]
        return v_u_87;
    end;
    v_u_84.get_native_size = function(p166) --[[ Name: get_native_size ]] --[[ Line: 624 ]]
        return p166._native_size;
    end;
    v_u_84.get_size = function(p167) --[[ Name: get_size ]] --[[ Line: 627 ]]
        return p167._size;
    end;
    v_u_84.set_size = function(p168, p169) --[[ Name: set_size ]] --[[ Line: 630 ]]
        --[[ Upvalues: (ref 1): v_u_85 ]]
        p168._size = p169
        v_u_85.PrimaryPart.Size = Vector3.new(p169.X, p169.Y, 0)
    end;
    v_u_84.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 634 ]]
        --[[ Upvalues: (ref 1): v_u_85 ]]
        return v_u_85.PrimaryPart.Position;
    end;
    v_u_84.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 637 ]]
        --[[ Upvalues: (ref 1): v_u_85 ]]
        return v_u_85.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_84;
end;
return v_u_78;
