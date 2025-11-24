-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GuildMessage)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
local v8 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v8:require_client(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_12 ]]
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_12 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
end)
local v_u_18 = {
    ["show_chat_message_data_popup"] = function(_, p13, p14) --[[ Name: show_chat_message_data_popup ]] --[[ Line: 122 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        v_u_12:show_message_box_ui(p13, "Message", string.format("From: %s [%s]", p14:get_player_name(), os.date(nil, p14:get_message_time())), p14:get_message_text())
    end,
    ["show_post_chat_message_menu"] = function(_, p15, p_u_16) --[[ Name: show_post_chat_message_menu ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_6 ]]
        v_u_12:show_text_input_box_ui(p15, "Post Message", string.format("Enter message text (Max %d characters).\nYour message will be run through Roblox moderation.", v_u_6:guild_message_max_length()), "", function(p17) --[[ Line: 140 ]]
            --[[ Upvalues: (copy 1): p_u_16 ]]
            p_u_16(p17)
        end):set_text_box_empty_text("(Message)"):set_max_length(v_u_6:guild_message_max_length())
    end
}
v_u_18.show_chat_menu = function(_, p_u_19, p_u_20, p_u_21, p_u_22) --[[ Name: show_chat_menu ]] --[[ Line: 29 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_7, (copy 3): v_u_1, (ref 4): v_u_10, (copy 5): v_u_3, (copy 6): v_u_4, (ref 7): v_u_9, (copy 8): v_u_18, (copy 9): v_u_5 ]]
    v_u_2:is_enum_member(p_u_20, v_u_7.Category)
    local l__menus_0 = p_u_19._menus
    local l__spui_0 = p_u_19._spui
    if v_u_1:do_disable_chat() then
        l__menus_0:push_menu(v_u_10:new(p_u_19, l__spui_0, l__menus_0):set_text("Disabled", "Chat is disabled on this platform."))
    else
        (function(p_u_23, p_u_24) --[[ Name: get_message_board_data ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_3, (ref 3): v_u_4, (copy 4): p_u_20, (copy 5): p_u_21 ]]
            local v_u_25 = p_u_23._menus:push_menu(v_u_10:new(p_u_23, p_u_23._spui, p_u_23._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_23._evt:wait_on_event_once(v_u_3.EVT_Lobby_GetGenericMessageBoardServerResponse, function(p26) --[[ Line: 42 ]]
                --[[ Upvalues: (copy 1): p_u_23, (copy 2): v_u_25, (ref 3): v_u_4, (copy 4): p_u_24 ]]
                p_u_23._menus:remove_menu(v_u_25)
                p_u_24((v_u_4:table_to_list(p26)))
            end)
            p_u_23._evt:fire_event_to_server(v_u_3.EVT_Lobby_GetGenericMessageBoardClient, p_u_20, p_u_21)
        end)(p_u_19, function(p_u_27) --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): l__menus_0, (ref 2): v_u_9, (copy 3): p_u_19, (copy 4): l__spui_0, (ref 5): v_u_4, (ref 6): v_u_1, (ref 7): v_u_18, (copy 8): p_u_22, (ref 9): v_u_10, (ref 10): v_u_3, (copy 11): p_u_20, (copy 12): p_u_21, (ref 13): v_u_5 ]]
            local v_u_36 = l__menus_0:push_menu(v_u_9:new(p_u_19, l__spui_0, l__menus_0, function(p28) --[[ Line: 53 ]]
                --[[ Upvalues: (ref 1): p_u_27 ]]
                for v29 = 1, p_u_27:count() do
                    p28:get_element_list():push_back(p_u_27:get(v29))
                end;
            end, function(p30, p31, p_u_32, _, p33) --[[ Line: 58 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1 ]]
                p31.Text = v_u_4:get_message_text_with_cutoff_length(p30:get_message_text(), 48)
                p_u_32.Image = v_u_1:transparent_assetid()
                p33:get_description_display().Text = string.format("%s - %s", p30:get_player_name(), os.date(nil, p30:get_message_time()))
                v_u_1:get_user_thumbnail(p30:get_player_id(), function(p34, _) --[[ Line: 62 ]]
                    --[[ Upvalues: (copy 1): p_u_32 ]]
                    if p_u_32 ~= nil then
                        p_u_32.Image = p34
                    end;
                end, false)
                p33:set_select_button_text("View")
            end, function(p35) --[[ Line: 67 ]]
                --[[ Upvalues: (ref 1): v_u_18, (ref 2): p_u_19 ]]
                if p35 then
                    v_u_18:show_chat_message_data_popup(p_u_19, p35)
                end;
            end)):set_empty_message("No messages."):set_close_on_element_select(false)
            v_u_36:get_list_adapter():set_do_wrap(true)
            v_u_36:set_header_text("Message Board")
            local v37 = {}
            if p_u_22 then
                p_u_22(v_u_36, v37)
            end;
            if v37.NoChatButton ~= true then
                v_u_36:set_settings_section_visible()
                if v_u_36:get_settings_buttons():count() > 0 then
                    local v38 = v_u_36:get_settings_buttons():get(1)
                    v38:set_visible(true)
                    v38:bind_data(function() --[[ Line: 87 ]]
                        --[[ Upvalues: (ref 1): v_u_18, (ref 2): p_u_19, (ref 3): v_u_10, (ref 4): v_u_3, (ref 5): l__spui_0, (ref 6): l__menus_0, (ref 7): p_u_27, (ref 8): v_u_4, (copy 9): v_u_36, (ref 10): p_u_20, (ref 11): p_u_21 ]]
                        v_u_18:show_post_chat_message_menu(p_u_19, function(p39) --[[ Line: 89 ]]
                            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_10, (ref 3): v_u_3, (ref 4): l__spui_0, (ref 5): l__menus_0, (ref 6): p_u_27, (ref 7): v_u_4, (ref 8): v_u_36, (ref 9): p_u_20, (ref 10): p_u_21 ]]
                            if typeof(p39) == "string" then
                                if #p39 ~= 0 then
                                    local v_u_40 = p_u_19._menus:push_menu(v_u_10:new(p_u_19, p_u_19._spui, p_u_19._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                                    p_u_19._evt:wait_on_event_once(v_u_3.EVT_Lobby_PostGenericMessageServerResponse, function(p_u_41, p_u_42, p_u_43, p44) --[[ Line: 94 ]]
                                        --[[ Upvalues: (ref 1): p_u_19, (copy 2): v_u_40, (ref 3): v_u_10, (ref 4): l__spui_0, (ref 5): l__menus_0, (ref 6): p_u_27, (ref 7): v_u_4, (ref 8): v_u_36 ]]
                                        local function f_fin() --[[ Name: fin ]] --[[ Line: 95 ]]
                                            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_40, (copy 3): p_u_41, (ref 4): v_u_10, (ref 5): l__spui_0, (ref 6): l__menus_0, (copy 7): p_u_42, (ref 8): p_u_27, (ref 9): v_u_4, (copy 10): p_u_43, (ref 11): v_u_36 ]]
                                            p_u_19._menus:remove_menu(v_u_40)
                                            if p_u_41 then
                                                p_u_27 = v_u_4:table_to_list(p_u_43)
                                                v_u_36:refresh()
                                            else
                                                p_u_19._menus:push_menu(v_u_10:new(p_u_19, l__spui_0, l__menus_0):set_text("Error", p_u_42))
                                            end;
                                        end;
                                        if p44 == true then
                                            p_u_19._player_blob_manager:do_sync(function() --[[ Line: 106 ]]
                                                --[[ Upvalues: (copy 1): f_fin ]]
                                                f_fin()
                                            end)
                                        else
                                            f_fin()
                                        end;
                                    end)
                                    p_u_19._evt:fire_event_to_server(v_u_3.EVT_Lobby_PostGenericMessageClient, p_u_20, p_u_21, p39)
                                end;
                            else
                                return;
                            end;
                        end)
                    end)
                    v_u_5:set_button_text(v38, "\240\159\146\172 Post")
                end;
            end;
        end)
    end;
end;
return v_u_18;
