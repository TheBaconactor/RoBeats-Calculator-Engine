-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:57 PM
-- Time elapsed: 13 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_6 = require(game.ReplicatedStorage.Shared.GuildUtil)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_11 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_12 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_13 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_14 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
v15:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_19, (ref 5): v_u_20, (ref 6): v_u_21 ]]
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.GuildViewUI)
    v_u_17 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
    v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.GuildContributionLeaderboardUI)
    v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
return {
    ["new"] = function(_, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_1, (copy 3): v_u_9, (copy 4): v_u_3, (copy 5): v_u_2, (copy 6): v_u_4, (ref 7): v_u_17, (copy 8): v_u_6, (copy 9): v_u_13, (copy 10): v_u_5, (copy 11): v_u_14, (ref 12): v_u_21, (ref 13): v_u_20, (copy 14): v_u_7, (ref 15): v_u_18, (copy 16): v_u_12, (ref 17): v_u_19, (copy 18): v_u_11, (copy 19): v_u_10, (ref 20): v_u_16 ]]
        local v25 = {}
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local function f_can_claim_guild_leaderboard_buff() --[[ Name: can_claim_guild_leaderboard_buff ]] --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): p_u_23, (copy 2): p_u_22, (ref 3): v_u_8, (ref 4): v_u_1 ]]
            return v_u_8:member_playerblob_can_claim_weekly_buff(p_u_23:get_guild_data(), p_u_22._player_blob_manager:get_player_blob(), v_u_1:get_local_userid());
        end;
        v25.cons = function(p_u_35) --[[ Name: cons ]] --[[ Line: 57 ]]
            --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_27, (ref 3): v_u_26, (copy 4): p_u_22, (ref 5): v_u_9, (ref 6): v_u_28, (copy 7): p_u_23, (ref 8): v_u_3, (ref 9): v_u_2, (ref 10): v_u_4, (ref 11): v_u_1, (ref 12): v_u_8, (ref 13): v_u_17, (ref 14): v_u_6, (ref 15): v_u_30, (ref 16): v_u_13, (ref 17): v_u_29, (ref 18): v_u_5, (ref 19): v_u_14, (ref 20): v_u_21, (ref 21): v_u_20, (ref 22): v_u_7, (ref 23): v_u_34, (ref 24): v_u_31, (ref 25): v_u_18, (ref 26): v_u_32, (ref 27): v_u_12, (ref 28): v_u_33, (ref 29): v_u_19 ]]
            local l_Frame_0 = p_u_24.MainSurface.SurfaceGui.Frame
            v_u_27 = l_Frame_0.LoadedSection.ContributionSection.TimeSection.Display
            v_u_27.Text = "-"
            v_u_26 = l_Frame_0.LoadedSection.ContributionSection
            v_u_26.CurrentWeekSection.EnteredDisplay.Visible = false
            v_u_26.CurrentWeekSection.NoEntryDisplay.Visible = true
            v_u_26.LastWeekSection.EnteredDisplay.Visible = false
            v_u_26.LastWeekSection.NoEntryDisplay.Visible = true
            local l__spui_0 = p_u_22._spui
            local l__menus_0 = p_u_22._menus
            if v_u_9.HideGuildContributionUIElements == true then
                p_u_24.LastWeekContributionButtons.ContributionBuffInfoButton.Parent = nil
                p_u_24.LastWeekContributionButtons.ClaimContributionButtonBuff.Parent = nil
                p_u_24.CurrentWeekContributionButtons.EnterTeamContributionButton.Parent = nil
                p_u_24.CurrentWeekContributionButtons.ContributionInfoButton.Parent = nil
                p_u_24.CurrentWeekContributionButtons.TeamLeaderboardButton.Parent = nil
            else
                v_u_28 = p_u_23:add_cycle_element(p_u_22, 1, v_u_3:new(v_u_2:new(p_u_23, p_u_24.PrimaryPart, p_u_24.LastWeekContributionButtons.ContributionBuffInfoButton), l__spui_0, function() --[[ Line: 81 ]]
                    --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_4, (ref 3): p_u_23, (ref 4): v_u_1, (ref 5): v_u_8, (ref 6): v_u_17, (copy 7): p_u_35, (ref 8): v_u_6 ]]
                    p_u_22._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    local v36 = p_u_22._player_blob_manager:get_player_blob()
                    local v37, v38, v39 = v_u_8:member_playerblob_can_claim_weekly_buff(p_u_23:get_guild_data(), v36, (v_u_1:get_local_userid()))
                    p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Contribution Bonus Buff", string.format("Bonus Stats: %s\nActive: %s\nCan Claim: %s\nMessage: %s", p_u_35:get_bonus_buff_stat_str(), tostring(v39 <= v_u_6:playerblob_get_team_buff_weekid(v36)), tostring(v37), v38)))
                end))
                local l_Frame_1 = p_u_24.LastWeekContributionButtons.ClaimContributionButtonBuff.SurfaceGui.Frame
                v_u_30 = v_u_13:create_display_wrapper(l_Frame_1, l_Frame_1.Notification.Display)
                v_u_29 = p_u_23:add_cycle_element(p_u_22, 1, v_u_3:new(v_u_2:new(p_u_23, p_u_24.PrimaryPart, p_u_24.LastWeekContributionButtons.ClaimContributionButtonBuff), l__spui_0, function() --[[ Line: 108 ]]
                    --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_4, (ref 3): v_u_17, (ref 4): v_u_5, (ref 5): p_u_23, (copy 6): p_u_35, (ref 7): v_u_14, (ref 8): v_u_9, (ref 9): v_u_21, (ref 10): v_u_20 ]]
                    p_u_22._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    local v_u_40 = p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_22._evt:wait_on_event_once(v_u_5.EVT_Guild_ClaimContributionBuff_ServerResponse, function(p_u_41, p_u_42, p_u_43) --[[ Line: 111 ]]
                        --[[ Upvalues: (ref 1): p_u_22, (copy 2): v_u_40, (ref 3): v_u_17, (ref 4): p_u_23, (ref 5): p_u_35, (ref 6): v_u_14, (ref 7): v_u_9, (ref 8): v_u_21, (ref 9): v_u_20, (ref 10): v_u_4 ]]
                        p_u_22._player_blob_manager:do_sync(function() --[[ Line: 112 ]]
                            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_40, (copy 3): p_u_41, (ref 4): v_u_17, (copy 5): p_u_42, (ref 6): p_u_23, (ref 7): p_u_35, (ref 8): v_u_14, (copy 9): p_u_43, (ref 10): v_u_9, (ref 11): v_u_21, (ref 12): v_u_20, (ref 13): v_u_4 ]]
                            p_u_22._menus:remove_menu(v_u_40)
                            if p_u_41 ~= true then
                                return p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Error", p_u_42));
                            end;
                            p_u_23:update_state()
                            p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Contribution Bonus Activated", "The bonus buff from last week\'s contribution has been activated! It will remain active until the end of the week. \nBonus stats: " .. p_u_35:get_bonus_buff_stat_str()):set_on_close_fn(function() --[[ Line: 119 ]]
                                --[[ Upvalues: (ref 1): v_u_14, (ref 2): p_u_43, (ref 3): v_u_9, (ref 4): p_u_22, (ref 5): v_u_21, (ref 6): v_u_20 ]]
                                local v44 = v_u_14.RewardInfo:table_to_list(p_u_43)
                                if v44:count() > 0 then
                                    if v_u_9.UseRewardDescriptionInfoAcquiredUI == true then
                                        p_u_22._menus:push_menu(v_u_21:new(p_u_22, p_u_22._spui, p_u_22._menus, v44))
                                        return;
                                    end;
                                    p_u_22._menus:push_menu(v_u_20:new(p_u_22, p_u_22._spui, p_u_22._menus, v44))
                                end;
                            end))
                            p_u_22._sfx_manager:play_sfx(v_u_4.SFX_FANFARE)
                        end)
                    end)
                    p_u_22._evt:fire_event_to_server(v_u_5.EVT_Guild_ClaimContributionBuff_Client)
                end))
                v_u_3:button_add_enabled_anim(v_u_29, function() --[[ Line: 138 ]]
                    --[[ Upvalues: (ref 1): p_u_23 ]]
                    return p_u_23:get_alpha();
                end)
                v_u_7:currency_type_render_icon(v_u_6:get_guild_enter_weekly_contribution_leaderboard_cost_type(), p_u_24.CurrentWeekContributionButtons.EnterTeamContributionButton.SurfaceGui.Frame.Icon)
                v_u_34 = p_u_24.CurrentWeekContributionButtons.EnterTeamContributionButton.SurfaceGui.Frame.PriceDisplay
                v_u_34.Text = "-"
                v_u_31 = p_u_23:add_cycle_element(p_u_22, 1, v_u_3:new(v_u_2:new(p_u_23, p_u_24.PrimaryPart, p_u_24.CurrentWeekContributionButtons.EnterTeamContributionButton), l__spui_0, function() --[[ Line: 147 ]]
                    --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_4, (copy 3): l__menus_0, (ref 4): v_u_18, (copy 5): l__spui_0, (ref 6): v_u_17, (ref 7): v_u_5, (ref 8): p_u_23 ]]
                    p_u_22._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    l__menus_0:push_menu(v_u_18:new(p_u_22, l__spui_0, l__menus_0, "Select Color", "Select the color for your team bonus (claimable next week).", function(p45) --[[ Line: 152 ]]
                        --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_17, (ref 3): v_u_5, (ref 4): p_u_23, (ref 5): v_u_4 ]]
                        local v_u_46 = p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_22._evt:wait_on_event_once(v_u_5.EVT_Guild_EnterContributionWeek_ServerResponse, function(p47, p48, p49) --[[ Line: 154 ]]
                            --[[ Upvalues: (ref 1): p_u_22, (copy 2): v_u_46, (ref 3): p_u_23, (ref 4): v_u_17, (ref 5): v_u_4 ]]
                            p_u_22._menus:remove_menu(v_u_46)
                            if p47 then
                                p_u_23:set_guild_data_from_tab(p49)
                            else
                                p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Error", p48))
                            end;
                            p_u_23:update_state()
                            p_u_22._sfx_manager:play_sfx(v_u_4.SFX_ACQUIRE)
                        end)
                        p_u_22._evt:fire_event_to_server(v_u_5.EVT_Guild_EnterContributionWeek_Client, p45)
                    end))
                end))
                v_u_3:button_add_enabled_anim(v_u_31, function() --[[ Line: 169 ]]
                    --[[ Upvalues: (ref 1): p_u_23 ]]
                    return p_u_23:get_alpha();
                end)
                v_u_32 = p_u_23:add_cycle_element(p_u_22, 1, v_u_3:new(v_u_2:new(p_u_23, p_u_24.PrimaryPart, p_u_24.CurrentWeekContributionButtons.ContributionInfoButton), l__spui_0, function() --[[ Line: 174 ]]
                    --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_4, (ref 3): v_u_6, (ref 4): v_u_12, (ref 5): v_u_17 ]]
                    p_u_22._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Team Contribution Info", ((((("Earn contribution points for your team to get a week-long bonus buff to your stats for next week! The bonus stats increase the higher your team is ranked.\n\nThe following activities add contribution points:\n" .. string.format("Completing Daily Missions: %d to %d points (based on rank)\n", v_u_6:contribution_source_to_points(v_u_6.ContributionSource.DailyMissionClaim, v_u_12.Beginner), v_u_6:contribution_source_to_points(v_u_6.ContributionSource.DailyMissionClaim, v_u_12.Star))) .. string.format("Completing Weekly Missions: %d to %d points (based on rank)\n", v_u_6:contribution_source_to_points(v_u_6.ContributionSource.WeeklyMissionClaim, v_u_12.Beginner), v_u_6:contribution_source_to_points(v_u_6.ContributionSource.WeeklyMissionClaim, v_u_12.Star))) .. string.format("Claiming Leaderboard Rewards: %d to %d points (based on rank)\n", v_u_6:contribution_source_to_points(v_u_6.ContributionSource.LeaderboardClaim, 201), v_u_6:contribution_source_to_points(v_u_6.ContributionSource.LeaderboardClaim, 1))) .. string.format("Donating stars to your team: %d points each\n", v_u_6:contribution_source_to_points(v_u_6.ContributionSource.DonateStars, 1))) .. string.format("Weekly player contribution cap: %d points total\n", v_u_6:get_weekly_player_contribution_cap())) .. string.format("All participating team members will also receive Leaderboard Tickets.")))
                end))
                v_u_33 = p_u_23:add_cycle_element(p_u_22, 1, v_u_3:new(v_u_2:new(p_u_23, p_u_24.PrimaryPart, p_u_24.CurrentWeekContributionButtons.TeamLeaderboardButton), l__spui_0, function() --[[ Line: 193 ]]
                    --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_4, (ref 3): v_u_19 ]]
                    p_u_22._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                    p_u_22._menus:push_menu(v_u_19:new(p_u_22, p_u_22._spui, p_u_22._menus))
                end))
            end;
        end;
        v25.get_bonus_buff_stat_str = function(_) --[[ Name: get_bonus_buff_stat_str ]] --[[ Line: 201 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_11, (ref 3): v_u_6 ]]
            local v50 = p_u_23:get_guild_data():get_last_week_contribution_entry()
            local v51 = ""
            for v52, v53 in pairs((v_u_11:get_team_buff_statmodifierobj_for_color_and_level(v50:get_selected_color(), v_u_6:contribution_entry_to_buff_level(v50)))) do
                if #v51 > 0 then
                    v51 = v51 .. ", "
                end;
                v51 = v51 .. string.format("%s +%d", v_u_11:type_to_name(v52), v53)
            end;
            return v51;
        end;
        local function f_display_contribution_entry(p54, p55) --[[ Name: display_contribution_entry ]] --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10 ]]
            p54.TeamPointsDisplay.Text = tostring(p55:get_contribution_points())
            p54.TeamPlaceDisplay.Text = string.format("%s of %s", v_u_1:num_placify(p55:get_rank() + 1), v_u_1:comma_value(p55:get_total_entries()))
            p54.ColorIcon.Image = v_u_10:color_to_iconimage(p55:get_selected_color())
            p54.ColorIconText.Image = v_u_10:color_to_textimage(p55:get_selected_color())
        end;
        v25.update_state = function(_) --[[ Name: update_state ]] --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_23, (ref 3): v_u_16, (ref 4): v_u_28, (ref 5): v_u_29, (ref 6): v_u_31, (ref 7): v_u_32, (ref 8): v_u_33, (copy 9): p_u_22, (ref 10): v_u_26, (copy 11): f_display_contribution_entry, (copy 12): f_can_claim_guild_leaderboard_buff, (ref 13): v_u_30, (ref 14): v_u_8, (ref 15): v_u_1, (ref 16): v_u_6, (ref 17): v_u_34 ]]
            if v_u_9.HideGuildContributionUIElements == true then
                return;
            elseif p_u_23:get_current_state() == v_u_16.State.Loading then
                v_u_28:set_visible(false)
                v_u_29:set_visible(false)
                v_u_31:set_visible(false)
                v_u_32:set_visible(false)
                v_u_33:set_visible(false)
            else
                p_u_22._player_blob_manager:get_player_blob()
                local v56 = p_u_23:get_guild_data()
                local v57 = v56:get_last_week_contribution_entry()
                local l_EnteredDisplay_0 = v_u_26.LastWeekSection.EnteredDisplay
                l_EnteredDisplay_0.Visible = v57:is_entered()
                v_u_26.LastWeekSection.NoEntryDisplay.Visible = not v57:is_entered()
                if v57:is_entered() then
                    f_display_contribution_entry(l_EnteredDisplay_0, v57)
                end;
                v_u_28:set_visible(v57:is_entered())
                v_u_29:set_visible(v57:is_entered())
                v_u_29:set_enabled(f_can_claim_guild_leaderboard_buff())
                v_u_30:update_state(v_u_8:member_playerblob_can_claim_weekly_buff(p_u_23:get_guild_data(), p_u_22._player_blob_manager:get_player_blob(), v_u_1:get_local_userid()), 1)
                local v58 = v56:get_current_week_contribution_entry()
                local l_EnteredDisplay_1 = v_u_26.CurrentWeekSection.EnteredDisplay
                l_EnteredDisplay_1.Visible = v58:is_entered()
                v_u_26.CurrentWeekSection.NoEntryDisplay.Visible = not v58:is_entered()
                local v59 = v_u_8:player_has_admin_access(v56, v_u_1:get_local_userid())
                if v58:is_entered() then
                    f_display_contribution_entry(l_EnteredDisplay_1, v58)
                    v_u_31:set_visible(false)
                else
                    v_u_31:set_visible(v59)
                    v_u_31:set_enabled(v56:get_star_currency() >= v_u_6:get_guild_enter_weekly_contribution_leaderboard_cost_for_guild_data(p_u_23:get_guild_data()))
                end;
                v_u_32:set_visible(true)
                v_u_33:set_visible(true)
                v_u_34.Text = tostring(v_u_6:get_guild_enter_weekly_contribution_leaderboard_cost_for_guild_data(p_u_23:get_guild_data())) .. " (Team)"
            end;
        end;
        v25.update = function(_, _) --[[ Name: update ]] --[[ Line: 273 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_1, (copy 3): p_u_22 ]]
            v_u_27.Text = v_u_1:format_sec_time(p_u_22._guild_manager:get_time_to_next_week_sec())
        end;
        v25:cons()
        return v25;
    end
};
