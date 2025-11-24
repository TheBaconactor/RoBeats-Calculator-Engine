-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessageType)
local v_u_2 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_9 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_10 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_11 = require(game.ReplicatedStorage.SPChat.Shared.SPChatChannel)
local v_u_12 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_13 = require(game.ReplicatedStorage.SPChat.Server.SPChatServerPlayerInfo)
local s_MessagingService_0 = game:GetService("MessagingService")
local s_TextChatService_0 = game:GetService("TextChatService")
local v14 = {}
local v_u_15 = 1
local function _() --[[ Name: alloc_channel_id ]] --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_15 ]]
    local v16 = v_u_15
    v_u_15 = v_u_15 + 1
    if v_u_15 >= 20000000000 then
        v_u_15 = 0
    end;
    return v16;
end;
local v_u_17 = 0
local function _() --[[ Name: alloc_message_id ]] --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_17 ]]
    local v18 = v_u_17
    v_u_17 = v_u_17 + 1
    if v_u_17 >= 20000000000 then
        v_u_17 = 0
    end;
    return v18;
end;
v14.new = function(_, p_u_19) --[[ Name: new ]] --[[ Line: 40 ]]
    --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_3, (copy 3): s_TextChatService_0, (copy 4): v_u_2, (copy 5): v_u_6, (copy 6): v_u_11, (copy 7): v_u_10, (copy 8): v_u_5, (copy 9): v_u_4, (copy 10): v_u_13, (copy 11): v_u_12, (ref 12): v_u_17, (copy 13): v_u_1, (copy 14): v_u_7, (copy 15): v_u_8, (copy 16): s_MessagingService_0, (copy 17): v_u_9 ]]
    local v_u_20 = {}
    local v_u_21 = v_u_15
    v_u_15 = v_u_15 + 1
    if v_u_15 >= 20000000000 then
        v_u_15 = 0
    end;
    local v_u_22 = v_u_15
    v_u_15 = v_u_15 + 1
    if v_u_15 >= 20000000000 then
        v_u_15 = 0
    end;
    v_u_20.get_server_chat_channel_id = function(_) --[[ Name: get_server_chat_channel_id ]] --[[ Line: 45 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        return v_u_21;
    end;
    v_u_20.get_server_system_channel_id = function(_) --[[ Name: get_server_system_channel_id ]] --[[ Line: 46 ]]
        --[[ Upvalues: (copy 1): v_u_22 ]]
        return v_u_22;
    end;
    local v_u_23 = v_u_3:new()
    local v_u_24 = v_u_3:new()
    local l_Folder_0 = Instance.new("Folder")
    l_Folder_0.Name = "SPChatServiceImplementation_ChatChannelFolder"
    pcall(function() --[[ Line: 53 ]]
        --[[ Upvalues: (copy 1): l_Folder_0, (ref 2): s_TextChatService_0 ]]
        l_Folder_0.Parent = s_TextChatService_0
    end)
    if l_Folder_0.Parent == nil then
        v_u_2:warnf("SPChatServiceImplementation:new failed to parent _chat_channel_folder to TextChatService")
        l_Folder_0.Parent = game.ReplicatedStorage
    end;
    local function f_create_roblox_text_channel_for_spchatchannel(p25) --[[ Name: create_roblox_text_channel_for_spchatchannel ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): l_Folder_0 ]]
        if v_u_6.UseRobloxTextChannel == true then
            local l_TextChannel_0 = Instance.new("TextChannel")
            l_TextChannel_0.Name = string.format("%s_%d", p25:get_name(), p25:get_channelid())
            l_TextChannel_0.Parent = l_Folder_0
            p25:set_roblox_text_channel(l_TextChannel_0)
        end;
        return p25;
    end;
    v_u_20.run_if_sp_chat_channel_exists_for_id = function(_, p26, p27) --[[ Name: run_if_sp_chat_channel_exists_for_id ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): v_u_23 ]]
        if v_u_23:contains(p26) then
            p27(v_u_23:get(p26))
        end;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 77 ]]
        --[[ Upvalues: (copy 1): v_u_23, (copy 2): v_u_20, (copy 3): f_create_roblox_text_channel_for_spchatchannel, (ref 4): v_u_11, (ref 5): v_u_10, (ref 6): v_u_5, (ref 7): v_u_6, (ref 8): v_u_2, (copy 9): p_u_19, (ref 10): v_u_4, (copy 11): v_u_24, (ref 12): v_u_13, (copy 13): v_u_21, (copy 14): v_u_22, (ref 15): v_u_12 ]]
        v_u_23:add(v_u_20:get_server_chat_channel_id(), (f_create_roblox_text_channel_for_spchatchannel(v_u_11:new(v_u_20:get_server_chat_channel_id(), "All"):set_default_channel(true):set_color(v_u_10:get_all_channel_color()))))
        v_u_23:add(v_u_20:get_server_system_channel_id(), (f_create_roblox_text_channel_for_spchatchannel(v_u_11:new(v_u_20:get_server_system_channel_id(), "System"):set_default_channel(true):set_players_can_message(false):set_color(v_u_10:get_system_channel_color()))))
        if v_u_5:is_dev_build() and v_u_6.UseRobloxTextChannel == true then
            v_u_23:get(v_u_20:get_server_chat_channel_id()):run_if_has_roblox_text_channel(function(p28) --[[ Line: 97 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                p28.ShouldDeliverCallback = function(p29, p30) --[[ Line: 98 ]]
                    --[[ Upvalues: (ref 1): v_u_2 ]]
                    v_u_2:puts("SPChatServiceImplementation DEBUG ShouldDeliverCallback message source(%d) can_send(%s) meta(%s) text(%s)", p30.UserId, tostring(p30.CanSend), p29.Metadata, p29.Text)
                    return true;
                end;
            end)
        end;
        p_u_19._evt:wait_on_event(v_u_4.EVT_Chat_ClientRequestInitialData, function(p_u_31) --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_2, (ref 3): v_u_13, (ref 4): v_u_6, (ref 5): v_u_20, (ref 6): v_u_23, (ref 7): v_u_21, (ref 8): v_u_22, (ref 9): p_u_19, (ref 10): v_u_4 ]]
            if v_u_24:contains(p_u_31.UserId) then
                return v_u_2:warnf("EVT_Chat_ClientRequestInitialData already contains player(%s)", (tostring(p_u_31.UserId)));
            end;
            v_u_24:add(p_u_31.UserId, v_u_13:new())
            if v_u_6.UseRobloxTextChannel == true then
                v_u_20:run_if_sp_chat_channel_exists_for_id(v_u_20:get_server_chat_channel_id(), function(p32) --[[ Line: 111 ]]
                    --[[ Upvalues: (copy 1): p_u_31 ]]
                    p32:run_if_has_roblox_text_channel(function(p33) --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): p_u_31 ]]
                        p33:AddUserAsync(p_u_31.UserId)
                    end)
                end)
                v_u_20:run_if_sp_chat_channel_exists_for_id(v_u_20:get_server_chat_channel_id(), function(p34) --[[ Line: 116 ]]
                    --[[ Upvalues: (copy 1): p_u_31 ]]
                    p34:run_if_has_roblox_text_channel(function(p35) --[[ Line: 117 ]]
                        --[[ Upvalues: (ref 1): p_u_31 ]]
                        p35:AddUserAsync(p_u_31.UserId)
                    end)
                end)
            end;
            local function f_get_rtv_table() --[[ Name: get_rtv_table ]] --[[ Line: 123 ]]
                --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_21, (ref 3): v_u_22 ]]
                return {
                    ["ServerChatChannel"] = v_u_23:get(v_u_21):to_table(),
                    ["ServerSystemChannel"] = v_u_23:get(v_u_22):to_table()
                };
            end;
            local v_u_36 = f_get_rtv_table()
            local function f_response() --[[ Name: response ]] --[[ Line: 130 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_4, (copy 3): p_u_31, (ref 4): v_u_36 ]]
                p_u_19._evt:fire_event_to_client(v_u_4.EVT_Chat_ServerRespondInitialData, p_u_31, v_u_36)
                local v37, v38 = p_u_19._guild_manager:is_player_in_guild(p_u_31.UserId)
                if v37 then
                    p_u_19._chat:create_channel_for_teamid(v38)
                    p_u_19._chat:add_player_to_channel_for_teamid(p_u_31, v38)
                end;
            end;
            if v_u_36.ServerChatChannel and v_u_36.ServerSystemChannel then
                f_response()
            else
                spawn(function() --[[ Line: 143 ]]
                    --[[ Upvalues: (ref 1): v_u_36, (copy 2): f_get_rtv_table, (copy 3): f_response ]]
                    while v_u_36.ServerChatChannel == nil or v_u_36.ServerSystemChannel == nil do
                        v_u_36 = f_get_rtv_table()
                        wait(0.5)
                    end;
                    f_response()
                end)
            end;
        end)
        p_u_19._evt:wait_on_event(v_u_4.EVT_Chat_ClientSendMessage, function(p39, p40) --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_20 ]]
            local v41 = v_u_12:message_from_table(p40)
            local v42 = v41:get_channelid()
            if v_u_23:contains(v42) ~= true then
                return v_u_2:warnf("EVT_Chat_ClientSendMessage does not contain channelid(%s)", (tostring(v42)));
            end;
            v_u_20:send_player_message_to_channel(p39, v41, (v_u_23:get(v42)))
        end)
    end;
    local function f_foreach_channel_player(p43, p44) --[[ Name: foreach_channel_player ]] --[[ Line: 163 ]]
        --[[ Upvalues: (copy 1): p_u_19, (copy 2): v_u_24 ]]
        if p43:is_default_channel() then
            for _, v45 in p_u_19._player_manager:players_key_itr() do
                if v_u_24:contains(v45.UserId) then
                    p44(v45, v_u_24:get(v45.UserId))
                end;
            end;
        else
            for v46, _ in p43:get_members():key_itr() do
                local v47 = p_u_19._player_manager:id_to_player(v46)
                if v47 and v_u_24:contains(v47.UserId) then
                    p44(v47, v_u_24:get(v47.UserId))
                end;
            end;
        end;
    end;
    local function f_apply_params_to_message_for_channel(p48, p49) --[[ Name: apply_params_to_message_for_channel ]] --[[ Line: 180 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_5 ]]
        p48:set_time(os.time())
        p48:set_channelid(p49:get_channelid())
        p48:set_channel_name(p49:get_name())
        local v50 = v_u_17
        v_u_17 = v_u_17 + 1
        if v_u_17 >= 20000000000 then
            v_u_17 = 0
        end;
        p48:set_message_id(v50)
        p48:set_channel_color(p49:get_color())
        if p48:get_message_type() == v_u_1.System then
            p48:set_icon(v_u_5:gear_assetid())
        end;
    end;
    v_u_20.send_system_message_to_player_for_channel = function(_, p51, p52, p53, p54) --[[ Name: send_system_message_to_player_for_channel ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_1, (copy 3): f_apply_params_to_message_for_channel, (copy 4): p_u_19, (ref 5): v_u_4 ]]
        local v55 = v_u_12:new(p53):set_message_type(v_u_1.System)
        f_apply_params_to_message_for_channel(v55, p52)
        if p54 then
            p54(v55)
        end;
        p_u_19._evt:fire_event_to_client(v_u_4.EVT_Chat_ServerOnNewMessage, p51, (v_u_12:message_to_table(v55)))
    end;
    v_u_20.send_message_to_channel = function(_, p56, p57, p58) --[[ Name: send_message_to_channel ]] --[[ Line: 203 ]]
        --[[ Upvalues: (copy 1): f_apply_params_to_message_for_channel, (ref 2): v_u_12, (copy 3): f_foreach_channel_player, (copy 4): p_u_19, (ref 5): v_u_4 ]]
        f_apply_params_to_message_for_channel(p56, p57)
        if p58 then
            p58(p56, p57)
        end;
        p57:add_message_to_channel(p56)
        local v_u_59 = v_u_12:message_to_table(p56)
        f_foreach_channel_player(p57, function(p60) --[[ Line: 212 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_4, (copy 3): v_u_59 ]]
            p_u_19._evt:fire_event_to_client(v_u_4.EVT_Chat_ServerOnNewMessage, p60, v_u_59)
        end)
    end;
    v_u_20.send_player_message_to_channel = function(p61, p_u_62, p_u_63, p_u_64) --[[ Name: send_player_message_to_channel ]] --[[ Line: 217 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_10, (copy 3): p_u_19, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_5, (ref 7): s_MessagingService_0, (ref 8): v_u_12, (ref 9): v_u_2, (ref 10): v_u_4, (copy 11): f_foreach_channel_player ]]
        if p_u_64:get_players_can_message() == true then
            if v_u_24:contains(p_u_62.UserId) == true then
                local v_u_65 = v_u_24:get(p_u_62.UserId)
                if v_u_65:is_channelid_on_chat_cooldown(p_u_64:get_channelid()) then
                    return p61:send_system_message_to_player_for_channel(p_u_62, p_u_64, (string.format("You must wait %d second(s) until sending your next message.", v_u_65:get_time_to_channelid_message_queue_pop_sec(p_u_64:get_channelid()))));
                elseif p_u_64:is_default_channel() == true or p_u_64:get_members():contains(p_u_62.UserId) == true then
                    if #p_u_63:get_message() > v_u_10:get_chat_max_message_length() then
                        return p61:send_system_message_to_player_for_channel(p_u_62, p_u_64, "Your message exceeds the maximum allowed length.");
                    elseif v_u_10:message_contains_invalid_whitespace(p_u_63:get_message()) then
                        return p61:send_system_message_to_player_for_channel(p_u_62, p_u_64, "Your message contains whitespace that is not allowed.");
                    else
                        p_u_63:set_speaker_name(p_u_62.Name)
                        p_u_63:set_speaker_userid(p_u_62.UserId)
                        local v66 = p_u_19._player_blob_manager:get_cached_blob(p_u_62.UserId)
                        if v66 ~= nil then
                            p_u_63:set_icon(v_u_10:playerblob_get_chat_icon(v66))
                            local v67 = v_u_7:get_title_id(v66)
                            if v_u_8:singleton():contains_title_for_id(v67) then
                                local v68 = v_u_8:singleton():get_title_for_id(v67):get_color()
                                if v68 == v_u_5:color3(255, 255, 255) then
                                    p_u_63:set_name_color(v_u_10:get_speaker_name_default_color())
                                else
                                    p_u_63:set_name_color(v68)
                                end;
                            end;
                        end;
                        local v_u_69 = p_u_63:get_message()
                        local v70 = #v_u_69
                        if p_u_64:is_broadcast_channel() then
                            spawn(function() --[[ Line: 258 ]]
                                --[[ Upvalues: (copy 1): p_u_63, (ref 2): v_u_5, (copy 3): v_u_69, (copy 4): p_u_62, (copy 5): v_u_65, (copy 6): p_u_64, (ref 7): s_MessagingService_0, (ref 8): v_u_12, (ref 9): v_u_2, (ref 10): p_u_19, (ref 11): v_u_4 ]]
                                p_u_63:set_message(v_u_5:filter_string(v_u_69, p_u_62, p_u_62))
                                p_u_63:set_filtered(true)
                                v_u_65:add_channelid_chat_message(p_u_64:get_channelid(), p_u_63)
                                local v71, v72 = pcall(function() --[[ Line: 262 ]]
                                    --[[ Upvalues: (ref 1): s_MessagingService_0, (ref 2): p_u_64, (ref 3): v_u_12, (ref 4): p_u_63 ]]
                                    s_MessagingService_0:PublishAsync(p_u_64:get_broadcast_topic(), v_u_12:message_to_string(p_u_63))
                                end)
                                if not v71 then
                                    v_u_2:warnf("SPChatServiceImplementation:send_player_message_to_channel is_team_channel MessagingService publish error(%s)", v72)
                                    p_u_19._evt:fire_event_to_client(v_u_4.EVT_Chat_ServerNotifyChatResponse, p_u_62, p_u_64:get_channelid(), v72)
                                end;
                            end)
                        else
                            p_u_63:set_filtered(false)
                            p_u_63:set_message(v_u_10:message_unfiltered_placeholder_of_length(v70))
                            p61:send_message_to_channel(p_u_63, p_u_64)
                            v_u_65:add_channelid_chat_message(p_u_64:get_channelid(), p_u_63)
                            v_u_5:spawn(function() --[[ Line: 278 ]]
                                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_63, (ref 3): v_u_5, (copy 4): v_u_69, (copy 5): p_u_62, (ref 6): f_foreach_channel_player, (copy 7): p_u_64, (ref 8): p_u_19, (ref 9): v_u_4 ]]
                                local v_u_73 = v_u_12:message_to_table(p_u_63)
                                local v74 = v_u_5:filter_string(v_u_69, p_u_62)
                                if p_u_63:is_filtered() ~= true then
                                    p_u_63:set_filtered(true)
                                    p_u_63:set_message(v74)
                                end;
                                v_u_12:table_set_filtered_message(v_u_73, v74)
                                f_foreach_channel_player(p_u_64, function(p75) --[[ Line: 288 ]]
                                    --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_4, (copy 3): v_u_73 ]]
                                    p_u_19._evt:fire_event_to_client(v_u_4.EVT_Chat_ServerOnMessageFiltered, p75, v_u_73)
                                end)
                            end)
                        end;
                    end;
                else
                    return p61:send_system_message_to_player_for_channel(p_u_62, p_u_64, "You are not allowed to speak in this channel.");
                end;
            else
                return p61:send_system_message_to_player_for_channel(p_u_62, p_u_64, "ERROR: player info not found");
            end;
        else
            return p61:send_system_message_to_player_for_channel(p_u_62, p_u_64, "You cannot speak in this channel.");
        end;
    end;
    v_u_20.create_channel = function(_, p76) --[[ Name: create_channel ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_23, (copy 3): f_create_roblox_text_channel_for_spchatchannel, (ref 4): v_u_11 ]]
        local v77 = v_u_15
        v_u_15 = v_u_15 + 1
        if v_u_15 >= 20000000000 then
            v_u_15 = 0
        end;
        v_u_23:add(v77, (f_create_roblox_text_channel_for_spchatchannel(v_u_11:new(v77, p76))))
        return v_u_23:get(v77);
    end;
    v_u_20.remove_channelid = function(_, p78) --[[ Name: remove_channelid ]] --[[ Line: 315 ]]
        --[[ Upvalues: (copy 1): v_u_23 ]]
        if v_u_23:contains(p78) then
            local v79 = v_u_23:get(p78)
            if v79:get_roblox_text_channel() ~= nil then
                local v80 = v79:get_roblox_text_channel()
                v79:set_roblox_text_channel(nil)
                v80:Destroy()
            end;
            v79:on_removed()
        end;
        v_u_23:remove(p78)
    end;
    v_u_20.get_channel = function(_, p81) --[[ Name: get_channel ]] --[[ Line: 330 ]]
        --[[ Upvalues: (copy 1): v_u_23 ]]
        return v_u_23:get(p81);
    end;
    v_u_20.debug_string = function(_) --[[ Name: debug_string ]] --[[ Line: 334 ]]
        --[[ Upvalues: (copy 1): v_u_23 ]]
        local v82 = ""
        for v83, v84 in v_u_23:key_itr() do
            v82 = v82 .. string.format("\tid(%d) -> %s\n", v83, v84:debug_string())
        end;
        return v82;
    end;
    v_u_20.player_disconnecting = function(_, p85) --[[ Name: player_disconnecting ]] --[[ Line: 342 ]]
        --[[ Upvalues: (copy 1): v_u_24 ]]
        v_u_24:remove(p85)
    end;
    local v_u_86 = v_u_9:new()
    v_u_86:add_cooldown(2.5)
    v_u_20.update = function(_, p87) --[[ Name: update ]] --[[ Line: 351 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_6, (copy 3): v_u_86, (copy 4): v_u_23, (copy 5): p_u_19, (ref 6): v_u_2 ]]
        for _, v88 in v_u_24:key_itr() do
            v88:update(p87)
        end;
        if v_u_6.UseRobloxTextChannel == true then
            v_u_86:update(p87)
            if v_u_86:is_on_cooldown() ~= true then
                v_u_86:add_cooldown(2.5)
                pcall(function() --[[ Line: 361 ]]
                    --[[ Upvalues: (ref 1): v_u_23, (ref 2): p_u_19, (ref 3): v_u_2 ]]
                    for _, v89 in v_u_23:key_itr() do
                        v89:run_if_has_roblox_text_channel(function(p90) --[[ Line: 363 ]]
                            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_2 ]]
                            for _, v91 in pairs(p90:GetChildren()) do
                                if v91.ClassName == "TextSource" and p_u_19._player_manager:id_to_player(v91.UserId) == nil then
                                    v91:Destroy()
                                    v_u_2:warnf("SPChatServiceImplementation:update removing player(%d) from roblox_text_channel(%s)", v91.UserId, p90:GetFullName())
                                end;
                            end;
                        end)
                    end;
                end)
            end;
        end;
    end;
    f_cons()
    return v_u_20;
end;
return v14;
