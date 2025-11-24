-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.AssertType)
local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_4 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_6 = require(game.ReplicatedStorage.SPChat.Shared.SPChatChannel)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["new"] = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_2, (copy 4): v_u_7, (copy 5): v_u_6, (copy 6): v_u_3, (copy 7): v_u_4 ]]
        local v9 = {
            ["cons"] = function(_) end,
            ["update"] = function(_, _) end
        }
        local v_u_10 = nil
        local v_u_11 = nil
        v9.get_server_chat_channel_id = function(_) --[[ Name: get_server_chat_channel_id ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end;
        v9.get_server_system_channel_id = function(_) --[[ Name: get_server_system_channel_id ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        local function v_u_12(_) --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("_on_new_message_fn not set")
        end;
        local function v_u_13(_) --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("_on_message_done_filtering_fn not set")
        end;
        local function v_u_14(_) --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("_on_add_channel_fn not set")
        end;
        local function v_u_15(_) --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("_on_remove_channel_fn not set")
        end;
        v9.set_on_new_message_fn = function(_, p16) --[[ Name: set_on_new_message_fn ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            v_u_12 = p16
        end;
        v9.set_on_message_done_filtering_fn = function(_, p17) --[[ Name: set_on_message_done_filtering_fn ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            v_u_13 = p17
        end;
        v9.set_on_add_channel_fn = function(_, p18) --[[ Name: set_on_add_channel_fn ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            v_u_14 = p18
        end;
        v9.set_on_remove_channel_fn = function(_, p19) --[[ Name: set_on_remove_channel_fn ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15 = p19
        end;
        local v_u_20 = false
        v9.is_init = function(_) --[[ Name: is_init ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        v9.on_init = function(_, p_u_21) --[[ Name: on_init ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_2, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_3, (ref 8): v_u_10, (ref 9): v_u_14, (ref 10): v_u_11, (ref 11): v_u_4, (ref 12): v_u_12, (ref 13): v_u_13, (ref 14): v_u_20 ]]
            p_u_8._evt:wait_on_event_once(v_u_5.EVT_Chat_ServerRespondInitialData, function(p22) --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_2, (ref 3): v_u_7, (ref 4): v_u_6, (ref 5): v_u_3, (ref 6): v_u_10, (ref 7): v_u_14, (ref 8): v_u_11, (ref 9): p_u_8, (ref 10): v_u_5, (ref 11): v_u_4, (ref 12): v_u_12, (ref 13): v_u_13, (ref 14): v_u_20, (copy 15): p_u_21 ]]
                if p22 == nil then
                    return v_u_1:warnf("EVT_Chat_ServerRespondInitialData chat_initial_data nil");
                end;
                if p22.ServerChatChannel then
                    if v_u_2:is_debug_user() and v_u_7.DebugChatLogging == true then
                        v_u_1:puts("SPChatEventNewImplementationAdapter EVT_Chat_ServerRespondInitialData chat_initial_data.ServerChatChannel")
                        print(v_u_2:table_to_string(p22.ServerChatChannel))
                    end;
                    local v23 = v_u_6:from_table(p22.ServerChatChannel)
                    if v_u_2:do_disable_chat() then
                        v_u_3:remove_if(v23:get_messages(), function(p24) --[[ Line: 52 ]]
                            return p24:is_speaker_default_userid() ~= true;
                        end)
                    end;
                    v_u_10 = v23:get_channelid()
                    v_u_14(v23)
                else
                    v_u_1:warnf("EVT_Chat_ServerRespondInitialData chat_initial_data.ServerChatChannel nil")
                end;
                if p22.ServerSystemChannel then
                    local v25 = v_u_6:from_table(p22.ServerSystemChannel)
                    v_u_11 = v25:get_channelid()
                    v_u_14(v25)
                else
                    v_u_1:warnf("EVT_Chat_ServerRespondInitialData chat_initial_data.ServerChatChannel nil")
                end;
                p_u_8._evt:wait_on_event(v_u_5.EVT_Chat_ServerOnNewMessage, function(p26) --[[ Line: 70 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2, (ref 3): v_u_12 ]]
                    local v27 = v_u_4:message_from_table(p26)
                    if not v_u_2:do_disable_chat() or v27:is_speaker_default_userid() == true then
                        v_u_12(v27)
                    end;
                end)
                p_u_8._evt:wait_on_event(v_u_5.EVT_Chat_ServerOnMessageFiltered, function(p28) --[[ Line: 85 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_1, (ref 4): v_u_4, (ref 5): v_u_13 ]]
                    if v_u_2:is_debug_user() and v_u_7.DebugChatLogging == true then
                        v_u_1:puts("SPChatEventNewImplementationAdapter EVT_Chat_ServerOnMessageFiltered message_table")
                        print(v_u_2:table_to_string(p28))
                    end;
                    local v29 = v_u_4:message_from_table(p28)
                    if not v_u_2:do_disable_chat() or v29:is_speaker_default_userid() == true then
                        v_u_13(v29)
                    end;
                end)
                v_u_20 = true
                p_u_21()
            end)
            p_u_8._evt:fire_event_to_server(v_u_5.EVT_Chat_ClientRequestInitialData)
        end;
        local v_u_30 = 0
        local function _() --[[ Name: allocate_local_message_id ]] --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            local v31 = v_u_30
            v_u_30 = v_u_30 + 1
            return v31;
        end;
        v9.say_message_to_channel = function(_, p_u_32, p33) --[[ Name: say_message_to_channel ]] --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_30, (ref 3): v_u_4, (copy 4): p_u_8, (ref 5): v_u_5, (ref 6): v_u_7, (ref 7): v_u_1 ]]
            local l_format_0 = string.format
            local v34 = v_u_2:get_local_userid()
            local v35 = v_u_30
            v_u_30 = v_u_30 + 1
            local v_u_36 = l_format_0("%d_%d", v34, v35)
            p_u_32:set_message_meta_id(v_u_36)
            local v37 = v_u_4:message_to_table(p_u_32)
            v_u_4:message_from_table(v37)
            p_u_8._evt:fire_event_to_server(v_u_5.EVT_Chat_ClientSendMessage, v37)
            if v_u_7.UseRobloxTextChannel == true then
                if p33 ~= nil then
                    p33:run_if_has_roblox_text_channel(function(p_u_38) --[[ Line: 123 ]]
                        --[[ Upvalues: (copy 1): p_u_32, (copy 2): v_u_36, (ref 3): v_u_2, (ref 4): v_u_1 ]]
                        task.spawn(function() --[[ Line: 124 ]]
                            --[[ Upvalues: (copy 1): p_u_38, (ref 2): p_u_32, (ref 3): v_u_36, (ref 4): v_u_2, (ref 5): v_u_1 ]]
                            local v39 = p_u_38:SendAsync(p_u_32:get_message(), v_u_36)
                            if v_u_2:is_dev_build() then
                                v_u_1:puts("SPChatEventNewImplementationAdapter:say_message_to_channel sent to channel[%s] message(%s) status(%s) res_meta[%s]", p_u_38:GetFullName(), p_u_32:get_message(), tostring(v39.Status), v39.Metadata)
                            end;
                        end)
                    end)
                    return;
                end;
                v_u_1:warnf("SPChatEventNewImplementationAdapter:say_message_to_channel sp_chat_channel nil")
            end;
        end;
        v9:cons()
        return v9;
    end
};
