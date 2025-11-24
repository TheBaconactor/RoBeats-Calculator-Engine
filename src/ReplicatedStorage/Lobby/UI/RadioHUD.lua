-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.SPUIButton)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIDisplay)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Lobby.Menus.DanceSelectUI)
require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Lobby.UI.ScrollingElementDisplay)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.DJRequestUI)
return {
    ["new"] = function(_, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_5, (copy 6): v_u_8, (copy 7): v_u_9, (copy 8): v_u_10, (copy 9): v_u_7, (copy 10): v_u_6 ]]
        local v17 = {
            ["playerblob_updated"] = function(p16) --[[ Name: playerblob_updated ]] --[[ Line: 120 ]]
                p16:refresh_mute_button()
            end
        }
        local v_u_18 = nil
        v17.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        v17.cons = function(p27) --[[ Name: cons ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_18, (ref 3): v_u_4, (copy 4): p_u_12, (ref 5): v_u_19, (ref 6): v_u_2, (ref 7): v_u_1, (ref 8): v_u_20, (copy 9): p_u_14, (copy 10): p_u_11, (ref 11): v_u_3, (ref 12): v_u_5, (ref 13): v_u_8, (copy 14): p_u_13, (ref 15): v_u_9, (ref 16): v_u_25, (ref 17): v_u_26, (ref 18): v_u_21, (ref 19): v_u_10, (ref 20): v_u_22, (ref 21): v_u_23, (ref 22): v_u_7, (ref 23): v_u_24 ]]
            local l_RadioSection_0 = p_u_15.RadioSection
            v_u_18 = v_u_4:new(l_RadioSection_0, p_u_12, true):set_position_nxy(1, 1):set_anchor_rnxy(1, 1)
            v_u_19 = v_u_2:new(v_u_18, v_u_18:get_part(), l_RadioSection_0.OpenSurface)
            local l_RadioBack_0 = l_RadioSection_0.OpenSurface.SurfaceGui.Frame.RadioBack
            l_RadioBack_0.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.9
            }, "RadioBack")
            l_RadioBack_0.ImageTransparency = v_u_1:tra(0.9)
            local l_TimeSectionBack_0 = l_RadioSection_0.OpenSurface.SurfaceGui.Frame.TimeSectionBack
            l_TimeSectionBack_0.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "TimeSectionBack")
            l_TimeSectionBack_0.ImageTransparency = v_u_1:tra(0.5)
            v_u_20 = p_u_14:add_cycle_element(p_u_11, 1, v_u_3:new(v_u_2:new(v_u_18, v_u_18:get_part(), l_RadioSection_0.MuteButton), p_u_12, function() --[[ Line: 62 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_5, (ref 3): v_u_8, (ref 4): p_u_13, (ref 5): v_u_9, (ref 6): p_u_12 ]]
                p_u_11._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                local v28 = not p_u_11._player_settings_manager:get_key(v_u_8.Key.RadioEnabled)
                p_u_11._player_settings_manager:set_key(v_u_8.Key.RadioEnabled, v28)
                if v28 == true then
                    p_u_11._player_settings_manager:set_key(v_u_8.Key.BGM, true)
                end;
                local v_u_29 = p_u_13:push_menu(v_u_9:new(p_u_11, p_u_12, p_u_13):set_text(v28 and "Enabling Radio..." or "Disabling Radio...", "Please wait..."):set_close_button_visible(false))
                p_u_11._player_settings_manager:save_changes_to_playerblob(p_u_11, function() --[[ Line: 81 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (copy 2): v_u_29, (ref 3): p_u_11 ]]
                    p_u_13:remove_menu(v_u_29)
                    p_u_11._player_settings_manager:clear_changes()
                end)
            end))
            v_u_25 = l_RadioSection_0.MuteButton.SurfaceGui.ButtonMuted
            v_u_26 = l_RadioSection_0.MuteButton.SurfaceGui.ButtonUnmuted
            p27:refresh_mute_button()
            v_u_21 = p_u_14:add_cycle_element(p_u_11, 1, v_u_3:new(v_u_2:new(v_u_18, v_u_18:get_part(), l_RadioSection_0.RadioButton), p_u_12, function() --[[ Line: 96 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_5, (ref 3): p_u_13, (ref 4): v_u_10, (ref 5): p_u_12 ]]
                p_u_11._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                p_u_13:push_menu(v_u_10:new(p_u_11, p_u_12, p_u_13))
            end))
            v_u_22 = v_u_1:get_list_of_children_of_classname(l_RadioSection_0.RadioButton, "ImageLabel")
            local l_Frame_0 = l_RadioSection_0.OpenSurface.SurfaceGui.Frame
            v_u_23 = v_u_7:new(l_Frame_0.ScrollingFrame.ScrollText1, l_Frame_0.ScrollingFrame.ScrollText2)
            v_u_23:set_text("")
            v_u_24 = l_Frame_0.TimeDisplay
        end;
        v17.refresh_mute_button = function(_) --[[ Name: refresh_mute_button ]] --[[ Line: 110 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_8, (ref 3): v_u_25, (ref 4): v_u_26 ]]
            if p_u_11._player_settings_manager:get_key(v_u_8.Key.RadioEnabled) then
                v_u_25.Visible = false
                v_u_26.Visible = true
            else
                v_u_25.Visible = true
                v_u_26.Visible = false
            end;
        end;
        local v_u_30 = 0
        v17.update = function(p31, p32) --[[ Name: update ]] --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_11, (ref 3): v_u_30 ]]
            v_u_23:update(p32)
            if p_u_11._dance_club_manager:get_synced_time() == v_u_30 then
                p31:sync_ui_now_playing_time_remaining_to_dance_club_manager()
            else
                v_u_30 = p_u_11._dance_club_manager:get_synced_time()
                p31:sync_ui_to_dance_club_manager()
            end;
        end;
        v17.sync_ui_to_dance_club_manager = function(_) --[[ Name: sync_ui_to_dance_club_manager ]] --[[ Line: 135 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_6, (ref 3): v_u_23, (ref 4): v_u_24, (ref 5): v_u_1, (ref 6): v_u_21, (ref 7): v_u_22, (copy 8): p_u_14 ]]
            local v33, v34, v35, _ = p_u_11._dance_club_manager:get_current_song_info()
            if v_u_6:singleton():contains_key(v33) then
                v_u_23:set_text(string.format("%s - Artist: %s - ", v_u_6:singleton():get_title_for_key(v33), v_u_6:singleton():get_artist_for_key(v33)))
                v_u_24.Text = string.format("%s / %s", v_u_1:format_ms_time(v34 * 1000), v_u_1:format_ms_time(v35 * 1000))
            else
                v_u_23:set_text("No song queued. Queue a song up in the DJ Club menu and get this party started!")
                v_u_24.Text = "- : -- / - : --"
            end;
            local v36, _ = p_u_11._dance_club_manager:get_queued_song_info()
            if v_u_6:singleton():contains_key(v36) then
                v_u_21:set_passive_anim(false)
                v_u_21:set_scale(1)
                for v37 = 1, v_u_22:count() do
                    v_u_1:obj_set_alpha(v_u_22:get(v37), 0.75, p_u_14:get_alpha())
                end;
            else
                v_u_21:set_passive_anim(true)
                v_u_21:set_scale(1.35)
                for v38 = 1, v_u_22:count() do
                    v_u_1:obj_set_alpha(v_u_22:get(v38), 1, p_u_14:get_alpha())
                end;
            end;
        end;
        v17.sync_ui_now_playing_time_remaining_to_dance_club_manager = function(_) --[[ Name: sync_ui_now_playing_time_remaining_to_dance_club_manager ]] --[[ Line: 172 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_6, (ref 3): v_u_24, (ref 4): v_u_1 ]]
            local v39, v40, v41, _ = p_u_11._dance_club_manager:get_current_song_info()
            if v_u_6:singleton():contains_key(v39) then
                v_u_24.Text = string.format("%s / %s", v_u_1:format_ms_time(v40 * 1000), v_u_1:format_ms_time(v41 * 1000))
            end;
        end;
        v17.layout = function(_) --[[ Name: layout ]] --[[ Line: 182 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_18, (ref 3): v_u_19 ]]
            p_u_12:uiobj_rescale_to_max_nxy(v_u_18, 0.5, 0.2, 1)
            v_u_18:layout()
            v_u_19:layout()
        end;
        v17:cons()
        return v17;
    end
};
