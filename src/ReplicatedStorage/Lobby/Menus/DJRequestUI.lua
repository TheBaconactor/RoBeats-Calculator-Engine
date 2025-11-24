-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:43 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.Lobby.Dialogue.DJRequestDialogue)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.QueuedDisplaySection)
require(game.ReplicatedStorage.Shared.ImageTextAlpha)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_13 = require(game.ReplicatedStorage.Shared.DanceClubQueuedSongVote)
local v_u_14 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_15 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_18 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_19 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v20 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_21 = nil
local v_u_22 = nil
v20:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.SongSelectV3UI)
end)
local v23 = {}
local v_u_24 = nil
v23.new = function(_, p_u_25, p_u_26, p_u_27) --[[ Name: new ]] --[[ Line: 39 ]]
    --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_22, (copy 3): v_u_3, (copy 4): v_u_2, (copy 5): v_u_15, (copy 6): v_u_11, (copy 7): v_u_1, (copy 8): v_u_7, (copy 9): v_u_5, (copy 10): v_u_4, (copy 11): v_u_6, (ref 12): v_u_21, (copy 13): v_u_13, (copy 14): v_u_10, (copy 15): v_u_12, (copy 16): v_u_9, (copy 17): v_u_18, (copy 18): v_u_8, (copy 19): v_u_19, (copy 20): v_u_16, (copy 21): v_u_17, (copy 22): v_u_14 ]]
    if v_u_24 == nil then
        v_u_24 = v_u_22:create_info_state()
    end;
    local v_u_28 = v_u_3:new(p_u_26, p_u_27)
    local v_u_29 = nil
    local v_u_30 = 1
    local v_u_31 = 1
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = nil
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = v_u_2:new()
    local l_Normal_0 = v_u_15.Normal
    local function f_hide_info_audiomod_to_buttons() --[[ Name: hide_info_audiomod_to_buttons ]] --[[ Line: 65 ]]
        --[[ Upvalues: (copy 1): v_u_42 ]]
        for _, v43 in v_u_42:key_itr() do
            v43:set_visible(false)
        end;
    end;
    local function _(p44, p45) --[[ Name: get_mode_for_songkey ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        local v46 = v_u_11:singleton():get_audiomod_to_modes_of_songkey(p44)
        if v46:contains(p45) then
            return v46:get(p45);
        else
            return p44;
        end;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_1, (ref 3): v_u_7, (copy 4): v_u_28, (copy 5): p_u_25, (ref 6): v_u_5, (ref 7): v_u_4, (copy 8): p_u_26, (copy 9): p_u_27, (ref 10): v_u_6, (ref 11): v_u_38, (ref 12): v_u_41, (ref 13): v_u_11, (ref 14): l_Normal_0, (ref 15): v_u_21, (ref 16): v_u_39, (ref 17): v_u_13, (ref 18): v_u_40, (ref 19): v_u_32, (ref 20): v_u_10, (ref 21): v_u_33, (ref 22): v_u_12, (ref 23): v_u_34, (ref 24): v_u_35, (ref 25): v_u_36, (ref 26): v_u_37, (copy 27): v_u_42, (ref 28): v_u_15 ]]
        v_u_29 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.DJRequestUI:Clone()
        v_u_29.Name = v_u_1:gen_name(v_u_29.Name)
        v_u_29.Parent = v_u_7:get_world_ui_folder()
        v_u_28._native_size = v_u_29.PrimaryPart.Size
        v_u_28._size = v_u_28._native_size
        v_u_28:add_cycle_element(p_u_25, 1, v_u_5:new(v_u_4:new(v_u_28, v_u_29.PrimaryPart, v_u_29.BackButtonSurface), p_u_26, function() --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_28, (ref 3): p_u_25, (ref 4): v_u_6 ]]
            p_u_27:remove_menu(v_u_28)
            p_u_25._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
        end))
        v_u_38 = v_u_28:add_cycle_element(p_u_25, 1, v_u_5:new(v_u_4:new(v_u_28, v_u_29.PrimaryPart, v_u_29.QueueSongButton), p_u_26, function() --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_6, (ref 3): v_u_28 ]]
            p_u_25._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
            v_u_28:queue_song_pressed()
        end))
        v_u_38:set_visible(false)
        v_u_41 = v_u_28:add_cycle_element(p_u_25, 1, v_u_5:new(v_u_4:new(v_u_28, v_u_29.PrimaryPart, v_u_29.PlayButtonSurface), p_u_26, function() --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_6, (ref 3): v_u_11, (ref 4): l_Normal_0, (ref 5): v_u_21 ]]
            p_u_25._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
            local v47 = p_u_25._dance_club_manager:get_current_song_info()
            if v_u_11:singleton():contains_key(v47) then
                local v48 = l_Normal_0
                local v49 = v_u_11:singleton():get_audiomod_to_modes_of_songkey(v47)
                if v49:contains(v48) then
                    v47 = v49:get(v48)
                end;
                p_u_25._menus:push_menu(v_u_21:new(p_u_25, p_u_25._spui, p_u_25._menus, v47, nil))
            end;
        end):set_passive_anim():set_auto_zoffset_behaviour(true))
        v_u_41:set_visible(false)
        v_u_39 = v_u_28:add_cycle_element(p_u_25, 1, v_u_5:new(v_u_4:new(v_u_28, v_u_29.PrimaryPart, v_u_29.UpVoteButton), p_u_26, function() --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_6, (ref 3): v_u_28, (ref 4): v_u_13 ]]
            p_u_25._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_28:vote_current_song(v_u_13.UpVote)
        end):set_passive_anim(true))
        v_u_39:set_visible(false)
        v_u_40 = v_u_28:add_cycle_element(p_u_25, 1, v_u_5:new(v_u_4:new(v_u_28, v_u_29.PrimaryPart, v_u_29.DownVoteButton), p_u_26, function() --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_6, (ref 3): v_u_28, (ref 4): v_u_13 ]]
            p_u_25._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_28:vote_current_song(v_u_13.DownVote)
        end):set_passive_anim(true))
        v_u_40:set_visible(false)
        v_u_32 = v_u_10:new(p_u_25, v_u_28, v_u_28, v_u_29)
        local l_Frame_0 = v_u_29.PrimaryPart.SurfaceGui.Frame
        l_Frame_0.LoadedFrame.Visible = true
        l_Frame_0.LoadingFrame.Visible = false
        v_u_33 = v_u_12:new(l_Frame_0.LoadedFrame.NowPlayingSection)
        local v50 = v_u_33
        v50:set_song_title_display(v50:get_section_root().TitleDisplay)
        v50:set_artist_display(v50:get_section_root().ArtistDisplay)
        v50:set_cover_and_overlay_image(v50:get_section_root().SongIcon.Icon, v50:get_section_root().SongIcon.IconOverlay)
        v50:set_time_remaining_display(v50:get_section_root().TimeRemainingSection.TimeRemainingDisplay)
        v50:set_queued_by_display(v50:get_section_root().QueuerDisplay)
        v50:set_vote_bar_section(l_Frame_0.LoadedFrame.NowPlayingSection.BarSection.BarFillUp, l_Frame_0.LoadedFrame.NowPlayingSection.BarSection.BarFillDown, l_Frame_0.LoadedFrame.NowPlayingSection.BarSection.UpVoteDisplay, l_Frame_0.LoadedFrame.NowPlayingSection.BarSection.DownVoteDisplay, l_Frame_0.LoadedFrame.NowPlayingSection.BarSection.VotesToSkipDisplay)
        v50:update_vote_bar_fill(0, 0)
        v50:update_vote_to_skip_count(0)
        v_u_34 = v_u_12:new(v_u_29.PrimaryPart.SurfaceGui.Frame.LoadedFrame.UpNextSection)
        local v51 = v_u_34
        v51:set_song_title_display(v51:get_section_root().TitleDisplay)
        v51:set_artist_display(v51:get_section_root().ArtistDisplay)
        v51:set_cover_and_overlay_image(v51:get_section_root().SongIcon.Icon, v51:get_section_root().SongIcon.IconOverlay)
        v51:set_queued_by_display(v51:get_section_root().QueuerDisplay)
        v51:set_queue_status_display(v51:get_section_root().SongsQueuedCountDisplay)
        v_u_35 = v_u_12:new(v_u_29.PrimaryPart.SurfaceGui.Frame.LoadedFrame.YourQueuedSection)
        local v52 = v_u_35
        v52:set_song_title_display(v52:get_section_root().TitleDisplay)
        v52:set_artist_display(v52:get_section_root().ArtistDisplay)
        v52:set_cover_and_overlay_image(v52:get_section_root().SongIcon.Icon, v52:get_section_root().SongIcon.IconOverlay)
        v52:set_queue_status_display(v52:get_section_root().QueueStatusDisplay)
        v_u_36 = l_Frame_0.LoadedFrame.NowPlayingEmptyText
        v_u_37 = l_Frame_0.LoadedFrame.UpNextEmptyText
        v_u_36.Visible = false
        v_u_37.Visible = false
        local function f_create_info_to_audiomod_button(p_u_53, p54) --[[ Name: create_info_to_audiomod_button ]] --[[ Line: 192 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): p_u_25, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_29, (ref 6): p_u_26, (ref 7): v_u_6, (ref 8): v_u_11, (ref 9): v_u_42 ]]
            local v55 = v_u_28:add_cycle_element(p_u_25, 1, v_u_5:new(v_u_4:new(v_u_28, v_u_29.PrimaryPart, p54), p_u_26, function() --[[ Line: 197 ]]
                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_6, (ref 3): v_u_28, (copy 4): p_u_53 ]]
                p_u_25._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                v_u_28:select_audiomod(p_u_53)
            end):set_auto_zoffset_behaviour(true))
            v55:bind_data({
                ["Toggle"] = v_u_5:button_bind_anim_toggle(v55, function() --[[ Line: 203 ]]
                    --[[ Upvalues: (ref 1): v_u_28 ]]
                    return v_u_28:get_alpha();
                end),
                ["DifficultyDisplay"] = p54.SurfaceGui.Button.DifficultyDisplay,
                ["TargetSongKey"] = v_u_11:invalid_songkey()
            })
            v55:set_visible(false)
            v_u_42:add(p_u_53, v55)
        end;
        f_create_info_to_audiomod_button(v_u_15.Easy, v_u_29.SongInfoButtons.EasyModeButton)
        f_create_info_to_audiomod_button(v_u_15.Normal, v_u_29.SongInfoButtons.NormalModeButton)
        f_create_info_to_audiomod_button(v_u_15.Hard, v_u_29.SongInfoButtons.HardModeButton)
        for _, v56 in v_u_42:key_itr() do
            v56:set_visible(false)
        end;
        v_u_33:set_visible(false)
        v_u_34:set_visible(false)
        v_u_35:set_visible(false)
        pcall(function() --[[ Line: 219 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29.CoinRewardSurface.Parent = nil
        end)
        p_u_25:set_character_random_position_around_anchors_fn(function() --[[ Line: 227 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().DanceClub.StandAnchor, v_u_7:get_lobby_anchors().DanceClub.StandLookAnchor;
        end)
        p_u_25:transition_local_camera_to_anchors_fn(function() --[[ Line: 231 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7:get_lobby_anchors().DanceClub.CameraAnchor, v_u_7:get_lobby_anchors().DanceClub.LookAnchor;
        end)
        v_u_28:reset_selected_item()
        v_u_28:transition_update_visual(0)
        v_u_28:layout()
    end;
    v_u_28.vote_current_song = function(_, p57) --[[ Name: vote_current_song ]] --[[ Line: 241 ]]
        --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_40, (copy 3): p_u_27, (ref 4): v_u_9, (copy 5): p_u_25, (copy 6): p_u_26, (ref 7): v_u_6, (ref 8): v_u_18, (ref 9): v_u_8 ]]
        v_u_39:set_visible(false)
        v_u_40:set_visible(false)
        local v_u_58 = p_u_27:push_menu(v_u_9:new(p_u_25, p_u_26, p_u_27):set_text("Voting...", "Please wait..."):set_close_button_visible(false))
        p_u_25._dance_club_manager:vote_current_song(p57, function(p59, p60, p61) --[[ Line: 245 ]]
            --[[ Upvalues: (ref 1): p_u_27, (copy 2): v_u_58, (ref 3): v_u_9, (ref 4): p_u_25, (ref 5): p_u_26, (ref 6): v_u_6, (ref 7): v_u_18, (ref 8): v_u_8 ]]
            p_u_27:remove_menu(v_u_58)
            if p59 == true then
                if p61 > 0 then
                    p_u_25._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                    p_u_25._chat:get_system_channel():add_message_to_channel(v_u_18:new(string.format("For voting on this song, you got %d coins!", p61)):set_icon(v_u_8:currency_type_get_image(v_u_8.CurrencyType.Coins)))
                end;
            else
                p_u_27:push_menu(v_u_9:new(p_u_25, p_u_26, p_u_27):set_text("Voting Failed", p60))
            end;
        end)
    end;
    v_u_28.queue_song_pressed = function(p_u_62) --[[ Name: queue_song_pressed ]] --[[ Line: 264 ]]
        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_22, (copy 3): p_u_25, (ref 4): v_u_24, (ref 5): v_u_11, (ref 6): v_u_9, (copy 7): p_u_26, (ref 8): v_u_6, (ref 9): v_u_18, (ref 10): v_u_8 ]]
        p_u_27:push_menu(v_u_22:new(p_u_25, v_u_24, function(p63) --[[ Line: 268 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11:singleton():get_songkey_priority(p63) ~= v_u_11.SongPriority.Hidden;
        end, function(p64) --[[ Line: 271 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_9, (ref 3): p_u_25, (ref 4): p_u_26, (ref 5): v_u_6, (ref 6): v_u_18, (ref 7): v_u_8, (copy 8): p_u_62 ]]
            local v_u_65 = p_u_27:push_menu(v_u_9:new(p_u_25, p_u_26, p_u_27):set_text("Queueing Song...", "Please wait..."):set_close_button_visible(false))
            p_u_25._dance_club_manager:queue_song(p64, function(_, p66) --[[ Line: 273 ]]
                --[[ Upvalues: (ref 1): p_u_25, (ref 2): v_u_6, (ref 3): v_u_18, (ref 4): v_u_8, (ref 5): p_u_27, (copy 6): v_u_65, (ref 7): p_u_62 ]]
                if p66 > 0 then
                    p_u_25._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                    p_u_25._chat:get_system_channel():add_message_to_channel(v_u_18:new(string.format("For queueing on this song, you got %d coins!", p66)):set_icon(v_u_8:currency_type_get_image(v_u_8.CurrencyType.Coins)))
                end;
                p_u_27:remove_menu(v_u_65)
                p_u_62:sync_ui_to_dance_club_manager()
            end)
        end))
    end;
    local v_u_67 = 0
    v_u_28.behaviour_update = function(p68, p69, p70) --[[ Name: behaviour_update ]] --[[ Line: 292 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_32, (copy 3): p_u_25, (ref 4): v_u_67 ]]
        p68:behaviour_update_base(p69, p70)
        if p68._current_mode == v_u_19.MODE_OPEN then
            v_u_32:update(p69)
            if p_u_25._dance_club_manager:get_synced_time() ~= v_u_67 then
                v_u_67 = p_u_25._dance_club_manager:get_synced_time()
                p68:sync_ui_to_dance_club_manager()
                return;
            end;
            p68:sync_ui_now_playing_time_remaining_to_dance_club_manager()
        end;
    end;
    local function f_update_info_audiomod_to_button_display() --[[ Name: update_info_audiomod_to_button_display ]] --[[ Line: 330 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_33, (copy 3): f_hide_info_audiomod_to_buttons, (copy 4): v_u_42, (ref 5): v_u_16, (copy 6): p_u_25, (ref 7): v_u_15, (ref 8): v_u_17, (ref 9): l_Normal_0 ]]
        if v_u_11:singleton():contains_key(v_u_33:get_songid()) ~= true then
            return f_hide_info_audiomod_to_buttons();
        end;
        local v71 = v_u_33:get_songid()
        local v72 = v_u_11:singleton():key_get_audiomod(v71)
        local v73 = v_u_11:singleton():get_audiomod_to_modes_of_songkey(v71)
        for v74, v75 in v_u_42:key_itr() do
            v75:set_visible(true)
            local l_Toggle_0 = v75:get_bound_data().Toggle
            local l_DifficultyDisplay_0 = v75:get_bound_data().DifficultyDisplay
            if v73:contains(v74) then
                local v76 = v73:get(v74)
                v75:get_bound_data().TargetSongKey = v76
                l_DifficultyDisplay_0.Text = tostring((v_u_11:singleton():get_difficulty_for_key(v76)))
                l_DifficultyDisplay_0.TextColor3 = v_u_11:singleton():get_difficulty_color_for_key(v76)
                local v77 = false
                if v77 == false then
                    local v78, v79 = v_u_16:is_event_active(p_u_25._player_blob_manager:get_day_event_list())
                    v77 = v78 and v_u_16:get_playable_song_set(v79):contains(v76) and true or v77
                end;
                local v80 = v77 == false and v_u_15:mod_to_compare_value(v72) >= v_u_15:mod_to_compare_value(v74) and true or v77
                if v80 == false and v_u_17:playerblob_has_access_to_song(p_u_25._player_blob_manager:get_player_blob(), v76, p_u_25:get_current_dayid(), p_u_25._player_blob_manager:get_cached_collection_info()) and true or v80 then
                    v75:set_enabled(true)
                    if l_Normal_0 == v74 then
                        v75:set_scale(1.35)
                        v75:set_unselected_zoffset(750)
                        v75:set_passive_anim(true)
                        l_Toggle_0:set_toggle(true)
                    else
                        v75:set_scale(0.85)
                        v75:set_unselected_zoffset(500)
                        v75:set_passive_anim(false)
                        l_Toggle_0:set_toggle_off_alpha(0.75)
                        l_Toggle_0:set_toggle(false)
                    end;
                else
                    v75:set_enabled(false)
                    l_Toggle_0:set_toggle_off_alpha(0.2)
                    l_Toggle_0:set_toggle(false)
                end;
            else
                v75:get_bound_data().TargetSongKey = v_u_11:invalid_songkey()
                l_DifficultyDisplay_0.Text = "-"
                l_DifficultyDisplay_0.TextColor3 = Color3.new(1, 1, 1)
                v75:set_enabled(false)
                l_Toggle_0:set_toggle_off_alpha(0.2)
                l_Toggle_0:set_toggle(false)
                v75:set_scale(0.85)
                v75:set_unselected_zoffset(500)
            end;
        end;
    end;
    v_u_28.sync_ui_to_dance_club_manager = function(_) --[[ Name: sync_ui_to_dance_club_manager ]] --[[ Line: 405 ]]
        --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_11, (ref 3): v_u_33, (ref 4): v_u_1, (ref 5): v_u_39, (ref 6): v_u_40, (ref 7): v_u_36, (ref 8): v_u_41, (ref 9): l_Normal_0, (copy 10): f_update_info_audiomod_to_button_display, (copy 11): v_u_42, (ref 12): v_u_34, (ref 13): v_u_37, (ref 14): v_u_35, (ref 15): v_u_38 ]]
        local v81, v82, v83, v84, v85, v86, v87, v88 = p_u_25._dance_club_manager:get_current_song_info()
        if v_u_11:singleton():contains_key(v81) then
            if v_u_11:singleton():contains_key(v81) then
                p_u_25._game_join:set_last_loaded_songkey(v81)
            end;
            local v89 = v81 ~= v_u_33:get_songid()
            v_u_33:set_visible(true)
            v_u_33:set_songid(v81)
            v_u_33:set_time_remaining_text(string.format("%s / %s", v_u_1:format_ms_time(v82 * 1000), v_u_1:format_ms_time(v83 * 1000)))
            v_u_33:set_queued_by_text(string.format("Queued by: %s", v84))
            v_u_33:update_vote_bar_fill(v85, v86)
            v_u_33:update_vote_to_skip_count(v87)
            if v88 then
                v_u_39:set_visible(true)
                v_u_40:set_visible(true)
            else
                v_u_39:set_visible(false)
                v_u_40:set_visible(false)
            end;
            v_u_36.Visible = false
            v_u_41:set_visible(true)
            if v89 then
                l_Normal_0 = v_u_11:singleton():key_get_audiomod(v81)
            end;
            f_update_info_audiomod_to_button_display()
        else
            v_u_41:set_visible(false)
            v_u_39:set_visible(false)
            v_u_40:set_visible(false)
            v_u_33:set_visible(false)
            v_u_36.Visible = true
            for _, v90 in v_u_42:key_itr() do
                v90:set_visible(false)
            end;
        end;
        local v91, v92, v93 = p_u_25._dance_club_manager:get_next_song_info()
        if v_u_11:singleton():contains_key(v91) then
            v_u_34:set_visible(true)
            v_u_34:set_songid(v91)
            v_u_34:set_queued_by_text(string.format("Queued by: %s", v92))
            v_u_34:set_queue_status_text(string.format("%d Song(s) Queued", v93))
            v_u_37.Visible = false
        else
            v_u_34:set_visible(false)
            v_u_37.Visible = true
        end;
        local v94, v95 = p_u_25._dance_club_manager:get_queued_song_info()
        if v_u_11:singleton():contains_key(v94) then
            v_u_35:set_visible(true)
            v_u_35:set_songid(v94)
            v_u_35:set_queue_status_text(string.format("Your song is %s in the queue.", v_u_1:num_placify(v95)))
            v_u_38:set_visible(false)
        else
            v_u_35:set_visible(false)
            v_u_38:set_visible(true)
        end;
    end;
    v_u_28.select_audiomod = function(_, p96) --[[ Name: select_audiomod ]] --[[ Line: 474 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): l_Normal_0, (copy 4): f_update_info_audiomod_to_button_display ]]
        v_u_14:is_enum_member(p96, v_u_15)
        l_Normal_0 = p96
        f_update_info_audiomod_to_button_display()
    end;
    v_u_28.sync_ui_now_playing_time_remaining_to_dance_club_manager = function(_) --[[ Name: sync_ui_now_playing_time_remaining_to_dance_club_manager ]] --[[ Line: 480 ]]
        --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_11, (ref 3): v_u_33, (ref 4): v_u_1 ]]
        local v97, v98, v99, _ = p_u_25._dance_club_manager:get_current_song_info()
        if v_u_11:singleton():contains_key(v97) then
            v_u_33:set_time_remaining_text(string.format("%s / %s", v_u_1:format_ms_time(v98 * 1000), v_u_1:format_ms_time(v99 * 1000)))
        end;
    end;
    v_u_28.visual_update = function(p100, p101, p102) --[[ Name: visual_update ]] --[[ Line: 490 ]]
        --[[ Upvalues: (copy 1): p_u_25 ]]
        if p_u_25:transition_local_camera_cframe_finished() ~= false then
            p100:visual_update_base(p101, p102)
        end;
    end;
    v_u_28.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 497 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        v_u_29:Destroy()
    end;
    v_u_28.layout = function(p103) --[[ Name: layout ]] --[[ Line: 501 ]]
        --[[ Upvalues: (copy 1): p_u_26, (ref 2): v_u_31, (ref 3): v_u_29, (ref 4): v_u_32 ]]
        p103:opt_rescale_to_max_nxy(p_u_26, 0.7, 0.85, v_u_31)
        local v104, v105 = p103:opt_update_cframe_params(p_u_26, {
            ["PositionNXY"] = Vector2.new(0.525, 0.475),
            ["OffsetXYZ"] = p103:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v104 == true then
            v_u_29:SetPrimaryPartCFrame(v105)
        end;
        v_u_32:layout()
    end;
    v_u_28.set_alpha = function(_, p106) --[[ Name: set_alpha ]] --[[ Line: 515 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_1, (ref 3): v_u_29 ]]
        if v_u_30 ~= p106 then
            v_u_30 = p106
            v_u_1:r_set_alpha(v_u_29, v_u_30)
        end;
    end;
    v_u_28.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 522 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    v_u_28.set_scale = function(_, p107) --[[ Name: set_scale ]] --[[ Line: 523 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        v_u_31 = p107
    end;
    v_u_28.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 524 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v_u_28.get_native_size = function(p108) --[[ Name: get_native_size ]] --[[ Line: 526 ]]
        return p108._native_size;
    end;
    v_u_28.get_size = function(p109) --[[ Name: get_size ]] --[[ Line: 529 ]]
        return p109._size;
    end;
    v_u_28.set_size = function(p110, p111) --[[ Name: set_size ]] --[[ Line: 532 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        p110._size = p111
        v_u_29.PrimaryPart.Size = Vector3.new(p111.X, p111.Y, 0)
    end;
    v_u_28.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 536 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29.PrimaryPart.Position;
    end;
    v_u_28.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 539 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29.PrimaryPart.SurfaceGui;
    end;
    v_u_28.set_showing = function(_, p112) --[[ Name: set_showing ]] --[[ Line: 542 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_7 ]]
        if p112 then
            v_u_29.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_29.Parent = nil
        end;
    end;
    f_cons()
    return v_u_28;
end;
return v23;
