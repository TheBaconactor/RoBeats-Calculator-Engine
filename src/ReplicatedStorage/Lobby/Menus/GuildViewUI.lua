-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:45 PM
-- Time elapsed: 23 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_14 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_15 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_16 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_18 = require(game.ReplicatedStorage.Shared.GuildBonusUtil)
local v_u_19 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_20 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_21 = require(game.ReplicatedStorage.Shared.GuildMessage)
local v22 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
local v_u_26 = nil
local v_u_27 = nil
local v_u_28 = nil
local v_u_29 = nil
v22:require_client(function() --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24, (ref 3): v_u_25, (ref 4): v_u_26, (ref 5): v_u_27, (ref 6): v_u_28, (ref 7): v_u_29 ]]
    v_u_23 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.UI.Guild.GuildViewMemberDisplayElement)
    v_u_25 = require(game.ReplicatedStorage.Lobby.UI.Guild.GuildViewContributionSection)
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.PlayerSelectUI)
    v_u_27 = require(game.ReplicatedStorage.Lobby.UI.Guild.GuildChatMenu)
    v_u_28 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
    v_u_29 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
end)
local v30 = {
    ["State"] = {
        ["Loading"] = 0,
        ["Loaded"] = 1
    }
}
local v_u_31 = {
    ["Loading"] = 0,
    ["Loaded"] = 1
}
v30.new = function(_, p_u_32, p_u_33, p_u_34) --[[ Name: new ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_31, (copy 3): v_u_14, (copy 4): v_u_11, (copy 5): v_u_3, (copy 6): v_u_1, (copy 7): v_u_15, (ref 8): v_u_25, (copy 9): v_u_6, (copy 10): v_u_5, (copy 11): v_u_8, (ref 12): v_u_29, (copy 13): v_u_7, (ref 14): v_u_23, (copy 15): v_u_9, (ref 16): v_u_27, (copy 17): v_u_17, (copy 18): v_u_18, (ref 19): v_u_26, (copy 20): v_u_12, (copy 21): v_u_2, (copy 22): v_u_21, (copy 23): v_u_19, (copy 24): v_u_16, (ref 25): v_u_28, (copy 26): v_u_13, (ref 27): v_u_24, (copy 28): v_u_20, (copy 29): v_u_10 ]]
    local v_u_35 = v_u_4:new(p_u_33, p_u_34)
    local l_Loading_0 = v_u_31.Loading
    v_u_35.set_current_state_loaded = function(_) --[[ Name: set_current_state_loaded ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_31 ]]
        l_Loading_0 = v_u_31.Loaded
    end;
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = v_u_14:new(v_u_11:not_in_guild_id())
    v_u_35.set_guild_data_from_tab = function(_, p39) --[[ Name: set_guild_data_from_tab ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_14, (ref 3): v_u_11 ]]
        if p39 then
            v_u_38 = v_u_14:from_table(p39)
        else
            v_u_38 = v_u_14:new(v_u_11:not_in_guild_id())
        end;
    end;
    v_u_35.get_guild_data = function(_) --[[ Name: get_guild_data ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): l_Loading_0 ]]
        return v_u_38, l_Loading_0;
    end;
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = v_u_3:new()
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = nil
    local function f_list_display_element_member_info_update_status_display(p51, p52) --[[ Name: list_display_element_member_info_update_status_display ]] --[[ Line: 80 ]]
        --[[ Upvalues: (copy 1): p_u_32, (ref 2): v_u_1, (ref 3): v_u_11 ]]
        local v53 = false
        if p51 and p52 then
            local v54 = p_u_32._guild_manager:get_status_dict()
            if p52:get_rbxid() == v_u_1:get_local_userid() then
                p51:set_status(v_u_11.Status.OnlineSameServer)
                return v53;
            end;
            if v54:contains(p52:get_rbxid()) == true then
                p51:set_status(v54:get(p52:get_rbxid()))
                return v53;
            end;
            p51:set_status_loading()
            v53 = true
        end;
        return v53;
    end;
    local v_u_61 = v_u_15:new():set_fn_get_data_list(function() --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38:get_member_infos();
    end):set_fn_set_element_data(function(p55, p56) --[[ Line: 98 ]]
        --[[ Upvalues: (copy 1): f_list_display_element_member_info_update_status_display ]]
        if p56 == nil then
            p55:set_visible(false)
        else
            p55:set_visible(true)
            p55:set_display_element(p56)
            f_list_display_element_member_info_update_status_display(p55, p56)
        end;
    end):set_fn_next_prev_visible(function(p57, p58) --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_40 ]]
        v_u_41:set_visible(p57)
        v_u_40:set_visible(p58)
    end):set_fn_update_page_display(function(p59, p60) --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        v_u_42.Text = string.format("%d/%d", p59, p60)
    end)
    local function _() --[[ Name: refresh_all_player_status_displays ]] --[[ Line: 116 ]]
        --[[ Upvalues: (copy 1): v_u_61, (copy 2): f_list_display_element_member_info_update_status_display ]]
        v_u_61:refresh_element_data(f_list_display_element_member_info_update_status_display)
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 120 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_1, (copy 3): v_u_35, (ref 4): v_u_37, (copy 5): p_u_32, (ref 6): v_u_42, (ref 7): v_u_43, (ref 8): v_u_50, (ref 9): v_u_25, (ref 10): v_u_6, (ref 11): v_u_5, (copy 12): p_u_33, (ref 13): v_u_8, (copy 14): p_u_34, (copy 15): v_u_44, (ref 16): v_u_29, (ref 17): v_u_11, (ref 18): v_u_38, (ref 19): v_u_7, (ref 20): v_u_23, (ref 21): v_u_9, (ref 22): l_Loading_0, (ref 23): v_u_31, (ref 24): v_u_27, (ref 25): v_u_17, (ref 26): v_u_18, (ref 27): v_u_26, (ref 28): v_u_14, (ref 29): v_u_12, (ref 30): v_u_2, (ref 31): v_u_21, (ref 32): v_u_45, (ref 33): v_u_46, (ref 34): v_u_49, (ref 35): v_u_19, (ref 36): v_u_48, (ref 37): v_u_16, (ref 38): v_u_47, (ref 39): v_u_28, (ref 40): v_u_13, (ref 41): v_u_41, (copy 42): v_u_61, (ref 43): v_u_40, (ref 44): v_u_24 ]]
        v_u_36 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Guild.GuildViewUI:Clone()
        v_u_36.Name = v_u_1:gen_name(v_u_36.Name)
        v_u_35:set_showing(true)
        v_u_37 = v_u_36.MainSurface.SurfaceGui.Frame
        p_u_32._guild_manager:get_status_dict():clear()
        v_u_35._native_size = v_u_36.PrimaryPart.Size
        v_u_35._size = v_u_35._native_size
        v_u_42 = v_u_37.LoadedSection.MemberListPageDisplay
        v_u_43 = v_u_37.LoadedSection.MemberListHeaderText
        v_u_50 = v_u_25:new(p_u_32, v_u_35, v_u_36)
        v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.BackButtonSurface), p_u_33, function() --[[ Line: 140 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): p_u_34, (ref 4): v_u_35 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            p_u_34:remove_menu(v_u_35)
        end))
        v_u_44:push_back(v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.InfoButtons.EditMessageButton), p_u_33, function() --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_29, (ref 4): v_u_11, (ref 5): v_u_38, (ref 6): v_u_7, (ref 7): v_u_23, (ref 8): v_u_9, (ref 9): v_u_35, (ref 10): l_Loading_0, (ref 11): v_u_31 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_29:show_text_input_box_ui(p_u_32, "Edit Team Message", string.format("Update this Team\'s displayed message (Max %d characters).\nYour message will be run through roblox moderation.", v_u_11:guild_message_max_length()), v_u_38:get_message(), function(p62) --[[ Line: 158 ]]
                --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_7, (ref 3): p_u_32, (ref 4): v_u_23, (ref 5): v_u_9, (ref 6): v_u_35, (ref 7): l_Loading_0, (ref 8): v_u_31 ]]
                if p62 == v_u_38:get_message() then
                    return v_u_7:puts("Guild message was not changed, not updating.");
                end;
                local v_u_63 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_UpdateGuildMessage_ServerResponse, function(p64, p65, p66) --[[ Line: 161 ]]
                    --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_63, (ref 3): v_u_35, (ref 4): v_u_7, (ref 5): l_Loading_0, (ref 6): v_u_31 ]]
                    p_u_32._menus:remove_menu(v_u_63)
                    if p64 then
                        v_u_35:set_guild_data_from_tab(p66)
                    else
                        v_u_7:warnf(p65)
                    end;
                    l_Loading_0 = v_u_31.Loaded
                    v_u_35:update_state()
                end)
                p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_UpdateGuildMessage_Client, p62)
            end):set_text_box_empty_text("New Team Message"):set_max_length(v_u_11:guild_message_max_length())
        end)))
        v_u_44:push_back(v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.InfoButtons.EditIconButton), p_u_33, function() --[[ Line: 180 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_27, (ref 4): p_u_33, (ref 5): p_u_34, (ref 6): v_u_35 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_27:show_guild_edit_icon_menu(p_u_32, p_u_33, p_u_34, v_u_35)
        end)))
        local function f_show_admin_purchase_guild_bonus_menu() --[[ Name: show_admin_purchase_guild_bonus_menu ]] --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): p_u_34, (ref 2): v_u_17, (ref 3): p_u_32, (ref 4): p_u_33, (ref 5): v_u_38, (ref 6): v_u_18, (ref 7): v_u_23, (ref 8): v_u_9, (ref 9): v_u_35, (ref 10): v_u_8 ]]
            p_u_34:push_menu(v_u_17:new(p_u_32, p_u_33, p_u_34, function(p67) --[[ Line: 189 ]]
                --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_18 ]]
                p67:set_header_text(string.format("Purchase Team Bonuses"))
                p67:set_sub_text(string.format("(Team Stars: %d)", v_u_38:get_star_currency()))
                local v68 = p67:get_element_list()
                for _, v69 in v_u_18:get_bonus_info_list():key_itr() do
                    v68:push_back(v69)
                end;
            end, function(p70, p71, p72, _, p73) --[[ Line: 197 ]]
                --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_38, (ref 3): p_u_32 ]]
                p71.Text = string.format("%s", p70:get_name())
                if v_u_18:guild_data_can_activate_bonus_id_for_weekid(v_u_38, p70:get_bonus_id(), p_u_32._player_blob_manager:get_weekid()) == true then
                    p73:get_description_display().Text = string.format("Cost: %d Stars", v_u_18:guild_data_get_bonus_id_price(v_u_38, p70:get_bonus_id()))
                else
                    p73:get_description_display().Text = "Active"
                end;
                p72.Image = p70:get_icon()
                local v74 = v_u_18:guild_data_can_activate_bonus_id_for_weekid(v_u_38, p70:get_bonus_id(), p_u_32._player_blob_manager:get_weekid()) == true
                if v_u_38:get_star_currency() < v_u_18:guild_data_get_bonus_id_price(v_u_38, p70:get_bonus_id()) then
                    v74 = false
                end;
                p73:set_select_button_enabled(v74)
            end, function(p75) --[[ Line: 218 ]]
                --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_23, (ref 3): v_u_9, (ref 4): v_u_35, (ref 5): v_u_18, (ref 6): v_u_38, (ref 7): v_u_8 ]]
                if p75 ~= nil then
                    local v_u_76 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_AddGuildBonus_ServerResponse, function(p77, p78, p79) --[[ Line: 221 ]]
                        --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_76, (ref 3): v_u_23, (ref 4): v_u_35, (ref 5): v_u_18, (ref 6): v_u_38, (ref 7): v_u_8 ]]
                        p_u_32._menus:remove_menu(v_u_76)
                        if p77 ~= true then
                            return p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Failed", p78));
                        end;
                        if p79 then
                            v_u_35:set_guild_data_from_tab(p79)
                        end;
                        v_u_35:update_state()
                        local v80 = ""
                        for v81, _ in v_u_18:guild_data_get_active_bonus_ids_set_for_weekid(v_u_38, p_u_32._player_blob_manager:get_weekid()):key_itr() do
                            v80 = v80 .. v_u_18:get_bonus_info_for_id(v81):get_name() .. "\n"
                        end;
                        p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Purchased Team Bonus", "This bonus will be active for the rest of the week.\nActive Team Bonuses:\n" .. v80))
                        p_u_32._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                    end)
                    p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_AddGuildBonus_Client, p75:get_bonus_id())
                end;
            end):set_fn_info_button_pressed(function() --[[ Line: 245 ]]
                --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_23 ]]
                p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Info: Purchase Team Bonus", "Admins can purchase \'Team Bonuses\' using Team Stars that will be available to team members for the duration of the week. Only team members who have been in the team for at least 1 week will be able to activate these bonuses. Team bonus price will be scaled based off number of eligible team members."))
            end))
        end;
        local function f_show_admin_invite_players_menu() --[[ Name: show_admin_invite_players_menu ]] --[[ Line: 254 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_23, (ref 4): p_u_34, (ref 5): v_u_26, (ref 6): p_u_33, (ref 7): v_u_9 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            local v_u_82 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_34:push_menu(v_u_26:new(p_u_32, p_u_33, p_u_34, function(p83) --[[ Line: 258 ]]
                p83:fill_players_list(false)
            end, function(p_u_84) --[[ Line: 261 ]]
                --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_82, (ref 3): v_u_9, (ref 4): v_u_23 ]]
                if p_u_84 == nil then
                    return p_u_32._menus:remove_menu(v_u_82);
                end;
                p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_InvitePlayer_ServerResponse, function(p85, p86) --[[ Line: 263 ]]
                    --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_82, (copy 3): p_u_84, (ref 4): v_u_23 ]]
                    p_u_32._menus:remove_menu(v_u_82)
                    local v87
                    if p85 then
                        p86 = string.format("Team invite sent to \'%s\'!\nThe invite will be visible in their chat window.", p_u_84.Name)
                        v87 = "Invite Sent"
                    else
                        v87 = "Failed"
                    end;
                    p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text(v87, p86))
                end)
                p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_InvitePlayer_Client, p_u_84.UserId)
            end))
        end;
        local function f_show_guild_recruiting_state_menu() --[[ Name: show_guild_recruiting_state_menu ]] --[[ Line: 281 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): p_u_34, (ref 4): v_u_17, (ref 5): p_u_33, (ref 6): v_u_14, (ref 7): v_u_1, (ref 8): v_u_12, (ref 9): v_u_23, (ref 10): v_u_9, (ref 11): v_u_35 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_34:push_menu(v_u_17:new(p_u_32, p_u_33, p_u_34, function(p88) --[[ Line: 284 ]]
                --[[ Upvalues: (ref 1): v_u_14 ]]
                p88:set_header_text("Update Recruitment State")
                local v89 = p88:get_element_list()
                for _, v90 in pairs(v_u_14.RecruitmentState) do
                    v89:push_back(v90)
                end;
            end, function(p91, p92, p93, _, p94) --[[ Line: 291 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_1 ]]
                p92.Text = v_u_14:get_recruitment_state_name(p91)
                p93.Image = v_u_1:important_assetid()
                p94:get_description_display().Text = v_u_14:get_recruitment_state_description(p91)
            end, function(p_u_95) --[[ Line: 296 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_14, (ref 3): p_u_32, (ref 4): v_u_8, (ref 5): v_u_23, (ref 6): v_u_9, (ref 7): v_u_35 ]]
                if v_u_12:test_enum_member(p_u_95, v_u_14.RecruitmentState) then
                    p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                    local v_u_96 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_32._evt:wait_on_event_once(v_u_9.EVT_GuildRecruitment_ChangeState_ServerResponse, function(p97, p98, p99) --[[ Line: 300 ]]
                        --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_96, (ref 3): v_u_14, (copy 4): p_u_95, (ref 5): v_u_35, (ref 6): v_u_23 ]]
                        p_u_32._menus:remove_menu(v_u_96)
                        local v100
                        if p97 then
                            v100 = "Team State Changed"
                            p98 = string.format("Your team recruitment state is changed to %s", v_u_14:get_recruitment_state_name(p_u_95))
                            if p99 then
                                v_u_35:set_guild_data_from_tab(p99)
                            end;
                            v_u_35:update_state()
                        else
                            v100 = "Failed"
                        end;
                        p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text(v100, p98))
                    end)
                    p_u_32._evt:fire_event_to_server(v_u_9.EVT_GuildRecruitment_ChangeState_Client, p_u_95)
                end;
            end))
        end;
        local function _(p_u_101) --[[ Name: get_recruitment_request_set ]] --[[ Line: 323 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_9, (ref 3): v_u_2 ]]
            p_u_32._evt:wait_on_event_once(v_u_9.EVT_GuildRecruitment_GetAdminRecruitmentData_ServerResponse, function(_, _, p102) --[[ Line: 324 ]]
                --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_101 ]]
                local v103 = v_u_2:new()
                if typeof(p102) == "table" then
                    v103:add_set_from_table_list(p102)
                end;
                p_u_101(v103)
            end)
            p_u_32._evt:fire_event_to_server(v_u_9.EVT_GuildRecruitment_GetAdminRecruitmentData_Client)
        end;
        local function f_show_approve_players_menu() --[[ Name: show_approve_players_menu ]] --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_23, (ref 4): p_u_34, (ref 5): v_u_26, (ref 6): p_u_33, (ref 7): v_u_1, (ref 8): v_u_9, (ref 9): v_u_2 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            local v_u_104 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            local function v_u_112(p_u_105) --[[ Line: 338 ]]
                --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_104, (ref 3): p_u_34, (ref 4): v_u_26, (ref 5): p_u_33, (ref 6): v_u_1, (ref 7): v_u_23, (ref 8): v_u_9 ]]
                p_u_32._menus:remove_menu(v_u_104)
                p_u_34:push_menu(v_u_26:new(p_u_32, p_u_33, p_u_34, function(p106) --[[ Line: 342 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_105 ]]
                    for _, v107 in pairs(v_u_1:get_players():GetPlayers()) do
                        if p_u_105:contains(v107.UserId) then
                            p106:get_players_list():push_back(v107)
                        end;
                    end;
                end, function(p108) --[[ Line: 349 ]]
                    --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_104, (ref 3): v_u_23, (ref 4): v_u_9 ]]
                    if p108 == nil then
                        return p_u_32._menus:remove_menu(v_u_104);
                    end;
                    local v_u_109 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_32._evt:wait_on_event_once(v_u_9.EVT_GuildRecruitment_ApprovePlayerToGuild_ServerResponse, function(p110, p111) --[[ Line: 352 ]]
                        --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_109, (ref 3): v_u_23 ]]
                        p_u_32._menus:remove_menu(v_u_109)
                        p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text(p110 and "Success" or "Failed", p111))
                    end)
                    p_u_32._evt:fire_event_to_server(v_u_9.EVT_GuildRecruitment_ApprovePlayerToGuild_Client, p108.UserId)
                end))
            end;
            p_u_32._evt:wait_on_event_once(v_u_9.EVT_GuildRecruitment_GetAdminRecruitmentData_ServerResponse, function(_, _, p113) --[[ Line: 324 ]]
                --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_112 ]]
                local v114 = v_u_2:new()
                if typeof(p113) == "table" then
                    v114:add_set_from_table_list(p113)
                end;
                v_u_112(v114)
            end)
            p_u_32._evt:fire_event_to_server(v_u_9.EVT_GuildRecruitment_GetAdminRecruitmentData_Client)
        end;
        local function f_show_change_name_menu() --[[ Name: show_change_name_menu ]] --[[ Line: 371 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_23, (ref 3): v_u_8, (ref 4): v_u_29, (ref 5): v_u_11, (ref 6): v_u_38, (ref 7): v_u_9, (ref 8): p_u_34, (ref 9): v_u_35 ]]
            local function f_show_error(p115) --[[ Name: show_error ]] --[[ Line: 372 ]]
                --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_23 ]]
                p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Cannot edit team name", p115))
            end;
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_29:show_text_input_box_ui(p_u_32, "Change Team Name", string.format("Enter the updated name of your team.\nRequirements: %d to %d characters, numbers and letters only.\nAll names are run through Roblox moderation.\nCost: %d Team Stars", v_u_11:guild_name_min_length(), v_u_11:guild_name_max_length(), v_u_11:get_guild_change_name_cost()), v_u_38:get_name(), function(p_u_116) --[[ Line: 387 ]]
                --[[ Upvalues: (ref 1): v_u_11, (copy 2): f_show_error, (ref 3): p_u_32, (ref 4): v_u_23, (ref 5): v_u_9, (ref 6): p_u_34, (ref 7): v_u_35 ]]
                if #p_u_116 < v_u_11:guild_name_min_length() then
                    return f_show_error("Team name must be 3 or more characters.");
                end;
                local v_u_117 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_EditGuildName_ServerResponse, function(p118, p119, p120) --[[ Line: 390 ]]
                    --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_117, (ref 3): f_show_error, (ref 4): p_u_34, (ref 5): v_u_35, (ref 6): v_u_23, (copy 7): p_u_116 ]]
                    p_u_32._menus:remove_menu(v_u_117)
                    if p118 ~= true then
                        return f_show_error(p119);
                    end;
                    p_u_34:remove_menu(v_u_35)
                    p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Team name changed!", string.format("Changed team name to \'%s\'!", p_u_116)))
                    if p120 then
                        v_u_35:set_guild_data_from_tab(p120)
                    end;
                    v_u_35:update_state()
                end)
                p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_EditGuildName_Client, p_u_116)
            end):set_text_box_empty_text("Team Name"):set_max_length(v_u_11:guild_name_max_length())
        end;
        local function f_show_activity_log_menu() --[[ Name: show_activity_log_menu ]] --[[ Line: 409 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_23, (ref 3): v_u_9, (ref 4): v_u_21, (ref 5): p_u_34, (ref 6): v_u_17, (ref 7): p_u_33, (ref 8): v_u_1 ]]
            local v_u_121 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_GetGuildActivityLogServerResponse, function(p122) --[[ Line: 411 ]]
                --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_121, (ref 3): v_u_21, (ref 4): p_u_34, (ref 5): v_u_17, (ref 6): p_u_33, (ref 7): v_u_1 ]]
                p_u_32._menus:remove_menu(v_u_121)
                local v_u_123 = v_u_21:table_to_list(p122)
                p_u_34:push_menu(v_u_17:new(p_u_32, p_u_33, p_u_34, function(p124) --[[ Line: 415 ]]
                    --[[ Upvalues: (copy 1): v_u_123 ]]
                    p124:set_header_text("Team Activity Log")
                    for v125 = 1, v_u_123:count() do
                        p124:get_element_list():push_back(v_u_123:get(v125))
                    end;
                end, function(p126, p127, p_u_128, _, p129) --[[ Line: 421 ]]
                    --[[ Upvalues: (ref 1): v_u_1 ]]
                    p127.Text = p126:get_message_text()
                    p_u_128.Image = v_u_1:transparent_assetid()
                    p129:get_description_display().Text = os.date(nil, p126:get_message_time())
                    v_u_1:get_user_thumbnail(p126:get_player_id(), function(p130, _) --[[ Line: 425 ]]
                        --[[ Upvalues: (copy 1): p_u_128 ]]
                        if p_u_128 ~= nil then
                            p_u_128.Image = p130
                        end;
                    end, false)
                    p129:set_select_button_enabled(false)
                end, function(_) end))
            end)
            p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_GetGuildActivityLogClient)
        end;
        v_u_45 = v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.AdminActionButton), p_u_33, function() --[[ Line: 440 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_38, (ref 3): v_u_1, (ref 4): p_u_32, (ref 5): v_u_8, (ref 6): p_u_34, (ref 7): v_u_17, (ref 8): p_u_33, (ref 9): v_u_11, (ref 10): v_u_9, (ref 11): v_u_2, (copy 12): f_show_admin_invite_players_menu, (ref 13): v_u_35, (ref 14): v_u_23, (copy 15): f_show_admin_purchase_guild_bonus_menu, (copy 16): f_show_guild_recruiting_state_menu, (copy 17): f_show_approve_players_menu, (copy 18): f_show_change_name_menu, (copy 19): f_show_activity_log_menu ]]
            local v_u_131 = v_u_14:player_has_admin_access(v_u_38, v_u_1:get_local_userid())
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_34:push_menu(v_u_17:new(p_u_32, p_u_33, p_u_34, function(p132) --[[ Line: 451 ]]
                --[[ Upvalues: (copy 1): v_u_131 ]]
                local v133 = p132:get_element_list()
                if v_u_131 then
                    p132:set_header_text("Team Actions (Admin)")
                    v133:push_back("View Activity Log")
                    v133:push_back("Invite Player")
                    v133:push_back("Purchase Team Bonuses")
                    v133:push_back("Change Team Recruiting Status")
                    v133:push_back("Approve Team Join Requests")
                    v133:push_back("Change Team Name")
                else
                    p132:set_header_text("Team Actions")
                    v133:push_back("View Activity Log")
                end;
            end, function(p134, p135, p136, _, p_u_137) --[[ Line: 466 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_11, (ref 3): v_u_38, (ref 4): v_u_14, (ref 5): p_u_32, (ref 6): v_u_9, (ref 7): v_u_2 ]]
                p135.Text = p134
                p136.Image = v_u_1:important_assetid()
                p_u_137:set_select_button_enabled(true)
                if p134 == "Change Team Name" then
                    p_u_137:get_description_display().Text = string.format("Cost: %d Team Stars", v_u_11:get_guild_change_name_cost())
                    p_u_137:set_select_button_enabled(v_u_38:get_star_currency() >= v_u_11:get_guild_change_name_cost())
                    return;
                elseif p134 == "Change Team Recruiting Status" then
                    p_u_137:get_description_display().Text = string.format("%s", v_u_14:get_recruitment_state_name(v_u_38:get_recruitment_state()))
                    return;
                elseif p134 == "Approve Team Join Requests" then
                    p_u_137:set_select_button_enabled(false)
                    p_u_137:get_description_display().Text = "Loading..."
                    local function v_u_139(p138) --[[ Line: 481 ]]
                        --[[ Upvalues: (copy 1): p_u_137 ]]
                        if p_u_137:get_data() == "Approve Team Join Requests" then
                            if p138:count() > 0 then
                                p_u_137:set_select_button_enabled(true)
                                p_u_137:get_description_display().Text = string.format("%d pending request(s)", p138:count())
                            else
                                p_u_137:get_description_display().Text = "No pending requests"
                            end;
                        else
                            return;
                        end;
                    end;
                    p_u_32._evt:wait_on_event_once(v_u_9.EVT_GuildRecruitment_GetAdminRecruitmentData_ServerResponse, function(_, _, p140) --[[ Line: 324 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_139 ]]
                        local v141 = v_u_2:new()
                        if typeof(p140) == "table" then
                            v141:add_set_from_table_list(p140)
                        end;
                        v_u_139(v141)
                    end)
                    p_u_32._evt:fire_event_to_server(v_u_9.EVT_GuildRecruitment_GetAdminRecruitmentData_Client)
                else
                    p_u_137:get_description_display().Text = ""
                end;
            end, function(p142) --[[ Line: 494 ]]
                --[[ Upvalues: (ref 1): f_show_admin_invite_players_menu, (ref 2): v_u_14, (ref 3): v_u_35, (ref 4): p_u_32, (ref 5): v_u_23, (ref 6): f_show_admin_purchase_guild_bonus_menu, (ref 7): f_show_guild_recruiting_state_menu, (ref 8): f_show_approve_players_menu, (ref 9): f_show_change_name_menu, (ref 10): f_show_activity_log_menu ]]
                if p142 == "Invite Player" then
                    f_show_admin_invite_players_menu()
                    return;
                elseif p142 == "Purchase Team Bonuses" then
                    if v_u_14:get_member_count_with_join_date_older_than_current_week(v_u_35:get_guild_data()) == 0 then
                        p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Cannot purchase team bonus", "Team must be at least 1 week old to activate team bonuses."))
                    else
                        f_show_admin_purchase_guild_bonus_menu()
                    end;
                elseif p142 == "Change Team Recruiting Status" then
                    f_show_guild_recruiting_state_menu()
                    return;
                elseif p142 == "Approve Team Join Requests" then
                    f_show_approve_players_menu()
                    return;
                elseif p142 == "Change Team Name" then
                    f_show_change_name_menu()
                elseif p142 == "View Activity Log" then
                    f_show_activity_log_menu()
                end;
            end):set_close_on_element_select(false))
        end):set_auto_zoffset_behaviour(true))
        v_u_46 = v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.ChatButton), p_u_33, function() --[[ Line: 522 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_27, (ref 4): p_u_33, (ref 5): p_u_34 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_27:show_guild_chat_menu(p_u_32, p_u_33, p_u_34)
        end))
        local l_ActivateTeamBonusButton_0 = v_u_36.ActivateTeamBonusButton
        local l_Frame_0 = l_ActivateTeamBonusButton_0.SurfaceGui.Frame
        v_u_49 = v_u_19:create_display_wrapper(l_Frame_0.Notification, l_Frame_0.Notification.Display)
        v_u_48 = v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, l_ActivateTeamBonusButton_0), p_u_33, function() --[[ Line: 536 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_23, (ref 4): v_u_9, (ref 5): v_u_18, (ref 6): v_u_35 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            local v_u_143 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_ClaimBonus_ServerResponse, function(p_u_144, p_u_145) --[[ Line: 539 ]]
                --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_143, (ref 3): v_u_23, (ref 4): v_u_18, (ref 5): v_u_8, (ref 6): v_u_35 ]]
                p_u_32._player_blob_manager:do_sync(function() --[[ Line: 540 ]]
                    --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_143, (copy 3): p_u_144, (ref 4): v_u_23, (copy 5): p_u_145, (ref 6): v_u_18, (ref 7): v_u_8, (ref 8): v_u_35 ]]
                    p_u_32._menus:remove_menu(v_u_143)
                    if p_u_144 ~= true then
                        return p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Failed", p_u_145));
                    end;
                    local v146 = ""
                    for v147, _ in v_u_18:playerblob_get_active_bonus_ids_set_for_weekid(p_u_32._player_blob_manager:get_player_blob(), p_u_32._player_blob_manager:get_weekid()):key_itr() do
                        v146 = v146 .. v_u_18:get_bonus_info_for_id(v147):get_name() .. "\n"
                    end;
                    p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Team Bonus Activated!", "This team bonus will be active for the rest of the week.\nActive Bonuses:\n" .. v146))
                    p_u_32._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                    v_u_35:update_state()
                end)
            end)
            p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_ClaimBonus_Client)
        end):set_auto_zoffset_behaviour(true))
        v_u_6:button_add_enabled_anim(v_u_48, function() --[[ Line: 563 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            return v_u_35:get_alpha();
        end)
        v_u_48:set_visible(false)
        if v_u_16.HideGuildContributionUIElements == true then
            v_u_36.InfoButtons.DonateStarsButton.Parent = nil
        else
            v_u_47 = v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.InfoButtons.DonateStarsButton), p_u_33, function() --[[ Line: 573 ]]
                --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_28, (ref 4): v_u_13, (ref 5): v_u_23, (ref 6): v_u_9, (ref 7): v_u_35, (ref 8): v_u_7, (ref 9): l_Loading_0, (ref 10): v_u_31, (ref 11): v_u_1 ]]
                p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                local v148 = p_u_32._player_blob_manager:get_player_blob()
                p_u_32._menus:push_menu(v_u_28:new(p_u_32, p_u_32._spui, p_u_32._menus, math.min(5, v_u_13:get_star_currency(v148)), function(p149) --[[ Line: 578 ]]
                    --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_23, (ref 3): v_u_9, (ref 4): v_u_35, (ref 5): v_u_7, (ref 6): l_Loading_0, (ref 7): v_u_31, (ref 8): v_u_8 ]]
                    if p149 > 0 then
                        local v_u_150 = p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_DonateStars_ServerResponse, function(p_u_151, p_u_152, p_u_153) --[[ Line: 581 ]]
                            --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_150, (ref 3): v_u_35, (ref 4): v_u_7, (ref 5): l_Loading_0, (ref 6): v_u_31, (ref 7): v_u_8 ]]
                            p_u_32._player_blob_manager:do_sync(function() --[[ Line: 582 ]]
                                --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_150, (copy 3): p_u_151, (ref 4): v_u_35, (copy 5): p_u_153, (ref 6): v_u_7, (copy 7): p_u_152, (ref 8): l_Loading_0, (ref 9): v_u_31, (ref 10): v_u_8 ]]
                                p_u_32._menus:remove_menu(v_u_150)
                                if p_u_151 then
                                    v_u_35:set_guild_data_from_tab(p_u_153)
                                else
                                    v_u_7:warnf(p_u_152)
                                end;
                                l_Loading_0 = v_u_31.Loaded
                                v_u_35:update_state()
                                p_u_32._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                            end)
                        end)
                        p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_DonateStars_Client, p149)
                    end;
                end):set_value_increment(5):set_reset_value(0):set_range_min_max(0, v_u_13:get_star_currency(v148)):set_title_sub_text(string.format("Donate Stars (You have: %d)", v_u_13:get_star_currency(v148)), "Stars will go to the \'Team Stars\' reserve, and will be used for Team events.\nDonating stars will also increase your weekly contribution points!"):set_value_display_info_fn(function(p154) --[[ Line: 603 ]]
                    --[[ Upvalues: (ref 1): v_u_1 ]]
                    return v_u_1:comma_value(p154), "Stars";
                end))
            end))
            v_u_6:button_add_enabled_anim(v_u_47, function() --[[ Line: 608 ]]
                --[[ Upvalues: (ref 1): v_u_35 ]]
                return v_u_35:get_alpha();
            end)
        end;
        v_u_41 = v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.PlayerListButtonDown), p_u_33, function() --[[ Line: 614 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_61 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_61:next_page()
        end))
        v_u_40 = v_u_35:add_cycle_element(p_u_32, 1, v_u_6:new(v_u_5:new(v_u_35, v_u_36.PrimaryPart, v_u_36.PlayerListButtonUp), p_u_33, function() --[[ Line: 623 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): v_u_61 ]]
            p_u_32._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_61:prev_page()
        end))
        local l_Anchors_0 = v_u_36.Anchors
        v_u_61:create_list_elements_from_anchors_and_proto({
            l_Anchors_0.Anchor1,
            l_Anchors_0.Anchor2,
            l_Anchors_0.Anchor3,
            l_Anchors_0.Anchor4,
            l_Anchors_0.Anchor5,
            l_Anchors_0.Anchor6,
            l_Anchors_0.Anchor7,
            l_Anchors_0.Anchor8
        }, v_u_36.MemberListElement, v_u_36, function(p155) --[[ Line: 643 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): p_u_32, (ref 3): v_u_35 ]]
            return v_u_24:new(p_u_32, v_u_35, p155);
        end)
        l_Loading_0 = v_u_31.Loading
        v_u_35:update_state()
        p_u_32._evt:wait_on_event_once(v_u_9.EVT_Guild_GetPlayerInfo_ServerResponse, function(p156, p157, _, p158) --[[ Line: 651 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): p_u_34, (ref 3): v_u_35, (ref 4): l_Loading_0, (ref 5): v_u_31, (ref 6): v_u_1, (ref 7): v_u_7, (ref 8): v_u_18, (ref 9): v_u_38, (ref 10): v_u_2 ]]
            p_u_32._guild_manager:handle_player_info_server_response(p156, p157)
            if p_u_34:contains_menu(v_u_35) == true then
                v_u_35:set_guild_data_from_tab(p158)
                l_Loading_0 = v_u_31.Loaded
                v_u_35:update_state()
                if v_u_1:is_dev_build() then
                    v_u_7:puts("Team Active Bonuses:")
                    for v159, _ in v_u_18:guild_data_get_active_bonus_ids_set_for_weekid(v_u_38, p_u_32._player_blob_manager:get_weekid()):key_itr() do
                        v_u_7:puts("\t%s", v_u_18:get_bonus_info_for_id(v159):get_name())
                    end;
                    v_u_7:puts("Player Active Bonuses:")
                    for v160, _ in v_u_18:playerblob_get_active_bonus_ids_set_for_weekid(p_u_32._player_blob_manager:get_player_blob(), p_u_32._player_blob_manager:get_weekid()):key_itr() do
                        v_u_7:puts("\t%s", v_u_18:get_bonus_info_for_id(v160):get_name())
                    end;
                end;
                local v161 = v_u_2:new()
                for _, v162 in v_u_38:get_member_infos():key_itr() do
                    v161:add_set(v162:get_rbxid())
                end;
                p_u_32._guild_manager:request_status_for_rbxid_list(v161:key_list())
            end;
        end)
        p_u_32._evt:fire_event_to_server(v_u_9.EVT_Guild_GetPlayerInfo_Client)
        v_u_35:transition_update_visual(0)
        v_u_35:layout()
    end;
    v_u_35.test_if_guild_valid = function(p163) --[[ Name: test_if_guild_valid ]] --[[ Line: 681 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_11, (ref 3): v_u_14, (ref 4): v_u_1, (copy 5): p_u_32, (copy 6): p_u_34, (ref 7): v_u_23 ]]
        if v_u_38:get_guildid() ~= v_u_11:not_in_guild_id() and v_u_14:get_player_info(v_u_38, v_u_1:get_local_userid()) ~= nil then
            return true;
        end;
        p_u_32._guild_manager:handle_player_info_server_response(false, v_u_11:not_in_guild_id())
        p_u_34:remove_menu(p163)
        p_u_32._menus:push_menu(v_u_23:new(p_u_32, p_u_32._spui, p_u_32._menus):set_text("Error", "Not in guild"))
        return false;
    end;
    v_u_35.get_current_state = function(_) --[[ Name: get_current_state ]] --[[ Line: 693 ]]
        --[[ Upvalues: (ref 1): l_Loading_0 ]]
        return l_Loading_0;
    end;
    v_u_35.update_state = function(p164) --[[ Name: update_state ]] --[[ Line: 694 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_31, (ref 3): v_u_37, (ref 4): v_u_41, (ref 5): v_u_40, (copy 6): v_u_44, (ref 7): v_u_45, (ref 8): v_u_46, (ref 9): v_u_47, (copy 10): v_u_61, (ref 11): v_u_48, (ref 12): v_u_38, (ref 13): v_u_14, (ref 14): v_u_1, (copy 15): p_u_32, (ref 16): v_u_13, (ref 17): v_u_43, (ref 18): v_u_11, (ref 19): v_u_16, (ref 20): v_u_18, (ref 21): v_u_49, (ref 22): v_u_50 ]]
        if l_Loading_0 == v_u_31.Loading then
            v_u_37.LoadedSection.Visible = false
            v_u_37.LoadingSection.Visible = true
            v_u_41:set_visible(false)
            v_u_40:set_visible(false)
            for v165 = 1, v_u_44:count() do
                v_u_44:get(v165):set_visible(false)
            end;
            v_u_45:set_visible(false)
            v_u_46:set_visible(false)
            v_u_47:set_visible(false)
            v_u_61:set_visible(false)
            v_u_48:set_visible(false)
        else
            if p164:test_if_guild_valid() ~= true then
                return;
            end;
            v_u_37.LoadedSection.Visible = true
            v_u_37.LoadingSection.Visible = false
            local l_InfoSection_0 = v_u_37.LoadedSection.InfoSection
            l_InfoSection_0.TeamNameDisplay.Text = v_u_38:get_name()
            l_InfoSection_0.TeamMessageDisplay.Text = v_u_38:get_message()
            v_u_14:render_guild_icon(v_u_38, l_InfoSection_0.TeamIconDisplay)
            local v166 = v_u_14:player_has_admin_access(v_u_38, v_u_1:get_local_userid())
            for v167 = 1, v_u_44:count() do
                v_u_44:get(v167):set_visible(v166)
            end;
            v_u_45:set_visible(true)
            if v_u_1:do_disable_chat() then
                v_u_46:set_visible(false)
            else
                v_u_46:set_visible(true)
            end;
            v_u_47:set_visible(true)
            local v168 = p_u_32._player_blob_manager:get_player_blob()
            v_u_47:set_enabled(v_u_13:get_star_currency(v168) > 0)
            v_u_43.Text = string.format("Team Members (%d/%d)", v_u_38:get_member_infos():count(), v_u_11:get_max_guild_players())
            v_u_61:page_update()
            if v_u_16.HideGuildContributionUIElements == true then
                l_InfoSection_0.StarSection.Display.Text = "-"
            else
                l_InfoSection_0.StarSection.Display.Text = tostring(v_u_38:get_star_currency())
            end;
            v_u_48:set_visible(true)
            local v169, v170 = v_u_18:playerblob_guild_data_can_claim_any_bonus_for_weekid(v168, v_u_38, p_u_32._player_blob_manager:get_weekid())
            v_u_48:set_enabled(v169)
            v_u_49:update_state(v169, v170)
        end;
        v_u_50:update_state()
    end;
    local v_u_171 = 0
    v_u_35.behaviour_update = function(p172, p173, p174) --[[ Name: behaviour_update ]] --[[ Line: 750 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_20, (ref 3): l_Loading_0, (ref 4): v_u_31, (copy 5): p_u_32, (ref 6): v_u_171, (copy 7): v_u_61, (copy 8): f_list_display_element_member_info_update_status_display ]]
        p172:behaviour_update_base(p173, p174)
        v_u_50:update(p173)
        if p172._current_mode == v_u_20.MODE_OPEN and l_Loading_0 == v_u_31.Loaded then
            local _, v175 = p_u_32._guild_manager:get_status_dict()
            if v_u_171 ~= v175 then
                v_u_61:refresh_element_data(f_list_display_element_member_info_update_status_display)
                v_u_171 = v175
            end;
        end;
    end;
    v_u_35.visual_update = function(p176, p177, p178) --[[ Name: visual_update ]] --[[ Line: 763 ]]
        --[[ Upvalues: (copy 1): p_u_32 ]]
        if p_u_32:transition_local_camera_cframe_finished() ~= false then
            p176:visual_update_base(p177, p178)
        end;
    end;
    v_u_35.on_refocus = function(p179) --[[ Name: on_refocus ]] --[[ Line: 770 ]]
        p179:update_state()
    end;
    v_u_35.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 774 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        v_u_36:Destroy()
    end;
    local v_u_180 = 1
    local v_u_181 = 1
    v_u_35.layout = function(p182) --[[ Name: layout ]] --[[ Line: 780 ]]
        --[[ Upvalues: (copy 1): p_u_33, (ref 2): v_u_181, (ref 3): v_u_36, (copy 4): v_u_61 ]]
        p182:opt_rescale_to_max_nxy(p_u_33, 0.8, 0.8, v_u_181)
        local v183, v184 = p182:opt_update_cframe_params(p_u_33, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p182:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v183 == true then
            v_u_36:SetPrimaryPartCFrame(v184)
        end;
        v_u_61:layout()
    end;
    v_u_35.set_alpha = function(_, p185) --[[ Name: set_alpha ]] --[[ Line: 794 ]]
        --[[ Upvalues: (ref 1): v_u_180, (ref 2): v_u_1, (ref 3): v_u_36 ]]
        if v_u_180 ~= p185 then
            v_u_180 = p185
            v_u_1:r_set_alpha(v_u_36, v_u_180)
        end;
    end;
    v_u_35.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 800 ]]
        --[[ Upvalues: (ref 1): v_u_180 ]]
        return v_u_180;
    end;
    v_u_35.set_scale = function(_, p186) --[[ Name: set_scale ]] --[[ Line: 801 ]]
        --[[ Upvalues: (ref 1): v_u_181 ]]
        v_u_181 = p186
    end;
    v_u_35.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 802 ]]
        --[[ Upvalues: (ref 1): v_u_181 ]]
        return v_u_181;
    end;
    v_u_35.get_native_size = function(p187) --[[ Name: get_native_size ]] --[[ Line: 804 ]]
        return p187._native_size;
    end;
    v_u_35.get_size = function(p188) --[[ Name: get_size ]] --[[ Line: 807 ]]
        return p188._size;
    end;
    v_u_35.set_size = function(p189, p190) --[[ Name: set_size ]] --[[ Line: 810 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        p189._size = p190
        v_u_36.PrimaryPart.Size = Vector3.new(p190.X, p190.Y, 0)
    end;
    v_u_35.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 814 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36.PrimaryPart.Position;
    end;
    v_u_35.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 817 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36.PrimaryPart.SurfaceGui;
    end;
    v_u_35.set_showing = function(_, p191) --[[ Name: set_showing ]] --[[ Line: 820 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_10 ]]
        if p191 then
            v_u_36.Parent = v_u_10:get_world_ui_folder()
        else
            v_u_36.Parent = nil
        end;
    end;
    v_u_35.get_uichild_parent = function(_) --[[ Name: get_uichild_parent ]] --[[ Line: 828 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36.PrimaryPart;
    end;
    f_cons()
    return v_u_35;
end;
return v30;
