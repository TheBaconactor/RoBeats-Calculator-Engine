-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:58 PM
-- Time elapsed: 13 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GuildMessage)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.LocalFeverIconUtil)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
v9:require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_12, (ref 4): v_u_13 ]]
    v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_12 = require(game.ReplicatedStorage.Lobby.UI.GenericMessageBoardMenu)
    v_u_13 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
end)
local v40 = {
    ["show_guild_edit_icon_menu"] = function(_, p_u_14, p15, p16, p_u_17) --[[ Name: show_guild_edit_icon_menu ]] --[[ Line: 118 ]]
        --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_11, (copy 3): v_u_3, (ref 4): v_u_10, (copy 5): v_u_1, (ref 6): v_u_13, (copy 7): v_u_6, (copy 8): v_u_7, (copy 9): v_u_8 ]]
        local function f_send_team_icon(p18) --[[ Name: send_team_icon ]] --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_2, (copy 3): p_u_14, (ref 4): v_u_11, (ref 5): v_u_3 ]]
            if p18 == p_u_17:get_guild_data():get_icon() then
                return v_u_2:puts("Guild icon was not changed, not updating.");
            end;
            local v_u_19 = p_u_14._menus:push_menu(v_u_11:new(p_u_14, p_u_14._spui, p_u_14._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_14._evt:wait_on_event_once(v_u_3.EVT_Guild_UpdateGuildIcon_ServerResponse, function(p20, p21, p22) --[[ Line: 126 ]]
                --[[ Upvalues: (ref 1): p_u_14, (copy 2): v_u_19, (ref 3): p_u_17, (ref 4): v_u_2 ]]
                p_u_14._menus:remove_menu(v_u_19)
                if p20 then
                    p_u_17:set_guild_data_from_tab(p22)
                else
                    v_u_2:warnf(p21)
                end;
                p_u_17:set_current_state_loaded()
                p_u_17:update_state()
            end)
            p_u_14._evt:fire_event_to_server(v_u_3.EVT_Guild_UpdateGuildIcon_Client, p18)
        end;
        p16:push_menu(v_u_10:new(p_u_14, p15, p16, function(p23) --[[ Line: 143 ]]
            p23:set_header_text("Edit Team Icon")
            p23:get_element_list():push_back(1)
            p23:get_element_list():push_back(2)
        end, function(p24, p25, p26, _, p27) --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            if p24 == 1 then
                p25.Text = "Select Icon"
                p26.Image = v_u_1:important_assetid()
                p27:get_description_display().Text = "Select an icon from a list of your available icons."
            elseif p24 == 2 then
                p25.Text = "Enter AssetID"
                p26.Image = v_u_1:get_question_assetid()
                p27:get_description_display().Text = "Enter the Roblox AssetID for the icon you want to use."
            end;
        end, function(p28) --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_14, (copy 3): f_send_team_icon, (ref 4): v_u_6, (ref 5): v_u_10, (ref 6): v_u_7, (ref 7): v_u_8 ]]
            if p28 == 2 then
                v_u_13:show_text_input_box_ui(p_u_14, "Edit Team Icon", "Update this Team\'s icon.\nThis should be in the form of an assetid (like \'rbxassetid://...\').", "", function(p29) --[[ Line: 166 ]]
                    --[[ Upvalues: (ref 1): f_send_team_icon ]]
                    if typeof(p29) == "string" then
                        f_send_team_icon(p29)
                    end;
                end):set_text_box_empty_text("rbxassetid://..."):set_max_length(v_u_6:guild_name_max_length())
            elseif p28 == 1 then
                p_u_14._player_blob_manager:get_player_blob()
                p_u_14._menus:push_menu(v_u_10:new(p_u_14, p_u_14._spui, p_u_14._menus, function(p30) --[[ Line: 179 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (ref 2): p_u_14, (ref 3): v_u_8 ]]
                    p30:set_header_text("Select icon to display...")
                    local v31 = v_u_7:get_available_fevericon_id_list(p_u_14)
                    v31:remove_if(function(p32) --[[ Line: 182 ]]
                        --[[ Upvalues: (ref 1): v_u_8 ]]
                        return v_u_8:singleton():get_fevericon_default_available_ids_set():contains(p32) or v_u_8:singleton():get_fevericon_for_id(p32):is_vip_only();
                    end)
                    for _, v33 in v31:key_itr() do
                        p30:get_element_list():push_back(v33)
                    end;
                end, function(p34, p35, p36, _, _) --[[ Line: 189 ]]
                    --[[ Upvalues: (ref 1): v_u_8 ]]
                    local v37 = v_u_8:singleton():get_fevericon_for_id(p34)
                    if v37 then
                        p35.Text = v37:get_name()
                        p36.Image = v37:get_image()
                    else
                        p35.Text = "?"
                    end;
                end, function(p38) --[[ Line: 198 ]]
                    --[[ Upvalues: (ref 1): v_u_8, (ref 2): f_send_team_icon ]]
                    local v39 = p38 ~= nil and v_u_8:singleton():get_fevericon_for_id(p38)
                    if v39 then
                        f_send_team_icon(v39:get_image())
                    end;
                end)):set_empty_message("No icons available."):get_list_adapter():set_do_wrap(true)
            end;
        end))
    end
}
local function f_get_guild_message_board_data(p_u_41, p_u_42) --[[ Name: get_guild_message_board_data ]] --[[ Line: 32 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_3, (copy 3): v_u_4 ]]
    local v_u_43 = p_u_41._menus:push_menu(v_u_11:new(p_u_41, p_u_41._spui, p_u_41._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_41._evt:wait_on_event_once(v_u_3.EVT_Guild_GetGuildMessageBoardServerResponse, function(p44) --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): p_u_41, (copy 2): v_u_43, (ref 3): v_u_4, (copy 4): p_u_42 ]]
        p_u_41._menus:remove_menu(v_u_43)
        p_u_42((v_u_4:table_to_list(p44)))
    end)
    p_u_41._evt:fire_event_to_server(v_u_3.EVT_Guild_GetGuildMessageBoardClient)
end;
v40.show_guild_chat_menu = function(_, p_u_45, p_u_46, p_u_47) --[[ Name: show_guild_chat_menu ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_11, (copy 3): f_get_guild_message_board_data, (ref 4): v_u_10, (copy 5): v_u_4, (ref 6): v_u_12, (copy 7): v_u_3, (copy 8): v_u_5 ]]
    if v_u_1:do_disable_chat() then
        p_u_47:push_menu(v_u_11:new(p_u_45, p_u_46, p_u_47):set_text("Disabled", "Chat is disabled on this platform."))
    else
        f_get_guild_message_board_data(p_u_45, function(p_u_48) --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): p_u_47, (ref 2): v_u_10, (copy 3): p_u_45, (copy 4): p_u_46, (ref 5): v_u_4, (ref 6): v_u_1, (ref 7): v_u_12, (ref 8): v_u_11, (ref 9): v_u_3, (ref 10): v_u_5 ]]
            local v_u_57 = p_u_47:push_menu(v_u_10:new(p_u_45, p_u_46, p_u_47, function(p49) --[[ Line: 51 ]]
                --[[ Upvalues: (ref 1): p_u_48 ]]
                p49:set_header_text("Team Message Board")
                for v50 = 1, p_u_48:count() do
                    p49:get_element_list():push_back(p_u_48:get(v50))
                end;
            end, function(p51, p52, p_u_53, _, p54) --[[ Line: 57 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1 ]]
                p52.Text = v_u_4:get_message_text_with_cutoff_length(p51:get_message_text(), 48)
                p_u_53.Image = v_u_1:transparent_assetid()
                p54:get_description_display().Text = string.format("%s - %s", p51:get_player_name(), os.date(nil, p51:get_message_time()))
                v_u_1:get_user_thumbnail(p51:get_player_id(), function(p55, _) --[[ Line: 61 ]]
                    --[[ Upvalues: (copy 1): p_u_53 ]]
                    if p_u_53 ~= nil then
                        p_u_53.Image = p55
                    end;
                end, false)
                p54:set_select_button_text("View")
            end, function(p56) --[[ Line: 66 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_45 ]]
                if p56 then
                    v_u_12:show_chat_message_data_popup(p_u_45, p56)
                end;
            end)):set_empty_message("No team messages."):set_close_on_element_select(false)
            v_u_57:set_settings_section_visible()
            if v_u_57:get_settings_buttons():count() > 0 then
                local v58 = v_u_57:get_settings_buttons():get(1)
                v58:set_visible(true)
                v58:bind_data(function() --[[ Line: 81 ]]
                    --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_45, (ref 3): v_u_11, (ref 4): v_u_3, (ref 5): p_u_46, (ref 6): p_u_47, (ref 7): p_u_48, (ref 8): v_u_4, (copy 9): v_u_57 ]]
                    v_u_12:show_post_chat_message_menu(p_u_45, function(p59) --[[ Line: 84 ]]
                        --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_11, (ref 3): v_u_3, (ref 4): p_u_46, (ref 5): p_u_47, (ref 6): p_u_48, (ref 7): v_u_4, (ref 8): v_u_57 ]]
                        if typeof(p59) == "string" then
                            if #p59 ~= 0 then
                                local v_u_60 = p_u_45._menus:push_menu(v_u_11:new(p_u_45, p_u_45._spui, p_u_45._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                                p_u_45._evt:wait_on_event_once(v_u_3.EVT_Guild_PostGuildMessageServerResponse, function(p_u_61, p_u_62, p_u_63, p64) --[[ Line: 89 ]]
                                    --[[ Upvalues: (ref 1): p_u_45, (copy 2): v_u_60, (ref 3): v_u_11, (ref 4): p_u_46, (ref 5): p_u_47, (ref 6): p_u_48, (ref 7): v_u_4, (ref 8): v_u_57 ]]
                                    local function f_fin() --[[ Name: fin ]] --[[ Line: 90 ]]
                                        --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_60, (copy 3): p_u_61, (ref 4): v_u_11, (ref 5): p_u_46, (ref 6): p_u_47, (copy 7): p_u_62, (ref 8): p_u_48, (ref 9): v_u_4, (copy 10): p_u_63, (ref 11): v_u_57 ]]
                                        p_u_45._menus:remove_menu(v_u_60)
                                        if p_u_61 then
                                            p_u_48 = v_u_4:table_to_list(p_u_63)
                                            v_u_57:refresh()
                                        else
                                            p_u_45._menus:push_menu(v_u_11:new(p_u_45, p_u_46, p_u_47):set_text("Error", p_u_62))
                                        end;
                                    end;
                                    if p64 == true then
                                        p_u_45._player_blob_manager:do_sync(function() --[[ Line: 101 ]]
                                            --[[ Upvalues: (copy 1): f_fin ]]
                                            f_fin()
                                        end)
                                    else
                                        f_fin()
                                    end;
                                end)
                                p_u_45._evt:fire_event_to_server(v_u_3.EVT_Guild_PostGuildMessageClient, p59)
                            end;
                        else
                            return;
                        end;
                    end)
                end)
                v_u_5:set_button_text(v58, "Post Message")
            end;
        end)
    end;
end;
return v40;
