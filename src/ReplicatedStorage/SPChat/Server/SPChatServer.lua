-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:55 PM
-- Time elapsed: 18 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_7 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessageType)
local v_u_8 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_9 = require(game.ReplicatedStorage.Shared.BuildConfig)
local v_u_10 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_11 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local s_MessagingService_0 = game:GetService("MessagingService")
local s_TextChatService_0 = game:GetService("TextChatService")
local v_u_12 = require(game.ReplicatedStorage.SPChat.Server.SPChatServiceImplementation)
return {
    ["new"] = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_12, (copy 3): v_u_8, (copy 4): v_u_9, (copy 5): v_u_1, (copy 6): v_u_3, (copy 7): v_u_5, (copy 8): v_u_11, (copy 9): v_u_10, (copy 10): v_u_7, (copy 11): v_u_4, (copy 12): s_TextChatService_0, (copy 13): s_MessagingService_0, (copy 14): v_u_6 ]]
        local v14 = {}
        local v_u_15 = false
        v14.is_loaded = function(_) --[[ Name: is_loaded ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        local v_u_16 = nil
        v14.get_chat_service = function(_) --[[ Name: get_chat_service ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        local v_u_17 = v_u_2:new()
        local v_u_18 = v_u_2:new()
        local function _() --[[ Name: cons ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_12, (copy 3): p_u_13, (ref 4): v_u_15 ]]
            v_u_16 = v_u_12:new(p_u_13)
            v_u_15 = true
        end;
        v14.debug_string = function(_) --[[ Name: debug_string ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): v_u_17, (copy 2): v_u_18 ]]
            return string.format("_gameid_to_channelid(%d) _teamid_to_channelid(%d)", v_u_17:count(), v_u_18:count());
        end;
        local v_u_19 = v_u_2:new()
        local v_u_20 = v_u_8:new()
        v14.start = function(p_u_21) --[[ Name: start ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_13, (ref 3): v_u_1, (ref 4): v_u_3, (ref 5): v_u_16, (copy 6): v_u_19, (ref 7): v_u_5, (ref 8): v_u_11, (ref 9): v_u_10, (ref 10): v_u_7, (ref 11): v_u_4, (ref 12): s_TextChatService_0, (copy 13): v_u_20 ]]
            local v22 = string.format("Welcome to RoBeats! Build(%s) server started at [%s].", v_u_9:get_build_time_str(), p_u_13._api:get_server_start_time_str())
            p_u_21:send_global_system_message(v22)
            v_u_1:puts(v22)
            p_u_13._evt:wait_on_event(v_u_3.EVT_Chat_ClientRequestCustomChannel, function(p_u_23) --[[ Line: 57 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_1, (ref 3): p_u_13, (ref 4): v_u_3, (ref 5): v_u_19, (ref 6): v_u_5, (ref 7): v_u_11 ]]
                local function f_response(p24) --[[ Name: response ]] --[[ Line: 58 ]]
                    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_1, (ref 3): p_u_13, (ref 4): v_u_3, (copy 5): p_u_23 ]]
                    local v25 = v_u_16:get_channel(p24)
                    if v25 == nil then
                        return v_u_1:warnf("EVT_Chat_ClientRequestCustomChannel response channel nil");
                    end;
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerRequestCustomChannelResponse, p_u_23, v25:to_table())
                end;
                if v_u_19:contains(p_u_23.UserId) then
                    return f_response(v_u_19:get(p_u_23.UserId));
                end;
                local v_u_26 = v_u_16:create_channel(string.format("%s", p_u_23.Name))
                task.spawn(function() --[[ Line: 72 ]]
                    --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_5, (copy 3): p_u_23, (ref 4): v_u_11, (ref 5): v_u_19, (ref 6): v_u_16, (ref 7): v_u_1, (ref 8): p_u_13, (ref 9): v_u_3 ]]
                    v_u_26:run_if_has_roblox_text_channel(function(p27) --[[ Line: 73 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_23 ]]
                        if v_u_5.UseDirectChatRequesterAPI == true then
                            p27:SetDirectChatRequester(p_u_23)
                        end;
                        p27:AddUserAsync(p_u_23.UserId)
                    end)
                    v_u_26:set_color(v_u_11:get_private_channel_color())
                    v_u_26:add_member(p_u_23.UserId)
                    v_u_19:add(p_u_23.UserId, v_u_26:get_channelid())
                    local v28 = v_u_16:get_channel((v_u_19:get(p_u_23.UserId)))
                    if v28 == nil then
                        v_u_1:warnf("EVT_Chat_ClientRequestCustomChannel response channel nil")
                    else
                        p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerRequestCustomChannelResponse, p_u_23, v28:to_table())
                    end;
                    v_u_16:send_system_message_to_player_for_channel(p_u_23, v_u_26, "Created a new private channel. Invite other players to this channel to start chatting!")
                end)
            end)
            local function _(p29, p30) --[[ Name: get_src_dest_playerid_cooldown_key ]] --[[ Line: 89 ]]
                return string.format("src(%d)_dest(%d)", p29, p30);
            end;
            local function f_player_join_custom_channel(p_u_31, p_u_32) --[[ Name: player_join_custom_channel ]] --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (ref 3): v_u_16, (ref 4): v_u_10, (ref 5): v_u_7, (ref 6): v_u_4, (ref 7): v_u_5 ]]
                local function f_response(p33, p34) --[[ Name: response ]] --[[ Line: 94 ]]
                    --[[ Upvalues: (copy 1): p_u_31, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): v_u_16, (ref 5): v_u_10, (ref 6): v_u_7, (ref 7): v_u_4 ]]
                    if p33 then
                        p34:add_member(p_u_31.UserId)
                    end;
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerAcceptPlayerCustomChannelInviteResponse, p_u_31, p33, p34:to_table())
                    if p33 then
                        v_u_16:send_message_to_channel(v_u_10:new(string.format("%s has joined the channel.", p_u_31.Name)):set_message_type(v_u_7.System), p34)
                    else
                        v_u_16:send_system_message_to_player_for_channel(p_u_31, v_u_16:get_channel(v_u_16:get_server_system_channel_id()), string.format("Could not join private channel."), function(p35) --[[ Line: 116 ]]
                            --[[ Upvalues: (ref 1): v_u_4 ]]
                            p35:set_icon(v_u_4:important_assetid())
                        end)
                    end;
                end;
                if v_u_5.UseRobloxTextChannel == true then
                    task.spawn(function() --[[ Line: 124 ]]
                        --[[ Upvalues: (copy 1): p_u_32, (copy 2): p_u_31, (copy 3): f_response ]]
                        local v_u_36 = false
                        p_u_32:run_if_has_roblox_text_channel(function(p37) --[[ Line: 126 ]]
                            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_36 ]]
                            if p37:AddUserAsync(p_u_31.UserId) ~= nil then
                                v_u_36 = true
                            end;
                        end)
                        f_response(v_u_36, p_u_32)
                    end)
                else
                    f_response(true, p_u_32)
                end;
            end;
            p_u_13._evt:wait_on_event(v_u_3.EVT_Chat_SendPlayerCustomChannelInvite, function(p_u_38, p_u_39) --[[ Line: 139 ]]
                --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_1, (ref 3): v_u_16, (ref 4): p_u_13, (ref 5): v_u_5, (ref 6): s_TextChatService_0, (ref 7): v_u_4, (copy 8): f_player_join_custom_channel, (ref 9): v_u_20, (ref 10): v_u_10 ]]
                if v_u_19:contains(p_u_38.UserId) == true then
                    local v_u_40 = v_u_19:get(p_u_38.UserId)
                    local v41 = v_u_16:get_channel(v_u_40)
                    if v41 == nil then
                        return v_u_1:warnf("EVT_Chat_SendPlayerCustomChannelInvite channel is nil");
                    else
                        local v42 = p_u_13._player_manager:id_to_player(p_u_39)
                        if v42 == nil then
                            return v_u_16:send_system_message_to_player_for_channel(p_u_38, v41, "Player does not exist.");
                        elseif v_u_5.CanSendChannelInviteToSelf == true or not v41:get_members():contains(p_u_39) then
                            local v_u_43 = true
                            pcall(function() --[[ Line: 153 ]]
                                --[[ Upvalues: (ref 1): v_u_43, (ref 2): s_TextChatService_0, (copy 3): p_u_38, (copy 4): p_u_39 ]]
                                v_u_43 = s_TextChatService_0:CanUsersDirectChatAsync(p_u_38.UserId, p_u_39)
                            end)
                            if v_u_43 == false then
                                v_u_16:send_system_message_to_player_for_channel(p_u_38, v_u_16:get_channel(v_u_16:get_server_system_channel_id()), string.format("Could not invite %s to your channel.", v42.Name), function(p44) --[[ Line: 161 ]]
                                    --[[ Upvalues: (ref 1): v_u_4 ]]
                                    p44:set_icon(v_u_4:important_assetid())
                                end)
                            else
                                if v_u_19:contains(p_u_39) then
                                    local v45 = v_u_16:get_channel((v_u_19:get(p_u_39)))
                                    if v45 ~= nil and v45:get_members():contains(p_u_38.UserId) then
                                        return f_player_join_custom_channel(v42, v41);
                                    end;
                                end;
                                local v46 = string.format("src(%d)_dest(%d)", p_u_38.UserId, p_u_39)
                                if v_u_20:is_on_cooldown(v46) then
                                    return v_u_16:send_system_message_to_player_for_channel(p_u_38, v41, string.format("You\'ve already sent %s an invite.", v42.Name));
                                end;
                                v_u_20:add_cooldown_to_id(v46, 10)
                                v_u_16:send_system_message_to_player_for_channel(p_u_38, v41, string.format("Sent invite to %s.", v42.Name))
                                v_u_16:send_system_message_to_player_for_channel(v42, v_u_16:get_channel(v_u_16:get_server_system_channel_id()), string.format("%s has invited you to their channel. Click on this message to join!", p_u_38.Name), function(p47) --[[ Line: 189 ]]
                                    --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_40, (ref 3): v_u_4 ]]
                                    p47:set_extradata(v_u_10.ExtraDataType.JoinCustomChannel, v_u_40)
                                    p47:set_icon(v_u_4:important_assetid())
                                end)
                            end;
                        else
                            return v_u_16:send_system_message_to_player_for_channel(p_u_38, v41, string.format("%s is already in the channel.", v42.Name));
                        end;
                    end;
                else
                    return v_u_1:warnf("EVT_Chat_SendPlayerCustomChannelInvite player does not have custom_channelid");
                end;
            end)
            local function f_channelid_is_custom_channel(p48) --[[ Name: channelid_is_custom_channel ]] --[[ Line: 196 ]]
                --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_16 ]]
                local v49 = nil
                for _, v50 in v_u_19:key_itr() do
                    if p48 == v50 then
                        return v_u_16:get_channel(p48);
                    end;
                end;
                return v49;
            end;
            p_u_13._evt:wait_on_event(v_u_3.EVT_Chat_ClientAcceptPlayerCustomChannelInvite, function(p51, p52) --[[ Line: 207 ]]
                --[[ Upvalues: (copy 1): f_channelid_is_custom_channel, (ref 2): v_u_16, (copy 3): f_player_join_custom_channel ]]
                local v53 = f_channelid_is_custom_channel(p52)
                if v53 == nil then
                    return v_u_16:send_system_message_to_player_for_channel(p51, v_u_16:get_channel(v_u_16:get_server_system_channel_id()), "Channel does not exist.");
                end;
                if v53:get_members():contains(p51.UserId) then
                    return v_u_16:send_system_message_to_player_for_channel(p51, v_u_16:get_channel(v_u_16:get_server_system_channel_id()), "You are already in this channel.");
                end;
                f_player_join_custom_channel(p51, v53)
            end)
            p_u_13._evt:wait_on_event(v_u_3.EVT_Chat_ClientLeaveCustomChannel, function(p54, p55) --[[ Line: 215 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_19, (copy 3): p_u_21, (copy 4): f_channelid_is_custom_channel ]]
                if p55 == v_u_16:get_server_chat_channel_id() or p55 == v_u_16:get_server_system_channel_id() then
                    return v_u_16:send_system_message_to_player_for_channel(p54, v_u_16:get_channel(v_u_16:get_server_system_channel_id()), "Cannot leave this channel.");
                elseif p55 == v_u_19:get(p54.UserId) then
                    p_u_21:remove_player_custom_channel(p54.UserId)
                else
                    local v56 = f_channelid_is_custom_channel(p55)
                    if v56 and v56:get_members():contains(p54.UserId) then
                        p_u_21:remove_player_from_custom_channel(p54.UserId, v56, true)
                        v_u_16:send_system_message_to_player_for_channel(p54, v_u_16:get_channel(v_u_16:get_server_system_channel_id()), "Left the channel.")
                    end;
                end;
            end)
            p_u_13._evt:wait_on_event(v_u_3.EVT_Chat_ClientQueryPlayerInCustomChannel, function(p_u_57, p_u_58) --[[ Line: 232 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (ref 3): v_u_19, (ref 4): v_u_16, (ref 5): v_u_20 ]]
                local function f_response(p59) --[[ Name: response ]] --[[ Line: 233 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_57, (copy 4): p_u_58 ]]
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerQueryPlayerInCustomChannelResponse, p_u_57, p_u_58, p59)
                end;
                if v_u_19:contains(p_u_57.UserId) == true then
                    local v60 = v_u_16:get_channel((v_u_19:get(p_u_57.UserId)))
                    if v60 == nil then
                        return f_response(false);
                    elseif p_u_13._player_manager:id_to_player(p_u_58) == nil then
                        return f_response(false);
                    elseif v_u_20:is_on_cooldown((string.format("src(%d)_dest(%d)", p_u_57.UserId, p_u_58))) then
                        return f_response(false);
                    else
                        return f_response(v60:get_members():contains(p_u_58));
                    end;
                else
                    return f_response(false);
                end;
            end)
        end;
        v14.remove_player_from_all_other_custom_channels = function(p61, p62) --[[ Name: remove_player_from_all_other_custom_channels ]] --[[ Line: 254 ]]
            --[[ Upvalues: (copy 1): v_u_19, (ref 2): v_u_16 ]]
            for v63, v64 in v_u_19:key_itr() do
                if v63 ~= p62 then
                    local v65 = v_u_16:get_channel(v64)
                    if v65 then
                        p61:remove_player_from_custom_channel(p62, v65, true)
                    end;
                end;
            end;
        end;
        v14.remove_player_from_custom_channel = function(_, p66, p67, p68) --[[ Name: remove_player_from_custom_channel ]] --[[ Line: 265 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_3, (ref 3): v_u_16, (ref 4): v_u_10, (ref 5): v_u_7 ]]
            if p67:get_members():contains(p66) then
                local v69 = p_u_13._player_manager:id_to_player(p66)
                if v69 then
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerNotifyLeaveCustomChannel, v69, p67:get_channelid())
                end;
                p67:get_members():remove(p66)
                if v69 and p68 then
                    v_u_16:send_message_to_channel(v_u_10:new(string.format("%s has left the channel.", v69.Name)):set_message_type(v_u_7.System), p67)
                end;
            end;
        end;
        v14.remove_player_custom_channel = function(p_u_70, p71) --[[ Name: remove_player_custom_channel ]] --[[ Line: 286 ]]
            --[[ Upvalues: (copy 1): v_u_19, (ref 2): v_u_16, (copy 3): p_u_13, (ref 4): v_u_10, (ref 5): v_u_7, (ref 6): v_u_2, (ref 7): v_u_1 ]]
            if v_u_19:contains(p71) == true then
                local v72 = v_u_19:get(p71)
                v_u_19:remove(p71)
                local v_u_73 = v_u_16:get_channel(v72)
                local v74 = p_u_13._player_manager:id_to_player(p71)
                if v74 and v_u_73 then
                    v_u_16:send_message_to_channel(v_u_10:new(string.format("Channel creator %s has left, disbanding channel.", v74.Name)):set_message_type(v_u_7.System), v_u_73)
                end;
                v_u_2:remove_if(v_u_73:get_members(), function(_, p75) --[[ Line: 304 ]]
                    --[[ Upvalues: (copy 1): p_u_70, (copy 2): v_u_73 ]]
                    p_u_70:remove_player_from_custom_channel(p75, v_u_73, false)
                    return false;
                end)
                v_u_16:remove_channelid(v72)
                v_u_1:puts("remove_player_custom_channel remove channel(%d)", v72)
            end;
        end;
        v14.send_system_server_chat_message = function(_, p76, p77) --[[ Name: send_system_server_chat_message ]] --[[ Line: 315 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_16, (ref 3): v_u_10, (ref 4): v_u_7 ]]
            v_u_16:send_message_to_channel(v_u_10:new(p76):set_message_type(v_u_7.System), v_u_16:get_channel(v_u_16:get_server_chat_channel_id()), p77 == nil and function(p78) --[[ Line: 317 ]]
                --[[ Upvalues: (ref 1): v_u_4 ]]
                p78:set_icon(v_u_4:important_assetid())
            end or p77)
        end;
        v14.send_global_system_message = function(_, p79) --[[ Name: send_global_system_message ]] --[[ Line: 330 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_10, (ref 3): v_u_7, (ref 4): v_u_4 ]]
            v_u_16:send_message_to_channel(v_u_10:new(p79):set_message_type(v_u_7.System), v_u_16:get_channel(v_u_16:get_server_system_channel_id()), function(p80) --[[ Line: 336 ]]
                --[[ Upvalues: (ref 1): v_u_4 ]]
                p80:set_icon(v_u_4:important_assetid())
            end)
        end;
        v14.create_channel_for_gameid = function(_, p81) --[[ Name: create_channel_for_gameid ]] --[[ Line: 342 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_11, (copy 3): v_u_17 ]]
            local v82 = v_u_16:create_channel("Game")
            v82:set_color(v_u_11:get_game_channel_color())
            v_u_17:add(p81, v82:get_channelid())
        end;
        v14.create_channel_for_teamid = function(_, p83) --[[ Name: create_channel_for_teamid ]] --[[ Line: 348 ]]
            --[[ Upvalues: (copy 1): v_u_18, (ref 2): v_u_16, (ref 3): v_u_11, (ref 4): s_MessagingService_0, (ref 5): v_u_1, (ref 6): v_u_4, (ref 7): v_u_10 ]]
            if v_u_18:contains(p83) then
                return;
            else
                local v_u_84 = v_u_16:create_channel("Team")
                v_u_84:set_color(v_u_11:get_team_channel_color())
                v_u_84:set_broadcast_channel(true, string.format("TeamChat_%d", p83))
                v_u_18:add(p83, v_u_84:get_channelid())
                local v86, v_u_87 = pcall(function() --[[ Line: 355 ]]
                    --[[ Upvalues: (ref 1): s_MessagingService_0, (copy 2): v_u_84, (ref 3): v_u_1, (ref 4): v_u_4, (ref 5): v_u_10, (ref 6): v_u_16 ]]
                    return s_MessagingService_0:SubscribeAsync(v_u_84:get_broadcast_topic(), function(p85) --[[ Line: 356 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_4, (ref 3): v_u_10, (ref 4): v_u_16, (ref 5): v_u_84 ]]
                        if p85.Data == nil then
                            return v_u_1:warnf("MessagingService:SubscribeAsync invalid message(%s)", v_u_4:table_to_string(p85));
                        end;
                        v_u_16:send_message_to_channel(v_u_10:message_from_string(p85.Data), v_u_84)
                    end);
                end)
                if v86 then
                    v_u_84:add_on_removed_fn(function() --[[ Line: 363 ]]
                        --[[ Upvalues: (copy 1): v_u_87 ]]
                        v_u_87:Disconnect()
                    end)
                else
                    v_u_1:warnf("SPChatServer:create_channel_for_teamid MessagingService subscribing error")
                end;
            end;
        end;
        v14.remove_channel_for_gameid = function(p88, p89) --[[ Name: remove_channel_for_gameid ]] --[[ Line: 371 ]]
            --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_16, (ref 3): v_u_4, (ref 4): v_u_1, (copy 5): p_u_13 ]]
            if v_u_17:contains(p89) == true then
                local v90 = v_u_17:get(p89)
                local v91 = v_u_16:get_channel(v90)
                if v91 then
                    if v91:get_members():count() > 0 and v_u_4:is_dev_build() then
                        v_u_1:puts("SPChatServer:remove_channel_for_gameid gameid(%d) channelid(%d) has > 0 members(%d)", p89, v91:get_channelid(), v91:get_members():count())
                    end;
                    for _, v92 in v91:get_members():key_list():key_itr() do
                        local v93 = p_u_13._player_manager:id_to_player(v92)
                        if v93 then
                            p88:remove_player_from_channel_for_gameid(v93, p89)
                        end;
                    end;
                end;
                v_u_16:remove_channelid(v90)
                v_u_17:remove(p89)
            end;
        end;
        v14.remove_channel_for_teamid = function(_, p94) --[[ Name: remove_channel_for_teamid ]] --[[ Line: 396 ]]
            --[[ Upvalues: (copy 1): v_u_18, (ref 2): v_u_16 ]]
            if v_u_18:contains(p94) == true then
                local v95 = v_u_18:get(p94)
                if v_u_16:get_channel(v95) then
                    v_u_16:remove_channelid(v95)
                    v_u_18:remove(p94)
                end;
            end;
        end;
        v14.add_player_to_channel_for_gameid = function(p96, p_u_97, p_u_98) --[[ Name: add_player_to_channel_for_gameid ]] --[[ Line: 406 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_17, (ref 3): v_u_1, (ref 4): v_u_16, (copy 5): p_u_13, (ref 6): v_u_6, (ref 7): v_u_3 ]]
            if p_u_97 == nil then
                return;
            end;
            if v_u_4:is_mock_debug_player(p_u_97) == true then
                return;
            end;
            if v_u_17:contains(p_u_98) ~= true then
                return v_u_1:warnf("SPChatServer:add_player_to_channel_for_gameid(%s, %s) _gameid_to_channelid does not contain gameid", tostring(p_u_97), (tostring(p_u_98)));
            end;
            for v99, v100 in v_u_17:key_itr() do
                local v101 = v_u_16:get_channel(v100)
                if v101 == nil then
                    v_u_1:warnf("SPChatServer:add_player_to_channel_for_gameid\n_gameid_to_channelid:\n%s\n_chat_service:\n%s", p96:debug_string(), v_u_16:debug_string())
                end;
                if v101:get_members():contains(p_u_97.UserId) then
                    p96:remove_player_from_channel_for_gameid(p_u_97, v99)
                    v_u_1:warnf("SPChatServer:add_player_to_channel_for_gameid player(%d) gameid(%d) already in another gameid(%d)", p_u_97.UserId, p_u_98, v99)
                    p_u_13._api:api_report_evt(v_u_6.ReportEvt_ChatDoubleGameInstance, p_u_98, v99, (tostring(p_u_97.UserId)))
                    break;
                end;
            end;
            local v102 = v_u_17:get(p_u_98)
            local v_u_103 = v_u_16:get_channel(v102)
            if v_u_103:get_members():contains(p_u_97.UserId) == true then
                return v_u_1:warnf("SPChatServer:add_player_to_channel_for_gameid already contains player(%s)", (tostring(p_u_97.UserId)));
            end;
            task.spawn(function() --[[ Line: 439 ]]
                --[[ Upvalues: (copy 1): v_u_103, (copy 2): p_u_97, (ref 3): v_u_1, (copy 4): p_u_98 ]]
                v_u_103:run_if_has_roblox_text_channel(function(p104) --[[ Line: 440 ]]
                    --[[ Upvalues: (ref 1): p_u_97, (ref 2): v_u_1, (ref 3): p_u_98 ]]
                    if p104:AddUserAsync(p_u_97.UserId) == nil then
                        v_u_1:warnf("SPChatServer:add_player_to_channel_for_gameid(%d,%d) AddUserAsync failed", p_u_97.UserId, p_u_98)
                    end;
                end)
            end)
            v_u_103:add_member(p_u_97.UserId)
            p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerNotifyJoinGameInstanceChannel, p_u_97, v102, v_u_103:to_table(), p_u_98)
            return true;
        end;
        v14.add_player_to_channel_for_teamid = function(_, p_u_105, p_u_106) --[[ Name: add_player_to_channel_for_teamid ]] --[[ Line: 454 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_18, (ref 3): v_u_1, (ref 4): v_u_16, (copy 5): p_u_13, (ref 6): v_u_3 ]]
            if p_u_105 ~= nil then
                if v_u_4:is_mock_debug_player(p_u_105) ~= true then
                    if v_u_18:contains(p_u_106) ~= true then
                        return v_u_1:warnf("SPChatServer:add_player_to_channel_for_teamid(%s, %s) _teamid_to_channelid does not contain teamid", tostring(p_u_105), (tostring(p_u_106)));
                    end;
                    local v107 = v_u_18:get(p_u_106)
                    local v_u_108 = v_u_16:get_channel(v107)
                    if v_u_108 == nil then
                        return v_u_1:warnf("SPChatServer:add_player_to_channel_for_teamid no channel for id(%s)", (tostring(v107)));
                    end;
                    if v_u_108:get_members():contains(p_u_105.UserId) == true then
                        return v_u_1:warnf("SPChatServer:add_player_to_channel_for_teamid already contains player(%s)", (tostring(p_u_105.UserId)));
                    end;
                    task.spawn(function() --[[ Line: 468 ]]
                        --[[ Upvalues: (copy 1): v_u_108, (copy 2): p_u_105, (ref 3): v_u_1, (copy 4): p_u_106 ]]
                        v_u_108:run_if_has_roblox_text_channel(function(p109) --[[ Line: 469 ]]
                            --[[ Upvalues: (ref 1): p_u_105, (ref 2): v_u_1, (ref 3): p_u_106 ]]
                            if p109:AddUserAsync(p_u_105.UserId) == nil then
                                v_u_1:warnf("SPChatServer:add_player_to_channel_for_teamid(%d,%d) AddUserAsync failed", p_u_105.UserId, p_u_106)
                            end;
                        end)
                    end)
                    v_u_108:add_member(p_u_105.UserId)
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerNotifyJoinTeamChannel, p_u_105, v107, v_u_108:to_table(), p_u_106)
                    p_u_13._guild_manager:get_guild_data(p_u_106, function(p110) --[[ Line: 481 ]]
                        --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_105, (copy 3): v_u_108, (ref 4): v_u_4 ]]
                        v_u_16:send_system_message_to_player_for_channel(p_u_105, v_u_108, string.format("Team \'%s\' message: %s", p110:get_name(), p110:get_message()), function(p111) --[[ Line: 486 ]]
                            --[[ Upvalues: (ref 1): v_u_4 ]]
                            p111:set_icon(v_u_4:get_team_icon())
                        end)
                    end)
                    return true;
                end;
            end;
        end;
        v14.gameid_get_channel = function(_, p112) --[[ Name: gameid_get_channel ]] --[[ Line: 495 ]]
            --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_16 ]]
            local v113 = v_u_17:get(p112)
            if v113 == nil then
                return nil;
            else
                return v_u_16:get_channel(v113);
            end;
        end;
        v14.gameid_send_system_message = function(_, p114, p115, p116) --[[ Name: gameid_send_system_message ]] --[[ Line: 502 ]]
            --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_16, (ref 4): v_u_10, (ref 5): v_u_7 ]]
            if v_u_17:contains(p114) ~= true then
                return v_u_1:warnf("SPChatServer:gameid_send_system_message(%s) _gameid_to_channelid does not contain gameid", (tostring(p114)));
            end;
            v_u_16:send_message_to_channel(v_u_10:new(p115):set_message_type(v_u_7.System), v_u_16:get_channel((v_u_17:get(p114))), p116)
        end;
        v14.remove_player_from_channel_for_gameid = function(_, p_u_117, p118) --[[ Name: remove_player_from_channel_for_gameid ]] --[[ Line: 516 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_17, (ref 3): v_u_1, (ref 4): v_u_16, (copy 5): p_u_13, (ref 6): v_u_3 ]]
            if p_u_117 ~= nil then
                if v_u_4:is_mock_debug_player(p_u_117) ~= true then
                    if v_u_17:contains(p118) ~= true then
                        return v_u_1:warnf("SPChatServer:remove_player_from_channel_for_gameid(%s) _gameid_to_channelid does not contain gameid", (tostring(p118)));
                    end;
                    local v119 = v_u_17:get(p118)
                    local v120 = v_u_16:get_channel(v119)
                    if v120:get_members():contains(p_u_117.UserId) ~= true then
                        return v_u_1:warnf("SPChatServer:remove_player_from_channel_for_gameid(%d,%d) does not contain player", p_u_117.UserId, p118);
                    end;
                    v120:remove_member(p_u_117.UserId)
                    v120:run_if_has_roblox_text_channel(function(p121) --[[ Line: 532 ]]
                        --[[ Upvalues: (copy 1): p_u_117 ]]
                        for _, v122 in pairs(p121:GetChildren()) do
                            if v122.UserId == p_u_117.UserId then
                                v122:Destroy()
                            end;
                        end;
                    end)
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerNotifyLeaveGameInstanceChannel, p_u_117, v119, p118)
                    return true;
                end;
            end;
        end;
        v14.remove_player_from_channel_for_teamid = function(p123, p_u_124, p125) --[[ Name: remove_player_from_channel_for_teamid ]] --[[ Line: 544 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_18, (ref 3): v_u_1, (ref 4): v_u_16, (copy 5): p_u_13, (ref 6): v_u_3 ]]
            if p_u_124 ~= nil then
                if v_u_4:is_mock_debug_player(p_u_124) ~= true then
                    if v_u_18:contains(p125) ~= true then
                        return v_u_1:warnf("SPChatServer:remove_player_from_channel_for_teamid(%s) _teamid_to_channelid does not contain teamid", (tostring(p125)));
                    end;
                    local v126 = v_u_18:get(p125)
                    local v127 = v_u_16:get_channel(v126)
                    if v127:get_members():contains(p_u_124.UserId) ~= true then
                        return v_u_1:warnf("SPChatServer:remove_player_from_channel_for_teamid(%d,%d) does not contain player", p_u_124.UserId, p125);
                    end;
                    v127:remove_member(p_u_124.UserId)
                    v127:run_if_has_roblox_text_channel(function(p128) --[[ Line: 560 ]]
                        --[[ Upvalues: (copy 1): p_u_124 ]]
                        for _, v129 in pairs(p128:GetChildren()) do
                            if v129.UserId == p_u_124.UserId then
                                v129:Destroy()
                            end;
                        end;
                    end)
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_Chat_ServerNotifyLeaveTeamChannel, p_u_124, v126, p125)
                    if v127:get_members():count() <= 0 then
                        p123:remove_channel_for_teamid(p125)
                    end;
                    return true;
                end;
            end;
        end;
        v14.remove_player_from_team_channel = function(p130, p131) --[[ Name: remove_player_from_team_channel ]] --[[ Line: 575 ]]
            --[[ Upvalues: (copy 1): v_u_18, (ref 2): v_u_16, (copy 3): p_u_13 ]]
            for v132, v133 in v_u_18:key_itr() do
                local v134 = v_u_16:get_channel(v133)
                if v134 and v134:get_members():contains(p131) then
                    p130:remove_player_from_channel_for_teamid(p_u_13._player_manager:id_to_player(p131), v132)
                end;
            end;
        end;
        v14.player_disconnecting = function(p135, p136) --[[ Name: player_disconnecting ]] --[[ Line: 584 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16:player_disconnecting(p136)
            p135:remove_player_from_all_other_custom_channels(p136)
            p135:remove_player_custom_channel(p136)
            p135:remove_player_from_team_channel(p136)
        end;
        v14.update = function(_, p137) --[[ Name: update ]] --[[ Line: 592 ]]
            --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_20 ]]
            v_u_16:update(p137)
            v_u_20:update(p137)
        end;
        v_u_16 = v_u_12:new(p_u_13)
        v_u_15 = true
        return v14;
    end
};
