-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_8 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v_u_12 = require(game.ReplicatedStorage.SPChat.Local.BubbleChat)
local v_u_13 = require(game.ReplicatedStorage.SPChat.Local.SPChatMessageLogDisplayAdapter)
local v_u_14 = require(game.ReplicatedStorage.SPChat.Local.SPChatWindowAdapter)
local v_u_15 = require(game.ReplicatedStorage.SPChat.Shared.SPChatChannel)
local v_u_16 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
return {
    ["new"] = function(_, p_u_17) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_10, (copy 3): v_u_6, (copy 4): v_u_7, (copy 5): v_u_2, (copy 6): v_u_12, (copy 7): v_u_14, (copy 8): v_u_1, (copy 9): v_u_16, (copy 10): v_u_3, (copy 11): v_u_15, (copy 12): v_u_9, (copy 13): v_u_13, (copy 14): v_u_4, (copy 15): v_u_8, (copy 16): v_u_11 ]]
        local v19 = {
            ["cleanup_message_log_display"] = function(_, p18) --[[ Name: cleanup_message_log_display ]] --[[ Line: 228 ]]
                p18:Destroy()
            end
        }
        local v_u_20 = nil
        local v_u_21 = nil
        v19.get_chat_window_adapter = function(_) --[[ Name: get_chat_window_adapter ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = v_u_5:new()
        local v_u_25 = v_u_5:new()
        v19.has_game_instance_channel = function(_) --[[ Name: has_game_instance_channel ]] --[[ Line: 35 ]]
            --[[ Upvalues: (copy 1): v_u_24 ]]
            return v_u_24:count() > 0;
        end;
        v19.get_game_instance_channelid = function(p26) --[[ Name: get_game_instance_channelid ]] --[[ Line: 36 ]]
            --[[ Upvalues: (copy 1): v_u_24 ]]
            if p26:has_game_instance_channel() == true then
                return v_u_24:get(v_u_24:count());
            else
                return nil;
            end;
        end;
        v19.get_team_channelid = function(_) --[[ Name: get_team_channelid ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): v_u_25 ]]
            if v_u_25:count() == 0 then
                return nil;
            else
                return v_u_25:get(v_u_25:count());
            end;
        end;
        local v_u_27 = v_u_10:get_invalid_channelid()
        local v_u_28 = nil
        local v_u_29 = false
        local v_u_30 = v_u_6:new()
        v19.get_joined_custom_channels = function(_) --[[ Name: get_joined_custom_channels ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_30 ]]
            return v_u_30;
        end;
        local v_u_31 = v_u_7:new()
        v19.query_is_playerid_in_custom_channel = function(_, p32, p33) --[[ Name: query_is_playerid_in_custom_channel ]] --[[ Line: 52 ]]
            --[[ Upvalues: (copy 1): v_u_31, (copy 2): p_u_17, (ref 3): v_u_2 ]]
            local v34 = v_u_31:list_of(p32):count()
            v_u_31:list_of(p32):push_back(p33)
            if v34 == 0 then
                p_u_17._evt:fire_event_to_server(v_u_2.EVT_Chat_ClientQueryPlayerInCustomChannel, p32)
            end;
        end;
        v19.init = function(p_u_35) --[[ Name: init ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_12, (ref 3): v_u_21, (ref 4): v_u_14, (copy 5): p_u_17, (ref 6): v_u_23, (ref 7): v_u_22, (ref 8): v_u_2, (ref 9): v_u_1, (copy 10): v_u_24, (ref 11): v_u_16, (ref 12): v_u_3, (ref 13): v_u_15, (ref 14): v_u_5, (ref 15): v_u_9, (copy 16): v_u_25, (copy 17): v_u_30, (ref 18): v_u_27, (ref 19): v_u_10, (copy 20): v_u_31 ]]
            v_u_20 = v_u_12:new()
            v_u_21 = v_u_14:new(p_u_17, v_u_20)
            v_u_23 = v_u_21:get_anim_update_fn()
            v_u_22 = v_u_21:get_do_focus_fn()
            p_u_17._evt:wait_on_event(v_u_2.EVT_Chat_ServerNotifyJoinGameInstanceChannel, function(p36, p37, p38) --[[ Line: 67 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_24, (copy 4): p_u_35, (ref 5): v_u_16, (ref 6): v_u_3, (ref 7): v_u_15, (ref 8): v_u_5, (ref 9): v_u_9 ]]
                if v_u_21:is_init() ~= true then
                    return v_u_1:warnf("EVT_Chat_ServerNotifyJoinGameInstanceChannel when _chat_window_adapter not init");
                end;
                if v_u_24:count() > 0 then
                    p_u_35:get_system_channel():add_message_to_channel(v_u_16:new(string.format("ERROR: ServerNotifyJoinGameInstanceChannel(%d) gameid(%d) already in (%d) channels. Channel(%s) TotalChannels(%d) game_instance_channelids(%s)", p36, p38, v_u_24:count(), tostring(v_u_21:get_channel(p36)), v_u_21:get_channel_count(), v_u_3:table_to_string(v_u_24._table))))
                end;
                if p37 == nil then
                    return p_u_35:get_system_channel():add_message_to_channel(v_u_16:new(string.format("ERROR: invalid GameInstanceChannel channelid(%s) gameid(%s)", tostring(p36), (tostring(p38)))));
                end;
                local v39 = v_u_15:from_table(p37)
                if v_u_3:do_disable_chat() then
                    v_u_5:remove_if(v39:get_messages(), function(p40) --[[ Line: 91 ]]
                        return p40:is_speaker_default_userid() ~= true;
                    end)
                end;
                v_u_9:is_true(p36 == v39:get_channelid())
                v_u_24:push_back(p36)
                v_u_21:add_channel(v39)
                v39:register_message_log_display(v_u_21:get_message_log_display(), false)
            end)
            p_u_17._evt:wait_on_event(v_u_2.EVT_Chat_ServerNotifyJoinTeamChannel, function(p41, p42, _) --[[ Line: 102 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_15, (ref 4): v_u_9, (ref 5): v_u_25 ]]
                if v_u_21:is_init() ~= true then
                    return v_u_1:warnf("EVT_Chat_ServerNotifyJoinTeamChannel when _chat_window_adapter not init");
                end;
                local v43 = v_u_15:from_table(p42)
                v_u_9:is_true(p41 == v43:get_channelid())
                v_u_25:push_back(p41)
                v_u_21:add_channel(v43)
                v43:register_message_log_display(v_u_21:get_message_log_display(), false)
            end)
            p_u_17._evt:wait_on_event(v_u_2.EVT_Chat_ServerNotifyLeaveGameInstanceChannel, function(p_u_44, p45) --[[ Line: 113 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_24, (copy 4): p_u_35, (ref 5): v_u_16, (ref 6): v_u_3, (ref 7): v_u_5 ]]
                if v_u_21:is_init() ~= true then
                    return v_u_1:warnf("EVT_Chat_ServerNotifyLeaveGameInstanceChannel when _chat_window_adapter not init");
                end;
                if v_u_24:count() == 0 or v_u_24:count() > 1 then
                    p_u_35:get_system_channel():add_message_to_channel(v_u_16:new(string.format("ERROR: ServerNotifyLeaveGameInstanceChannel(%d) gameid(%d) in (%d) channels. Channel(%s) TotalChannels(%d) game_instance_channelids(%s)", p_u_44, p45, v_u_24:count(), tostring(v_u_21:get_channel(p_u_44)), v_u_21:get_channel_count(), v_u_3:table_to_string(v_u_24._table))))
                end;
                local v46 = v_u_21:get_channel(p_u_44)
                if v46 then
                    v46:unregister_message_log_display(v_u_21:get_message_log_display())
                end;
                v_u_21:remove_channel(p_u_44)
                v_u_5:remove_if(v_u_24, function(p47) --[[ Line: 136 ]]
                    --[[ Upvalues: (copy 1): p_u_44 ]]
                    return p47 == p_u_44;
                end)
            end)
            p_u_17._evt:wait_on_event(v_u_2.EVT_Chat_ServerNotifyLeaveTeamChannel, function(p_u_48, _) --[[ Line: 141 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_5, (ref 4): v_u_25 ]]
                if v_u_21:is_init() ~= true then
                    return v_u_1:warnf("EVT_Chat_ServerNotifyLeaveTeamChannel when _chat_window_adapter not init");
                end;
                local v49 = v_u_21:get_channel(p_u_48)
                if v49 then
                    v49:unregister_message_log_display(v_u_21:get_message_log_display())
                end;
                v_u_21:remove_channel(p_u_48)
                v_u_5:remove_if(v_u_25, function(p50) --[[ Line: 150 ]]
                    --[[ Upvalues: (copy 1): p_u_48 ]]
                    return p50 == p_u_48;
                end)
            end)
            p_u_17._evt:wait_on_event(v_u_2.EVT_Chat_ServerAcceptPlayerCustomChannelInviteResponse, function(p51, p52) --[[ Line: 155 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_15, (ref 3): v_u_30, (ref 4): v_u_21 ]]
                if p51 ~= true then
                    return v_u_1:warnf("EVT_Chat_ServerAcceptPlayerCustomChannelInviteResponse success=false");
                end;
                if p52 then
                    local v53 = v_u_15:from_table(p52)
                    v_u_30:add(v53:get_channelid(), v53)
                    v_u_21:add_channel(v53)
                    v53:register_message_log_display(v_u_21:get_message_log_display(), true)
                    v_u_21:get_message_log_display():sort_all_messages_by_time()
                end;
            end)
            p_u_17._evt:wait_on_event(v_u_2.EVT_Chat_ServerNotifyLeaveCustomChannel, function(p54) --[[ Line: 169 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_30, (ref 4): v_u_27, (ref 5): v_u_10 ]]
                if v_u_21:is_init() ~= true then
                    return v_u_1:warnf("EVT_Chat_ServerNotifyLeaveCustomChannel when _chat_window_adapter not init");
                end;
                v_u_30:remove(p54)
                local v55 = v_u_21:get_channel(p54)
                if v55 then
                    v55:unregister_message_log_display(v_u_21:get_message_log_display())
                end;
                v_u_21:remove_channel(p54)
                if p54 == v_u_27 then
                    v_u_27 = v_u_10:get_invalid_channelid()
                end;
            end)
            p_u_17._evt:wait_on_event(v_u_2.EVT_Chat_ServerQueryPlayerInCustomChannelResponse, function(p56, p57) --[[ Line: 184 ]]
                --[[ Upvalues: (ref 1): v_u_31 ]]
                local v58 = v_u_31:list_of(p56)
                for _, v59 in v58:key_itr() do
                    v59(p57)
                end;
                v58:clear()
            end)
        end;
        v19.can_request_custom_channel = function(_) --[[ Name: can_request_custom_channel ]] --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_10, (ref 3): v_u_29 ]]
            local v60
            if v_u_27 == v_u_10:get_invalid_channelid() then
                v60 = v_u_29 == false
            else
                v60 = false
            end;
            return v60;
        end;
        v19.has_custom_channel = function(_) --[[ Name: has_custom_channel ]] --[[ Line: 195 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_10 ]]
            return v_u_27 ~= v_u_10:get_invalid_channelid();
        end;
        v19.get_custom_channel_id = function(_) --[[ Name: get_custom_channel_id ]] --[[ Line: 196 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v19.get_custom_channel = function(_) --[[ Name: get_custom_channel ]] --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v19.request_custom_channel = function(p61, p_u_62) --[[ Name: request_custom_channel ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_29, (copy 3): p_u_17, (ref 4): v_u_2, (ref 5): v_u_15, (ref 6): v_u_28, (copy 7): v_u_30, (ref 8): v_u_27, (ref 9): v_u_21 ]]
            if p61:can_request_custom_channel() ~= true then
                if p_u_62 then
                    p_u_62()
                end;
                return v_u_1:warnf("SPChatLocal:request_custom_channel can_request_custom_channel invalid");
            end;
            v_u_29 = true
            p_u_17._evt:wait_on_event_once(v_u_2.EVT_Chat_ServerRequestCustomChannelResponse, function(p63) --[[ Line: 205 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_28, (ref 3): v_u_30, (ref 4): v_u_27, (ref 5): v_u_29, (ref 6): v_u_21, (copy 7): p_u_62 ]]
                local v64 = v_u_15:from_table(p63)
                v_u_28 = v64
                v_u_30:add(v64:get_channelid(), v64)
                v_u_27 = v64:get_channelid()
                v_u_29 = false
                v_u_21:add_channel(v64)
                v64:register_message_log_display(v_u_21:get_message_log_display(), true)
                if p_u_62 then
                    p_u_62()
                end;
            end)
            p_u_17._evt:fire_event_to_server(v_u_2.EVT_Chat_ClientRequestCustomChannel)
        end;
        v19.request_join_custom_channel_of_id = function(_, p65) --[[ Name: request_join_custom_channel_of_id ]] --[[ Line: 218 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_2 ]]
            p_u_17._evt:fire_event_to_server(v_u_2.EVT_Chat_ClientAcceptPlayerCustomChannelInvite, p65)
        end;
        v19.make_message_log_display = function(_, p66) --[[ Name: make_message_log_display ]] --[[ Line: 224 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_17 ]]
            return v_u_13:new(p_u_17, p66);
        end;
        v19.get_game_instance_channel = function(p67) --[[ Name: get_game_instance_channel ]] --[[ Line: 232 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            if p67:has_game_instance_channel() == false then
                return nil;
            else
                return v_u_21:get_channel(p67:get_game_instance_channelid());
            end;
        end;
        v19.get_channel_by_id = function(_, p68) --[[ Name: get_channel_by_id ]] --[[ Line: 238 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21:get_channel(p68);
        end;
        v19.get_channel_by_name = function(_, p69) --[[ Name: get_channel_by_name ]] --[[ Line: 242 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21:get_channel_by_name(p69);
        end;
        v19.get_system_channel = function(_) --[[ Name: get_system_channel ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21:get_system_channel();
        end;
        v19.post_message_to_gameinstance = function(p70, p71) --[[ Name: post_message_to_gameinstance ]] --[[ Line: 250 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_16 ]]
            if p70:get_game_instance_channelid() ~= nil then
                v_u_21:send_message(v_u_16:new(p71):set_channelid(p70:get_game_instance_channelid()))
            end;
        end;
        v_u_4:new(0, 0, 0, 0)
        v_u_4:new(0, 0, 0, 0)
        v19.get_chat_window_nsize = function(_) --[[ Name: get_chat_window_nsize ]] --[[ Line: 258 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21:get_chat_window():get_base_frame_nrect();
        end;
        local v_u_72 = true
        v19.store_chat_visible = function(_) --[[ Name: store_chat_visible ]] --[[ Line: 263 ]]
            --[[ Upvalues: (ref 1): v_u_72, (ref 2): v_u_21 ]]
            v_u_72 = v_u_21:get_visible()
        end;
        v19.get_stored_chat_visible = function(_) --[[ Name: get_stored_chat_visible ]] --[[ Line: 266 ]]
            --[[ Upvalues: (ref 1): v_u_72 ]]
            return v_u_72;
        end;
        v19.set_chat_visible = function(_, p_u_73) --[[ Name: set_chat_visible ]] --[[ Line: 268 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            if v_u_21 then
                v_u_21:set_visible(p_u_73)
            else
                spawn(function() --[[ Line: 272 ]]
                    --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_73 ]]
                    while v_u_21 == nil do
                        wait(0.25)
                    end;
                    v_u_21:set_visible(p_u_73)
                end)
            end;
        end;
        v19.get_chat_visible = function(_) --[[ Name: get_chat_visible ]] --[[ Line: 281 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21:get_visible();
        end;
        v19.disable = function(_) --[[ Name: disable ]] --[[ Line: 283 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21:disable()
        end;
        v19.do_press_trigger = function(_) --[[ Name: do_press_trigger ]] --[[ Line: 287 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_17, (ref 3): v_u_8 ]]
            if v_u_3:is_mobile() then
                local v74 = p_u_17._chat:get_chat_visible() and p_u_17._input:control_just_released(v_u_8.KEY_CLICK)
                if v74 then
                    v74 = p_u_17._input:get_touch_move_count() < 10
                end;
                return v74;
            else
                local v75 = p_u_17._chat:get_chat_visible()
                if v75 then
                    v75 = p_u_17._input:control_just_pressed(v_u_8.KEY_CLICK)
                end;
                return v75;
            end;
        end;
        local l_Chat_0 = v_u_11.Test.Chat
        v19.update = function(p76, _) --[[ Name: update ]] --[[ Line: 298 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23, (ref 3): v_u_11, (copy 4): l_Chat_0, (copy 5): p_u_17, (ref 6): v_u_3, (ref 7): v_u_8, (ref 8): v_u_20 ]]
            if v_u_22 == nil or v_u_23 == nil then
                return;
            else
                local v77 = v_u_11:singleton()
                if v77:should_run(l_Chat_0) ~= false then
                    local v78 = v77:get_test_state(l_Chat_0)
                    local v79 = v78:get_dt_scale()
                    p_u_17._input:set_frame_index_state(v78)
                    if p76:get_chat_window_nsize():contains_vec2((v_u_3:get_cursor_nxy())) == true then
                        p_u_17._input:set_has_frame_focused_element(true)
                    end;
                    if not v_u_3:do_disable_chat() and p_u_17._input:control_just_pressed(v_u_8.KEY_CHAT_WINDOW_FOCUS) then
                        v_u_22()
                    end;
                    if v_u_20 then
                        if game.Players and (game.Players.LocalPlayer and game.Players.LocalPlayer.Character) then
                            v_u_20:set_enabled(true)
                        else
                            v_u_20:set_enabled(false)
                        end;
                        v_u_20:update()
                    end;
                    v_u_23(v79)
                    p_u_17._input:set_frame_index_state(nil)
                end;
            end;
        end;
        return v19;
    end
};
