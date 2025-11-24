-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:46 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_10 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_12 = require(game.ReplicatedStorage.Lobby.Dialogue.GuildDialogue)
local v_u_13 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_14 = require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
local v_u_15 = require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
local v16 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_17 = nil
local v_u_18 = nil
v16:require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18 ]]
    v_u_17 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
end)
local v_u_25 = {
    ["show_guild_data_popup"] = function(_, p19, p20) --[[ Name: show_guild_data_popup ]] --[[ Line: 293 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_1, (ref 3): v_u_17 ]]
        if p20 ~= nil then
            local v21 = string.format("Team: %s", p20:get_name())
            local v22 = v_u_11:get_owner(p20)
            local v23 = v22 == nil and "-" or v22:get_name()
            local v24 = p20:get_current_week_contribution_entry()
            p19._menus:push_menu(v_u_17:new(p19, p19._spui, p19._menus):set_text(v21, (string.format("Owner: %s\nContribution Points: %s\nRank: %s\nMembers: %d\nMessage: %s", v23, v_u_1:comma_value(v24:get_contribution_points()), v_u_1:num_placify(v24:get_rank() + 1), p20:get_member_infos():count(), p20:get_message()))))
        end;
    end
}
v_u_25.new = function(_, p_u_26, p_u_27, p_u_28) --[[ Name: new ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_9, (copy 4): v_u_1, (copy 5): v_u_12, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_6, (copy 9): v_u_25, (copy 10): v_u_15, (copy 11): v_u_14, (copy 12): v_u_10, (copy 13): v_u_11, (copy 14): v_u_7, (copy 15): v_u_13, (copy 16): v_u_8 ]]
    local v_u_29 = v_u_3:new(p_u_27, p_u_28)
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = v_u_2:new()
    local v_u_33 = v_u_2:new()
    local v_u_36 = v_u_9:new():set_fn_get_data_list(function() --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end):set_fn_set_element_data(function(p34, p35) --[[ Line: 40 ]]
        if p35 == nil then
            p34:set_visible(false)
        else
            p34:set_visible(true)
            p34:set_display_element(p35)
        end;
    end)
    local v_u_37 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_1, (copy 3): v_u_29, (ref 4): v_u_31, (ref 5): v_u_12, (copy 6): p_u_26, (ref 7): v_u_37, (ref 8): v_u_5, (ref 9): v_u_4, (copy 10): p_u_27, (ref 11): v_u_6, (copy 12): p_u_28, (ref 13): v_u_25, (ref 14): v_u_15, (ref 15): v_u_14, (ref 16): v_u_9, (ref 17): v_u_10, (ref 18): v_u_11, (copy 19): v_u_36, (copy 20): v_u_32, (ref 21): v_u_7, (ref 22): v_u_33 ]]
        v_u_30 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Guild.GuildContributionLeaderboardUI:Clone()
        v_u_30.Name = v_u_1:gen_name(v_u_30.Name)
        v_u_29:set_showing(true)
        v_u_29._native_size = v_u_30.PrimaryPart.Size
        v_u_29._size = v_u_29._native_size
        v_u_31 = v_u_12:new(p_u_26, v_u_29, v_u_29, v_u_30)
        local l_Frame_0 = v_u_30.PrimaryPart.SurfaceGui.Frame
        v_u_37 = l_Frame_0.LoadedSection.TimeSection.Display
        v_u_37.Text = "-"
        local l_NotEnteredDisplay_0 = l_Frame_0.LoadedSection.NotEnteredDisplay
        l_NotEnteredDisplay_0.Visible = false
        v_u_29:add_cycle_element(p_u_26, 1, v_u_5:new(v_u_4:new(v_u_29, v_u_30.PrimaryPart, v_u_30.BackButtonSurface), p_u_27, function() --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_6, (ref 3): p_u_28, (ref 4): v_u_29 ]]
            p_u_26._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_28:remove_menu(v_u_29)
        end))
        v_u_29:add_cycle_element(p_u_26, 1, v_u_5:new(v_u_4:new(v_u_29, v_u_30.PrimaryPart, v_u_30.LastWeekButton), p_u_27, function() --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_6, (ref 3): v_u_25 ]]
            p_u_26._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
            v_u_25:show_last_week_leaderboard(p_u_26)
        end))
        v_u_29:add_cycle_element(p_u_26, 1, v_u_5:new(v_u_4:new(v_u_29, v_u_30.PrimaryPart, v_u_30.ChatButton), p_u_27, function() --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_6, (ref 3): v_u_15, (ref 4): v_u_14 ]]
            p_u_26._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
            v_u_15:show_chat_menu(p_u_26, v_u_14.Category.CurrentGuildContributionWeeklyLeaderboard, "", function(p38, _) --[[ Line: 90 ]]
                --[[ Upvalues: (ref 1): p_u_26 ]]
                p38:set_header_text(string.format("Team Contribution Leaderboard Chat (Current Week - %d)", p_u_26._player_blob_manager:get_week_id()))
            end)
        end))
        local function v47(p_u_39) --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_29, (ref 3): v_u_30, (ref 4): p_u_26, (ref 5): v_u_5, (ref 6): v_u_4, (ref 7): v_u_6, (ref 8): v_u_25, (ref 9): v_u_1, (ref 10): v_u_10, (ref 11): v_u_11 ]]
            local l_Frame_1 = p_u_39.PrimaryPart.SurfaceGui.Frame
            local l_Bubble_0 = l_Frame_1.Bubble
            local l_PlaceDisplay_0 = l_Bubble_0.PlaceDisplay
            local l_TeamIconDisplay_0 = l_Frame_1.TeamIconDisplay
            local l_NameDisplay_0 = l_Frame_1.NameDisplay
            local l_CurrentWeekContributionPointsDisplay_0 = l_Frame_1.CurrentWeekContributionPointsDisplay
            local v_u_40 = nil
            local v_u_41 = nil
            return v_u_9.DisplayElement:new(v_u_29, v_u_30.PrimaryPart, p_u_39, function(p42) --[[ Line: 106 ]]
                --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_29, (ref 3): p_u_26, (ref 4): v_u_5, (ref 5): v_u_4, (copy 6): p_u_39, (ref 7): v_u_6, (ref 8): v_u_25, (ref 9): v_u_41 ]]
                v_u_40 = v_u_29:add_cycle_element(p_u_26, 1, v_u_5:new(v_u_4:new(p42:get_uichild(), p_u_39.PrimaryPart, p_u_39.InfoButtonSurface), p_u_26._spui, function() --[[ Line: 110 ]]
                    --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_6, (ref 3): v_u_25, (ref 4): v_u_41 ]]
                    p_u_26._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    v_u_25:show_guild_data_popup(p_u_26, v_u_41)
                end))
            end):set_fn_set_display_element(function(p43) --[[ Line: 117 ]]
                --[[ Upvalues: (ref 1): v_u_41, (copy 2): l_Bubble_0, (copy 3): l_PlaceDisplay_0, (ref 4): v_u_1, (ref 5): v_u_10, (copy 6): l_CurrentWeekContributionPointsDisplay_0, (ref 7): v_u_11, (copy 8): l_TeamIconDisplay_0, (copy 9): l_NameDisplay_0 ]]
                v_u_41 = p43
                if p43 ~= nil then
                    local v44 = v_u_41:get_current_week_contribution_entry()
                    if v44:is_entered() then
                        l_Bubble_0.Visible = true
                        l_PlaceDisplay_0.Text = v_u_1:num_placify(v44:get_rank() + 1)
                        local v45 = v_u_10:contribution_entry_to_buff_level(v44)
                        if v45 == 6 then
                            l_Bubble_0.Image = v_u_1:get_leaderboard_bubble_gold_assetid()
                        elseif v45 == 5 or v45 == 4 then
                            l_Bubble_0.Image = v_u_1:get_leaderboard_bubble_silver_assetid()
                        elseif v45 == 3 then
                            l_Bubble_0.Image = v_u_1:get_leaderboard_bubble_bronze_assetid()
                        else
                            l_Bubble_0.Image = v_u_1:get_leaderboard_bubble_none_assetid()
                        end;
                        l_CurrentWeekContributionPointsDisplay_0.Text = v_u_1:comma_value(v44:get_contribution_points())
                    else
                        l_Bubble_0.Visible = false
                        l_CurrentWeekContributionPointsDisplay_0.Text = "-"
                    end;
                    v_u_11:render_guild_icon(v_u_41, l_TeamIconDisplay_0)
                    l_NameDisplay_0.Text = v_u_41:get_name()
                end;
            end):set_fn_set_visible(function(p46) --[[ Line: 142 ]]
                --[[ Upvalues: (ref 1): v_u_40 ]]
                v_u_40:set_visible(p46)
            end);
        end;
        local l_Anchors_0 = v_u_30.Anchors
        v_u_36:create_list_elements_from_anchors_and_proto({
            l_Anchors_0.Anchor1,
            l_Anchors_0.Anchor2,
            l_Anchors_0.Anchor3,
            l_Anchors_0.Anchor4,
            l_Anchors_0.Anchor5,
            l_Anchors_0.Anchor6,
            l_Anchors_0.Anchor7,
            l_Anchors_0.Anchor8,
            l_Anchors_0.Anchor9,
            l_Anchors_0.Anchor10,
            l_Anchors_0.Anchor11,
            l_Anchors_0.Anchor12,
            l_Anchors_0.Anchor13,
            l_Anchors_0.Anchor14,
            l_Anchors_0.Anchor15
        }, v_u_30.ListElementProto, v_u_30, v47)
        v_u_36:set_visible(false)
        l_Frame_0.LoadingSection.Visible = true
        l_Frame_0.LoadedSection.Visible = false
        local v_u_48 = v47(v_u_30.YourTeamDisplay)
        v_u_32:push_back(v_u_48)
        local v_u_49 = v47(v_u_30.NextTeamDisplay)
        v_u_32:push_back(v_u_49)
        local v_u_50 = v47(v_u_30.PrevTeamDisplay)
        v_u_32:push_back(v_u_50)
        for _, v51 in v_u_32:key_itr() do
            v51:set_visible(false)
        end;
        p_u_26._evt:wait_on_event_once(v_u_7.EVT_Guild_GetLeaderboardInfo_ServerResponse, function(p52, p53) --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_29, (copy 3): l_Frame_0, (ref 4): v_u_33, (ref 5): v_u_11, (ref 6): v_u_36, (ref 7): p_u_26, (copy 8): v_u_48, (copy 9): v_u_49, (copy 10): v_u_50, (copy 11): l_NotEnteredDisplay_0 ]]
            if p_u_28:contains_menu(v_u_29) == true then
                l_Frame_0.LoadingSection.Visible = false
                l_Frame_0.LoadedSection.Visible = true
                v_u_33 = v_u_11:table_list_to_list(p52)
                v_u_36:page_update()
                if p_u_26._guild_manager:player_has_guild() then
                    if p53.YourTeam == nil then
                        l_NotEnteredDisplay_0.Visible = true
                        l_NotEnteredDisplay_0.Text = "Your team is not entered in this week\'s competition."
                        return;
                    end;
                    local v54 = v_u_11:from_table(p53.YourTeam)
                    v_u_48:set_visible(true)
                    v_u_48:set_display_element(v54)
                    if p53.NextTeam ~= nil then
                        v_u_49:set_visible(true)
                        v_u_49:set_display_element(v_u_11:from_table(p53.NextTeam))
                    end;
                    if p53.PrevTeam ~= nil then
                        v_u_50:set_visible(true)
                        v_u_50:set_display_element(v_u_11:from_table(p53.PrevTeam))
                        return;
                    end;
                else
                    l_NotEnteredDisplay_0.Visible = true
                    l_NotEnteredDisplay_0.Text = "You are not in a team."
                end;
            end;
        end)
        p_u_26._evt:fire_event_to_server(v_u_7.EVT_Guild_GetLeaderboardInfo_Client)
        v_u_29:transition_update_visual(0)
        v_u_29:layout()
    end;
    v_u_29.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 218 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        v_u_30:Destroy()
    end;
    v_u_29.behaviour_update = function(p55, p56, p57) --[[ Name: behaviour_update ]] --[[ Line: 222 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_1, (copy 3): p_u_26, (ref 4): v_u_13, (ref 5): v_u_31 ]]
        p55:behaviour_update_base(p56, p57)
        v_u_37.Text = v_u_1:format_sec_time(p_u_26._guild_manager:get_time_to_next_week_sec())
        if p55._current_mode == v_u_13.MODE_OPEN then
            v_u_31:update(p56)
        end;
    end;
    v_u_29.visual_update = function(p58, p59, p60) --[[ Name: visual_update ]] --[[ Line: 230 ]]
        --[[ Upvalues: (copy 1): p_u_26 ]]
        if p_u_26:transition_local_camera_cframe_finished() ~= false then
            p58:visual_update_base(p59, p60)
        end;
    end;
    local v_u_61 = 1
    local v_u_62 = 1
    v_u_29.layout = function(p63) --[[ Name: layout ]] --[[ Line: 239 ]]
        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_62, (ref 3): v_u_30, (copy 4): v_u_36, (copy 5): v_u_32, (ref 6): v_u_31 ]]
        p63:opt_rescale_to_max_nxy(p_u_27, 0.8, 0.8, v_u_62)
        local v64, v65 = p63:opt_update_cframe_params(p_u_27, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p63:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v64 == true then
            v_u_30:SetPrimaryPartCFrame(v65)
        end;
        v_u_36:layout()
        for _, v66 in v_u_32:key_itr() do
            v66:layout()
        end;
        v_u_31:layout()
    end;
    v_u_29.set_alpha = function(_, p67) --[[ Name: set_alpha ]] --[[ Line: 255 ]]
        --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_1, (ref 3): v_u_30 ]]
        if v_u_61 ~= p67 then
            v_u_61 = p67
            v_u_1:r_set_alpha(v_u_30, v_u_61)
        end;
    end;
    v_u_29.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 261 ]]
        --[[ Upvalues: (ref 1): v_u_61 ]]
        return v_u_61;
    end;
    v_u_29.set_scale = function(_, p68) --[[ Name: set_scale ]] --[[ Line: 262 ]]
        --[[ Upvalues: (ref 1): v_u_62 ]]
        v_u_62 = p68
    end;
    v_u_29.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 263 ]]
        --[[ Upvalues: (ref 1): v_u_62 ]]
        return v_u_62;
    end;
    v_u_29.get_native_size = function(p69) --[[ Name: get_native_size ]] --[[ Line: 265 ]]
        return p69._native_size;
    end;
    v_u_29.get_size = function(p70) --[[ Name: get_size ]] --[[ Line: 268 ]]
        return p70._size;
    end;
    v_u_29.set_size = function(p71, p72) --[[ Name: set_size ]] --[[ Line: 271 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        p71._size = p72
        v_u_30.PrimaryPart.Size = Vector3.new(p72.X, p72.Y, 0)
    end;
    v_u_29.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 275 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30.PrimaryPart.Position;
    end;
    v_u_29.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 278 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30.PrimaryPart.SurfaceGui;
    end;
    v_u_29.set_showing = function(_, p73) --[[ Name: set_showing ]] --[[ Line: 281 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_8 ]]
        if p73 then
            v_u_30.Parent = v_u_8:get_world_ui_folder()
        else
            v_u_30.Parent = nil
        end;
    end;
    f_cons()
    return v_u_29;
end;
v_u_25.show_last_week_leaderboard = function(_, p_u_74) --[[ Name: show_last_week_leaderboard ]] --[[ Line: 317 ]]
    --[[ Upvalues: (ref 1): v_u_17, (copy 2): v_u_7, (copy 3): v_u_11, (ref 4): v_u_18, (copy 5): v_u_1, (copy 6): v_u_25, (copy 7): v_u_2, (copy 8): v_u_5, (copy 9): v_u_15, (copy 10): v_u_14 ]]
    local v_u_75 = p_u_74._menus:push_menu(v_u_17:new(p_u_74, p_u_74._spui, p_u_74._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_74._evt:wait_on_event_once(v_u_7.EVT_Guild_GetLastWeekLeaderboardInfo_ServerResponse, function(p76) --[[ Line: 319 ]]
        --[[ Upvalues: (copy 1): p_u_74, (copy 2): v_u_75, (ref 3): v_u_11, (ref 4): v_u_18, (ref 5): v_u_1, (ref 6): v_u_25, (ref 7): v_u_2, (ref 8): v_u_5, (ref 9): v_u_15, (ref 10): v_u_14 ]]
        p_u_74._menus:remove_menu(v_u_75)
        local v_u_77 = v_u_11:table_list_to_list(p76)
        local v85 = p_u_74._menus:push_menu(v_u_18:new(p_u_74, p_u_74._spui, p_u_74._menus, function(p78) --[[ Line: 326 ]]
            --[[ Upvalues: (ref 1): p_u_74, (copy 2): v_u_77 ]]
            p78:set_header_text(string.format("Team Contribution Leaderboard (Last Week - %d)", p_u_74._player_blob_manager:get_week_id() - 1))
            p78:get_element_list():push_back_from_list(v_u_77)
        end, function(p79, p80, p81, _, p82, p83, _) --[[ Line: 330 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            p80.Text = string.format("[%s] %s", v_u_1:num_placify(p83), p79:get_name())
            p82:get_description_display().Text = string.format("%s Points", v_u_1:comma_value(p79:get_current_week_contribution_entry():get_contribution_points()))
            p81.Image = p79:get_icon()
        end, function(p84) --[[ Line: 335 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): p_u_74 ]]
            if p84 ~= nil then
                v_u_25:show_guild_data_popup(p_u_74, p84)
            end;
        end)):set_close_on_element_select(false)
        v85:get_list_adapter():set_do_wrap(true)
        v85:set_settings_section_visible()
        local v89 = v_u_2:new():push_back_table_list({ function(p86) --[[ Line: 345 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_15, (ref 3): p_u_74, (ref 4): v_u_14 ]]
                v_u_5:set_button_text(p86, "\240\159\146\172 View Messages")
                p86:bind_data(function() --[[ Line: 347 ]]
                    --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_74, (ref 3): v_u_14 ]]
                    v_u_15:show_chat_menu(p_u_74, v_u_14.Category.LastGuildContributionWeeklyLeaderboard, "", function(p87, p88) --[[ Line: 348 ]]
                        --[[ Upvalues: (ref 1): p_u_74 ]]
                        p87:set_header_text(string.format("Team Contribution Leaderboard Chat Archive (Last Week - %d)", p_u_74._player_blob_manager:get_week_id() - 1))
                        p88.NoChatButton = true
                    end)
                end)
            end })
        for _, v90 in v85:get_settings_buttons():key_itr() do
            if v89:count() > 0 then
                v90:set_visible(true)
                v89:pop_front()(v90)
            else
                v90:set_visible(false)
            end;
        end;
    end)
    p_u_74._evt:fire_event_to_server(v_u_7.EVT_Guild_GetLastWeekLeaderboardInfo_Client)
end;
return v_u_25;
