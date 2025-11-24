-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Time elapsed: 14 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.MissionInfo)
require(game.ReplicatedStorage.Shared.MissionType)
local v_u_8 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_11 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_12 = require(game.ReplicatedStorage.AudioData.SelectableArtists)
local v_u_13 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v14:require_client(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17, (ref 4): v_u_18 ]]
    v_u_15 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_Shared)
    v_u_16 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_17 = require(game.ReplicatedStorage.Shared.Mission.ScaledScoreMissionUtil)
    v_u_18 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
end)
return {
    ["new"] = function(_, p_u_19, p_u_20, p_u_21, p_u_22) --[[ Name: new ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_11, (ref 6): v_u_18, (copy 7): v_u_13, (ref 8): v_u_16, (copy 9): v_u_7, (copy 10): v_u_5, (copy 11): v_u_10, (copy 12): v_u_12, (copy 13): v_u_9, (ref 14): v_u_15, (copy 15): v_u_6, (copy 16): v_u_2 ]]
        local v_u_23 = {}
        local l_Parent_0 = p_u_19:get_child_part().Parent
        local l_SurfaceGui_0 = l_Parent_0.PrimaryPart.SurfaceGui
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
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
        local v_u_42 = nil
        local v_u_43 = nil
        local v_u_44 = nil
        local v_u_45 = nil
        local l_Daily_0 = v_u_8.Daily
        local v_u_46 = 0
        local function f_cons() --[[ Name: cons ]] --[[ Line: 65 ]]
            --[[ Upvalues: (copy 1): l_SurfaceGui_0, (ref 2): v_u_29, (ref 3): v_u_30, (ref 4): v_u_31, (ref 5): v_u_32, (ref 6): v_u_33, (ref 7): v_u_34, (ref 8): v_u_35, (ref 9): v_u_36, (ref 10): v_u_37, (ref 11): v_u_38, (ref 12): v_u_39, (ref 13): v_u_40, (ref 14): v_u_41, (ref 15): v_u_42, (ref 16): v_u_1, (ref 17): v_u_43, (ref 18): v_u_24, (copy 19): p_u_22, (copy 20): p_u_20, (ref 21): v_u_4, (ref 22): v_u_3, (copy 23): p_u_19, (copy 24): l_Parent_0, (copy 25): p_u_21, (ref 26): v_u_11, (ref 27): v_u_44, (ref 28): v_u_25, (copy 29): v_u_23, (ref 30): v_u_26, (ref 31): v_u_27, (ref 32): v_u_28, (ref 33): v_u_45, (ref 34): v_u_18, (ref 35): v_u_13, (ref 36): l_Daily_0, (ref 37): v_u_16 ]]
            local l_Frame_0 = l_SurfaceGui_0.Frame
            v_u_29 = l_Frame_0.Back
            v_u_30 = l_Frame_0.CoverSection.AlbumArt
            v_u_31 = l_Frame_0.CoverSection.AlbumArtOverlay
            v_u_32 = l_Frame_0.CoverSection.ColorSection
            v_u_33 = l_Frame_0.CoverSection.SongDifficultySection
            v_u_34 = v_u_33.Display
            v_u_35 = l_Frame_0.CoverSection.ArtistIcon
            v_u_36 = l_Frame_0.Description
            v_u_37 = l_Frame_0.BarSection.ProgressBarFill
            v_u_38 = l_Frame_0.BarSection.BarText
            v_u_39 = l_Frame_0.DifficultySection.DifficultyIcon
            v_u_40 = l_Frame_0.RewardSection.CurrencyIcon
            v_u_41 = l_Frame_0.RewardSection.CurrencyDisplay
            v_u_42 = l_Frame_0.TimeSection.Display
            v_u_35.Image = v_u_1:transparent_assetid()
            v_u_43 = Vector2.new(v_u_37.Size.X.Offset, v_u_37.Size.Y.Offset)
            v_u_24 = p_u_22:add_cycle_element(p_u_20, 1, v_u_4:new(v_u_3:new(p_u_19, l_Parent_0.PrimaryPart, l_Parent_0.ClaimButton), p_u_21, function() --[[ Line: 89 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_11, (ref 3): p_u_22, (ref 4): v_u_44 ]]
                p_u_20._sfx_manager:play_sfx(v_u_11.SFX_BUTTONPRESS)
                p_u_22:claim_mission_complete_reward(v_u_44)
            end))
            v_u_4:button_add_enabled_anim(v_u_24, function() --[[ Line: 95 ]]
                --[[ Upvalues: (ref 1): p_u_22 ]]
                return p_u_22:get_alpha();
            end)
            v_u_24:set_visible(false)
            v_u_25 = p_u_22:add_cycle_element(p_u_20, 1, v_u_4:new(v_u_3:new(p_u_19, l_Parent_0.PrimaryPart, l_Parent_0.ActionButton), p_u_21, function() --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_11, (ref 3): v_u_23 ]]
                p_u_20._sfx_manager:play_sfx(v_u_11.SFX_BUTTONPRESS)
                v_u_23:mission_action_button_pressed()
            end))
            v_u_26 = v_u_25:get_part().SurfaceGui.Frame.ButtonIcon
            v_u_26.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.25
            }, v_u_26.Name)
            v_u_27 = v_u_25:get_part().SurfaceGui.Frame.Display
            v_u_1:r_set_alpha(l_Parent_0, 1)
            v_u_25:set_visible(false)
            v_u_28 = p_u_22:add_cycle_element(p_u_20, 1, v_u_4:new(v_u_3:new(p_u_19, l_Parent_0.PrimaryPart, l_Parent_0.InfoButton), p_u_21, function() --[[ Line: 115 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_11, (ref 3): v_u_45, (ref 4): v_u_18, (ref 5): v_u_13, (ref 6): l_Daily_0, (ref 7): v_u_16, (ref 8): p_u_21 ]]
                p_u_20._sfx_manager:play_sfx(v_u_11.SFX_BUTTONPRESS)
                if v_u_45 == nil then
                    return;
                elseif v_u_45:has_target_song() == true then
                    v_u_18:show_song_info_popup(p_u_20, v_u_45:get_target_song(), v_u_13:get_playerblob_mission_data_display_text(p_u_20._player_blob_manager:get_player_blob(), v_u_45, l_Daily_0, p_u_20._player_blob_manager:get_day_id()) .. "\n\n", nil, nil, {
                        ["NoDescription"] = true,
                        ["NoCollectionInfo"] = true,
                        ["NoMiscSongInfo"] = true,
                        ["TitleText"] = "Mission Info"
                    })
                else
                    p_u_20._menus:push_menu(v_u_16:new(p_u_20, p_u_21, p_u_20._menus):set_rich_text("Mission Info", v_u_13:get_playerblob_mission_data_display_text(p_u_20._player_blob_manager:get_player_blob(), v_u_45, l_Daily_0, p_u_20._player_blob_manager:get_day_id())))
                end;
            end))
        end;
        local function _() --[[ Name: update_time_remaining_display ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_1, (ref 3): v_u_46 ]]
            v_u_42.Text = v_u_1:format_sec_time(v_u_46)
        end;
        local function f_update_progress_section(p47, p48, p49) --[[ Name: update_progress_section ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_20, (ref 3): v_u_38, (ref 4): v_u_1, (ref 5): v_u_37, (ref 6): v_u_43 ]]
            local v50 = v_u_7:missiondata_get_mission_of_id_and_timeframe(p47, p49, p48)
            local v51 = v_u_7:mission_get_count(v50)
            local v52 = v_u_7:playerblob_missionid_get_count(p_u_20._player_blob_manager:get_player_blob(), p49, p48)
            v_u_38.Text = v_u_7:get_playerblob_mission_progress_text(p_u_20._player_blob_manager:get_player_blob(), v50, p49)
            v_u_37.Size = UDim2.new(0, v_u_43.X * v_u_1:clamp(v52 / v51, 0, 1), 0, v_u_43.Y)
        end;
        v_u_23.set_mission_data = function(p53, p54, p55, p56, p57) --[[ Name: set_mission_data ]] --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_44, (ref 2): v_u_8, (ref 3): v_u_29, (ref 4): v_u_1, (ref 5): v_u_46, (ref 6): v_u_7, (ref 7): v_u_45, (ref 8): v_u_13, (ref 9): l_Daily_0, (ref 10): v_u_30, (ref 11): v_u_31, (ref 12): v_u_32, (ref 13): v_u_33, (ref 14): v_u_35, (ref 15): v_u_5, (ref 16): v_u_10, (ref 17): v_u_34, (ref 18): v_u_12, (ref 19): v_u_36, (copy 20): f_update_progress_section, (ref 21): v_u_39, (ref 22): v_u_40, (copy 23): p_u_20, (ref 24): v_u_41, (ref 25): v_u_42, (ref 26): v_u_9, (ref 27): v_u_28, (ref 28): v_u_24, (ref 29): v_u_25, (ref 30): v_u_15, (ref 31): v_u_26, (ref 32): v_u_27 ]]
            v_u_44 = p55
            if p56 == v_u_8.Daily then
                v_u_29.Image = v_u_1:get_mission_box_assetid()
            elseif p56 == v_u_8.Weekly then
                v_u_29.Image = v_u_1:get_mission_box_weekly_assetid()
            end;
            v_u_46 = p57
            local v58 = v_u_7:missiondata_get_mission_of_id_and_timeframe(p54, p56, p55)
            if v58 == nil then
                v_u_45 = nil
                p53:set_visible(false)
                return p53;
            end;
            v_u_45 = v_u_13.MissionData:from_table(v58)
            l_Daily_0 = p56
            p53:set_visible(true)
            if v_u_45:has_target_song() == true then
                local v59 = v_u_45:get_target_song()
                v_u_5:singleton():render_coverimage_for_key(v_u_30, v_u_31, v59)
                v_u_10:render_songkey_colorsection(v59, v_u_32)
                v_u_33.Visible = true
                v_u_34.Text = v_u_5:singleton():get_difficulty_for_key(v59)
                v_u_34.TextColor3 = v_u_5:singleton():get_difficulty_color_for_key(v59)
                local v60, v61 = v_u_12:artist_name_is_selectable((v_u_5:singleton():get_artist_for_key(v59)))
                if v60 then
                    local v62 = v_u_12:artist_name_to_icon(v61)
                    if #v62 > 0 then
                        v_u_35.Image = v62
                    else
                        v_u_35.Image = v_u_1:transparent_assetid()
                    end;
                else
                    v_u_35.Image = v_u_1:transparent_assetid()
                end;
            else
                v_u_7:render_placeholder_cover_art(v58, v_u_30, v_u_31)
                v_u_32.Visible = false
                v_u_33.Visible = false
                v_u_35.Image = v_u_1:transparent_assetid()
            end;
            v_u_36.Text = v_u_7:get_mission_description_text(v58)
            f_update_progress_section(p54, p55, p56)
            v_u_7:render_difficulty_image(v_u_39, v_u_45:get_difficulty())
            v_u_40.Image = v_u_45:get_reward_image()
            v_u_41.Text = v_u_45:get_reward_display_amount_for_playerblob_and_timeframe(p_u_20._player_blob_manager:get_player_blob(), p56)
            v_u_42.Text = v_u_1:format_sec_time(v_u_46)
            local v63 = v_u_9.MissionDebugAlwaysClaim == true and true or v_u_7:playerblob_missiondata_missionid_is_completeable(p_u_20._player_blob_manager:get_player_blob(), p54, p56, v_u_7:mission_get_id(v58))
            v_u_28:set_visible(true)
            if v63 == true then
                v_u_24:set_visible(true)
                v_u_24:set_enabled(true)
                v_u_24:set_passive_anim(true)
                v_u_25:set_visible(false)
                return p53;
            end;
            v_u_24:set_passive_anim(false)
            if not v_u_45:has_target_song() then
                v_u_24:set_visible(true)
                v_u_24:set_enabled(false)
                v_u_25:set_visible(false)
                return p53;
            end;
            v_u_24:set_visible(false)
            v_u_25:set_visible(true)
            local v64 = v_u_45:get_target_song()
            local l_DailyMission_0 = v_u_15.RecommendationType.DailyMission
            if p56 == v_u_8.Weekly then
                l_DailyMission_0 = v_u_15.RecommendationType.WeeklyMission
            end;
            local v65 = v_u_15:get_recommendation_button_action_data_for_songkey(p_u_20, v64, l_DailyMission_0, {})
            v_u_26.Image = v65.IconImage
            v_u_27.Image = v65.TextImage
            v_u_25:bind_data(v65)
            return p53;
        end;
        v_u_23.mission_action_button_pressed = function(_) --[[ Name: mission_action_button_pressed ]] --[[ Line: 276 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_6, (ref 3): v_u_15, (copy 4): p_u_20 ]]
            local v66 = v_u_25:get_bound_data()
            if v66 == nil then
                return v_u_6:warnf("MissionDisplayElement:mission_action_button");
            end;
            v_u_15:perform_selected_button_action(p_u_20, v66.SelectedButtonAction, v66.SelectedButtonSongkey, v66.SelectedButtonData)
        end;
        v_u_23.set_visible = function(p67, p68) --[[ Name: set_visible ]] --[[ Line: 287 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_28, (copy 4): l_SurfaceGui_0 ]]
            if p68 == false then
                v_u_24:set_visible(false)
                v_u_25:set_visible(false)
                v_u_28:set_visible(false)
            end;
            l_SurfaceGui_0.Enabled = p68
            return p67;
        end;
        v_u_23.behaviour_update = function(_, p69) --[[ Name: behaviour_update ]] --[[ Line: 297 ]]
            --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_2, (ref 3): v_u_42, (ref 4): v_u_1 ]]
            v_u_46 = math.max(v_u_46 - v_u_2:TimescaleToDeltaTime(p69), 0)
            v_u_42.Text = v_u_1:format_sec_time(v_u_46)
        end;
        v_u_23.layout = function(_) --[[ Name: layout ]] --[[ Line: 302 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            p_u_19:layout()
        end;
        f_cons()
        return v_u_23;
    end
};
