-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.SPRect)
local v_u_4 = require(game.ReplicatedStorage.SPChat.Local.SPChatWindowTopBar)
local v_u_5 = require(game.ReplicatedStorage.SPChat.Local.SPChatWindow)
local v_u_6 = require(game.ReplicatedStorage.SPChat.Local.SPChatMessageLogDisplayAdapter)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.SPChat.Shared.SPChatChannel)
local v_u_8 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_9 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_13 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_15 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local s_TextChatService_0 = game:GetService("TextChatService")
local v_u_16 = require(game.ReplicatedStorage.SPChat.Local.SPChatEventNewImplementationAdapter)
return {
    ["new"] = function(_, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_12, (copy 3): v_u_15, (copy 4): v_u_14, (copy 5): v_u_16, (copy 6): v_u_1, (copy 7): v_u_3, (copy 8): v_u_9, (copy 9): v_u_11, (copy 10): s_TextChatService_0, (copy 11): v_u_4, (copy 12): v_u_5, (copy 13): v_u_6, (copy 14): v_u_13, (copy 15): v_u_8, (copy 16): v_u_2, (copy 17): v_u_10 ]]
        local v_u_21 = {
            ["get_anim_update_fn"] = function(p_u_19) --[[ Name: get_anim_update_fn ]] --[[ Line: 467 ]]
                return function(p20) --[[ Line: 468 ]]
                    --[[ Upvalues: (copy 1): p_u_19 ]]
                    p_u_19:update(p20)
                end;
            end
        }
        local v_u_22 = nil
        v_u_21.is_init = function(_) --[[ Name: is_init ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            if v_u_22 == nil then
                return false;
            else
                return v_u_22:is_init();
            end;
        end;
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = v_u_7:new()
        local function f_get_available_dance_id_list() --[[ Name: get_available_dance_id_list ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_17, (ref 3): v_u_15, (ref 4): v_u_14 ]]
            local v27 = v_u_12:new()
            local v28 = p_u_17._player_blob_manager:get_player_blob()
            if v28 then
                local v29 = v_u_15:get_owned_danceid_to_equipped_dict(v28)
                for v30, _ in v_u_14:singleton():key_itr() do
                    if v29:contains(v30) and v29:get(v30) == true then
                        v27:push_back(v30)
                    end;
                end;
            end;
            return v27;
        end;
        local v_u_31 = v_u_7:new()
        local v_u_32 = v_u_7:new()
        local v_u_33 = v_u_12:new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_16, (copy 3): p_u_17, (copy 4): v_u_21, (ref 5): v_u_1, (ref 6): v_u_3, (ref 7): v_u_9, (copy 8): p_u_18, (ref 9): v_u_11, (copy 10): v_u_31, (copy 11): v_u_32, (copy 12): v_u_33, (ref 13): s_TextChatService_0, (ref 14): v_u_23, (ref 15): v_u_4, (ref 16): v_u_24, (ref 17): v_u_5, (ref 18): v_u_25, (ref 19): v_u_6, (copy 20): f_get_available_dance_id_list, (ref 21): v_u_7, (ref 22): v_u_14, (ref 23): v_u_12 ]]
            v_u_22 = v_u_16:new(p_u_17)
            v_u_22:set_on_add_channel_fn(function(p34) --[[ Line: 65 ]]
                --[[ Upvalues: (ref 1): v_u_21 ]]
                v_u_21:add_channel(p34)
            end)
            v_u_22:set_on_remove_channel_fn(function(p35) --[[ Line: 68 ]]
                --[[ Upvalues: (ref 1): v_u_21 ]]
                v_u_21:remove_channel(p35)
            end)
            v_u_22:set_on_new_message_fn(function(p36) --[[ Line: 72 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_3, (ref 4): v_u_9, (ref 5): p_u_18 ]]
                local v37 = v_u_21:get_channel(p36:get_channelid())
                if v37 == nil then
                    return v_u_1:warnf("_chat_events:on_new_message_fn channel(%s) does not exist [%s]", tostring(p36:get_channelid()), v_u_3:table_to_string(v_u_9:message_to_table(p36)));
                end;
                v37:add_message_to_channel(p36)
                p_u_18:OnNewMessage(v_u_9:message_to_legacy_table(p36), p36:get_channel_name())
            end)
            if v_u_11.UseRobloxTextChannel == true then
                local function f_resolve_meta_message_id(p_u_38, p39) --[[ Name: resolve_meta_message_id ]] --[[ Line: 83 ]]
                    --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_21, (ref 5): v_u_1, (ref 6): p_u_18, (ref 7): v_u_9 ]]
                    v_u_31:remove(p_u_38)
                    v_u_32:remove(p_u_38)
                    v_u_33:remove_if(function(p40) --[[ Line: 86 ]]
                        --[[ Upvalues: (copy 1): p_u_38 ]]
                        return p40 == p_u_38;
                    end)
                    local v41 = v_u_21:get_channel(p39:get_channelid())
                    if v41 == nil then
                        return v_u_1:warnf("_chat_events:set_on_message_done_filtering_fn channel(%s) does not exist", (tostring(p39:get_channelid())));
                    end;
                    v41:update_message_filtered(p39)
                    p_u_18:OnMessageDoneFiltering(v_u_9:message_to_legacy_table(p39), p39:get_channel_name())
                end;
                local function _(p42) --[[ Name: add_pending_meta_message_id_lru ]] --[[ Line: 96 ]]
                    --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_31, (ref 3): v_u_32 ]]
                    v_u_33:push_back(p42)
                    if v_u_33:count() > 100 then
                        local v43 = v_u_33:pop_front()
                        v_u_31:remove(v43)
                        v_u_32:remove(v43)
                    end;
                end;
                s_TextChatService_0.MessageReceived:Connect(function(p44) --[[ Line: 111 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_32, (copy 4): f_resolve_meta_message_id, (ref 5): v_u_31, (ref 6): v_u_33 ]]
                    local l_Text_0 = p44.Text
                    local l_Metadata_0 = p44.Metadata
                    if #l_Metadata_0 == 0 then
                        v_u_1:puts("resolve meta_message_id len-0 TextChatService.MessageReceived")
                        return;
                    else
                        if v_u_3:is_dev_build() then
                            v_u_1:puts("SPChatWindowAdapter TextChatService.MessageReceived[%s] Meta(%s) Text(%s)", tostring(p44.Status), l_Metadata_0, l_Text_0)
                        end;
                        if v_u_32:contains(l_Metadata_0) then
                            local v45 = v_u_32:get(l_Metadata_0)
                            v45:set_message(l_Text_0)
                            f_resolve_meta_message_id(l_Metadata_0, v45)
                        else
                            v_u_31:add(l_Metadata_0, l_Text_0)
                            v_u_33:push_back(l_Metadata_0)
                            if v_u_33:count() > 100 then
                                local v46 = v_u_33:pop_front()
                                v_u_31:remove(v46)
                                v_u_32:remove(v46)
                            end;
                        end;
                    end;
                end)
                v_u_22:set_on_message_done_filtering_fn(function(p47) --[[ Line: 134 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_resolve_meta_message_id, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_33 ]]
                    local v48 = p47:get_message_meta_id()
                    if #v48 == 0 then
                        v_u_1:puts("resolve meta_message_id len-0 set_on_message_done_filtering_fn")
                        f_resolve_meta_message_id(v48, p47)
                        return;
                    elseif v_u_31:contains(p47:get_message_meta_id()) then
                        p47:set_message((v_u_31:get(v48)))
                        f_resolve_meta_message_id(v48, p47)
                    else
                        v_u_32:add(v48, p47)
                        v_u_33:push_back(v48)
                        if v_u_33:count() > 100 then
                            local v49 = v_u_33:pop_front()
                            v_u_31:remove(v49)
                            v_u_32:remove(v49)
                        end;
                    end;
                end)
            else
                v_u_22:set_on_message_done_filtering_fn(function(p50) --[[ Line: 154 ]]
                    --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): p_u_18, (ref 4): v_u_9 ]]
                    local v51 = v_u_21:get_channel(p50:get_channelid())
                    if v51 == nil then
                        return v_u_1:warnf("_chat_events:set_on_message_done_filtering_fn channel(%s) does not exist", (tostring(p50:get_channelid())));
                    end;
                    v51:update_message_filtered(p50)
                    p_u_18:OnMessageDoneFiltering(v_u_9:message_to_legacy_table(p50), p50:get_channel_name())
                end)
            end;
            v_u_23 = v_u_4:new(p_u_17, v_u_21)
            v_u_24 = v_u_5:new(p_u_17, v_u_21, v_u_23)
            v_u_23:post_create()
            v_u_25 = v_u_6:new(p_u_17, 2)
            v_u_25:SetParentManual(v_u_24:get_message_display_frame())
            v_u_24:set_on_layout_changed_fn(function() --[[ Line: 170 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                v_u_25:relayout()
            end)
            v_u_24:register_on_text_sent_fn(function(p52) --[[ Line: 174 ]]
                --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_21, (ref 3): v_u_9 ]]
                v_u_24:get_input_bar():clear()
                v_u_21:send_message(v_u_9:new(p52):set_channelid(v_u_21:get_chat_window_selected_channel_id()))
            end)
            v_u_24:register_on_text_changed_fn(function(p53) --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): f_get_available_dance_id_list, (ref 3): v_u_7, (ref 4): v_u_14, (ref 5): v_u_12, (ref 6): v_u_24 ]]
                if #p53 >= 6 then
                    local v54 = string.lower(p53)
                    if v54:match("^/e ") then
                        local v55 = v_u_3:str_split(v54, " ")
                        if #v55 >= 2 then
                            local v56 = v_u_3:string_join(v55, " ", 2)
                            if #v56 >= 4 then
                                local v57 = f_get_available_dance_id_list()
                                local v58 = v_u_7:new()
                                for _, v59 in v57:key_itr() do
                                    v58:add(string.lower(v_u_14:singleton():get_dance_info_for_id(v59):get_name()), v59)
                                end;
                                local v60 = v_u_12:new()
                                for v61, v62 in v58:key_itr() do
                                    if v61:match("^" .. v56) then
                                        v60:push_back(v62)
                                    end;
                                end;
                                if v60:count() == 1 then
                                    local v63 = v_u_14:singleton():get_dance_info_for_id(v60:get(1))
                                    if v63 then
                                        v_u_24:get_input_bar():set_text_and_move_cursor_to_end("/e " .. v63:get_name())
                                    end;
                                end;
                            end;
                        end;
                    end;
                    if v54:match("^/w ") then
                        local v64 = v_u_3:str_split(v54, " ")
                        if #v64 == 2 then
                            local v65 = v64[2]
                            if #v65 >= 4 then
                                local v66 = v_u_3:get_lowercase_name_to_player()
                                local v67 = v_u_12:new()
                                for v68, v69 in v66:key_itr() do
                                    if v69 ~= v_u_3:get_local_player() and v68:match("^" .. v65) then
                                        v67:push_back(v69)
                                    end;
                                end;
                                if v67:count() == 1 then
                                    v_u_24:get_input_bar():set_text_and_move_cursor_to_end("/w " .. v67:get(1).Name .. " ")
                                end;
                            end;
                        end;
                    end;
                end;
            end)
            v_u_22:on_init(function() --[[ Line: 239 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22, (ref 3): v_u_25, (ref 4): v_u_24 ]]
                v_u_21:get_channel(v_u_22:get_server_chat_channel_id()):register_message_log_display(v_u_25, true)
                v_u_21:get_channel(v_u_22:get_server_system_channel_id()):register_message_log_display(v_u_25, true)
                v_u_24:update_current_channel_display()
            end)
        end;
        local function f_send_error_message(p70) --[[ Name: send_error_message ]] --[[ Line: 246 ]]
            --[[ Upvalues: (copy 1): v_u_21, (ref 2): v_u_22, (ref 3): v_u_9, (ref 4): v_u_3 ]]
            v_u_21:get_channel(v_u_22:get_server_chat_channel_id()):add_message_to_channel(v_u_9:new(p70):set_icon(v_u_3:important_assetid()))
        end;
        local v_u_71 = v_u_7:new()
        v_u_21.send_message = function(p72, p_u_73) --[[ Name: send_message ]] --[[ Line: 256 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): f_get_available_dance_id_list, (ref 3): v_u_7, (ref 4): v_u_14, (copy 5): v_u_71, (copy 6): v_u_21, (ref 7): v_u_22, (ref 8): v_u_9, (copy 9): p_u_17, (ref 10): v_u_13, (ref 11): v_u_8, (copy 12): f_send_error_message ]]
            if #p_u_73:get_message() >= 2 then
                local v74 = string.lower(p_u_73:get_message())
                if v74:match("^/e") then
                    local v75 = v_u_3:str_split(v74, " ")
                    local v76 = f_get_available_dance_id_list()
                    local v77
                    if #v75 == 1 then
                        v77 = v76:random()
                    else
                        local v78 = v_u_7:new()
                        for _, v79 in v76:key_itr() do
                            v78:add(string.lower(v_u_14:singleton():get_dance_info_for_id(v79):get_name()), v79)
                        end;
                        local v80 = v_u_3:string_join(v75, " ", 2)
                        if v78:contains(v80) then
                            v77 = v78:get(v80)
                        elseif v80 == "dance" then
                            v77 = v76:random()
                        else
                            if v_u_71:contains(v80) == false then
                                if v80:match("^dance") == nil then
                                    v_u_21:get_channel(v_u_22:get_server_chat_channel_id()):add_message_to_channel(v_u_9:new((string.format("Dance \"%s\" not found!", v80))):set_icon(v_u_3:important_assetid()))
                                end;
                                v_u_71:add(v80, v76:random())
                            end;
                            v77 = v_u_71:get(v80)
                        end;
                    end;
                    if v_u_14:singleton():contains_dance_for_id(v77) and p_u_17._lobby_join:get_lobby() then
                        p_u_17._lobby_join:get_lobby():character_perform_danceid(v77)
                        p72:get_channel(v_u_22:get_server_chat_channel_id()):add_message_to_channel(v_u_9:new(string.format("Dancing \"%s\"!", v_u_14:singleton():get_dance_name_for_id(v77))):set_icon(v_u_14:singleton():get_dance_icon_for_id(v77)))
                    end;
                    return;
                end;
                if v74:match("^/w") then
                    local v81 = v_u_3:str_split(v74, " ")
                    if #v81 >= 2 then
                        local function f_send_custom_channel_message_removing_first_n_tokens(p82) --[[ Name: send_custom_channel_message_removing_first_n_tokens ]] --[[ Line: 311 ]]
                            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_73, (ref 3): p_u_17, (ref 4): v_u_22 ]]
                            local v83 = v_u_3:str_split(p_u_73:get_message(), " ")
                            for _ = 1, p82 do
                                table.remove(v83, 1)
                            end;
                            local v84 = ""
                            for v85 = 1, #v83 do
                                v84 = v84 .. v83[v85]
                                if v85 ~= #v83 then
                                    v84 = v84 .. " "
                                end;
                            end;
                            if #v84 > 0 then
                                p_u_73:set_message(v84)
                                p_u_73:set_channelid(p_u_17._chat:get_custom_channel_id())
                                v_u_22:say_message_to_channel(p_u_73, p_u_17._chat:get_custom_channel())
                            end;
                        end;
                        local function f_on_validate_has_custom_channel(p_u_86) --[[ Name: on_validate_has_custom_channel ]] --[[ Line: 331 ]]
                            --[[ Upvalues: (ref 1): p_u_17 ]]
                            if p_u_17._chat:can_request_custom_channel() then
                                p_u_17._chat:request_custom_channel(function() --[[ Line: 333 ]]
                                    --[[ Upvalues: (copy 1): p_u_86 ]]
                                    p_u_86()
                                end)
                            else
                                p_u_86()
                            end;
                        end;
                        local v87 = v_u_3:get_lowercase_name_to_player()
                        local v88 = v81[2]
                        if v87:contains(v88) ~= true then
                            return f_on_validate_has_custom_channel(function() --[[ Line: 345 ]]
                                --[[ Upvalues: (copy 1): f_send_custom_channel_message_removing_first_n_tokens ]]
                                f_send_custom_channel_message_removing_first_n_tokens(1)
                            end);
                        end;
                        local v_u_89 = v87:get(v88)
                        return f_on_validate_has_custom_channel(function() --[[ Line: 350 ]]
                            --[[ Upvalues: (ref 1): p_u_17, (copy 2): v_u_89, (ref 3): v_u_13, (copy 4): f_send_custom_channel_message_removing_first_n_tokens ]]
                            p_u_17._chat:query_is_playerid_in_custom_channel(v_u_89.UserId, function(p90) --[[ Line: 351 ]]
                                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_13, (ref 3): v_u_89, (ref 4): f_send_custom_channel_message_removing_first_n_tokens ]]
                                if p90 ~= true then
                                    p_u_17._evt:fire_event_to_server(v_u_13.EVT_Chat_SendPlayerCustomChannelInvite, v_u_89.UserId)
                                end;
                                f_send_custom_channel_message_removing_first_n_tokens(2)
                            end)
                        end);
                    end;
                    return;
                end;
            end;
            if #p_u_73:get_message() > v_u_8:get_chat_string_param_sanity_max_length() then
                return f_send_error_message("Your message exceeds the maximum allowed length!");
            end;
            v_u_22:say_message_to_channel(p_u_73, (p72:get_channel(p_u_73:get_channelid())))
        end;
        local function f_get_selectable_channels_list() --[[ Name: get_selectable_channels_list ]] --[[ Line: 375 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_26 ]]
            local v91 = v_u_12:new()
            for v92, v93 in v_u_26:key_itr() do
                if v93:get_players_can_message() then
                    v91:push_back(v92)
                end;
            end;
            v91:sort(function(p94, p95) --[[ Line: 382 ]]
                return p95 - p94;
            end)
            return v91;
        end;
        local v_u_96 = 1
        local v_u_97 = nil
        v_u_21.clear_chat_window_selected_channel_cache = function(_) --[[ Name: clear_chat_window_selected_channel_cache ]] --[[ Line: 390 ]]
            --[[ Upvalues: (ref 1): v_u_97 ]]
            v_u_97 = nil
        end;
        v_u_21.get_chat_window_selected_channel_id = function(_) --[[ Name: get_chat_window_selected_channel_id ]] --[[ Line: 391 ]]
            --[[ Upvalues: (ref 1): v_u_97, (copy 2): f_get_selectable_channels_list, (ref 3): v_u_96 ]]
            if v_u_97 == nil then
                local v98 = f_get_selectable_channels_list()
                if v_u_96 > v98:count() then
                    v_u_96 = 1
                end;
                v_u_97 = v98:get(v_u_96)
            end;
            return v_u_97;
        end;
        v_u_21.cycle_chat_window_selected_channel_id = function(p99) --[[ Name: cycle_chat_window_selected_channel_id ]] --[[ Line: 400 ]]
            --[[ Upvalues: (ref 1): v_u_96 ]]
            p99:clear_chat_window_selected_channel_cache()
            v_u_96 = v_u_96 + 1
            p99:get_chat_window_selected_channel_id()
        end;
        local v_u_100 = v_u_7:new()
        v_u_21.set_id_to_channel_visible = function(_, p101, p102) --[[ Name: set_id_to_channel_visible ]] --[[ Line: 408 ]]
            --[[ Upvalues: (copy 1): v_u_100, (copy 2): v_u_26, (ref 3): v_u_1, (ref 4): v_u_25 ]]
            if v_u_100:get(p101) == p102 then
                return;
            elseif v_u_26:contains(p101) == true then
                v_u_100:add(p101, p102)
                local v103 = v_u_26:get(p101)
                if p102 then
                    v103:register_message_log_display(v_u_25, true)
                    v_u_25:sort_all_messages_by_time()
                else
                    v103:unregister_message_log_display(v_u_25)
                    v_u_25:remove_messages_from_channel(v103)
                end;
            else
                return v_u_1:warnf("SPChatWindowAdapter:set_id_to_channel_visible does not contain channel(%d)", p101);
            end;
        end;
        v_u_21.get_id_to_channel_visible = function(_, p104) --[[ Name: get_id_to_channel_visible ]] --[[ Line: 422 ]]
            --[[ Upvalues: (copy 1): v_u_100 ]]
            return v_u_100:get(p104);
        end;
        v_u_21.channels_itr = function(_) --[[ Name: channels_itr ]] --[[ Line: 426 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            return v_u_26:key_itr();
        end;
        v_u_21.get_channel = function(_, p105) --[[ Name: get_channel ]] --[[ Line: 428 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_26 ]]
            v_u_2:is_int(p105)
            return v_u_26:get(p105);
        end;
        v_u_21.get_channel_count = function(_) --[[ Name: get_channel_count ]] --[[ Line: 433 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            return v_u_26:count();
        end;
        v_u_21.get_channel_by_name = function(_, p106) --[[ Name: get_channel_by_name ]] --[[ Line: 435 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            for _, v107 in v_u_26:key_itr() do
                if v107:get_name() == p106 then
                    return v107;
                end;
            end;
            return nil;
        end;
        v_u_21.add_channel = function(_, p108) --[[ Name: add_channel ]] --[[ Line: 444 ]]
            --[[ Upvalues: (copy 1): v_u_26, (copy 2): v_u_100 ]]
            local v109 = p108:get_channelid()
            if v_u_26:contains(v109) ~= true then
                v_u_26:add(v109, p108)
                v_u_100:add(v109, true)
            end;
            return v_u_26:get(v109);
        end;
        v_u_21.remove_channel = function(p110, p111) --[[ Name: remove_channel ]] --[[ Line: 453 ]]
            --[[ Upvalues: (copy 1): v_u_26, (copy 2): v_u_100, (ref 3): v_u_24 ]]
            if v_u_26:contains(p111) then
                v_u_26:get(p111):on_removed()
            end;
            v_u_26:remove(p111)
            v_u_100:remove(p111)
            p110:clear_chat_window_selected_channel_cache()
            v_u_24:update_current_channel_display()
        end;
        v_u_21.get_system_channel = function(p112) --[[ Name: get_system_channel ]] --[[ Line: 463 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return p112:get_channel(v_u_22:get_server_system_channel_id());
        end;
        v_u_21.set_visible = function(_, p113) --[[ Name: set_visible ]] --[[ Line: 471 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if v_u_24 then
                v_u_24:set_visible(p113)
            end;
        end;
        v_u_21.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 477 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if v_u_24 then
                return v_u_24:get_visible();
            else
                return false;
            end;
        end;
        v_u_21.get_do_focus_fn = function(p_u_114) --[[ Name: get_do_focus_fn ]] --[[ Line: 485 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            return function() --[[ Line: 486 ]]
                --[[ Upvalues: (copy 1): p_u_114, (ref 2): v_u_24 ]]
                if p_u_114:get_visible() ~= true then
                    p_u_114:set_visible(true)
                end;
                v_u_24:get_input_bar():capture_focus()
            end;
        end;
        v_u_21.get_message_log_display = function(_) --[[ Name: get_message_log_display ]] --[[ Line: 494 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            return v_u_25;
        end;
        v_u_21.get_chat_window = function(_) --[[ Name: get_chat_window ]] --[[ Line: 498 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            return v_u_24;
        end;
        v_u_21.get_chat_events = function(_) --[[ Name: get_chat_events ]] --[[ Line: 499 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v_u_21.update = function(p115, p116) --[[ Name: update ]] --[[ Line: 501 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_24, (ref 3): v_u_23, (ref 4): v_u_25 ]]
            v_u_22:update(p116)
            v_u_24:update(p116)
            v_u_23:update(p116)
            v_u_25:update(p116)
            p115:update_fadeout(p116)
        end;
        local v_u_117 = 0.5
        v_u_21.update_fadeout = function(_, p118) --[[ Name: update_fadeout ]] --[[ Line: 510 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_3, (ref 3): v_u_117, (ref 4): v_u_10, (ref 5): v_u_25 ]]
            local v119 = 1
            if v_u_24:get_input_bar():is_focused() or v_u_24:get_base_frame_nrect():contains_vec2((v_u_3:get_cursor_nxy())) == true then
                v_u_117 = 0
            else
                v_u_117 = v_u_117 + v_u_10:TimescaleToDeltaTime(p118)
                v119 = v_u_117 > 0.5 and 0 or v119
            end;
            local v120 = v_u_10:expt_sec(v_u_24:get_alpha(), v119, 0.25, p118)
            v_u_24:set_alpha(v120)
            v_u_25:get_spchat_message_display():get_scrolling_frame().ScrollBarImageTransparency = v_u_3:tra(v120)
        end;
        f_cons()
        return v_u_21;
    end
};
