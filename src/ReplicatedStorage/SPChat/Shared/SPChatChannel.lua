-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:54 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.AssertType)
local v_u_1 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_56 = {
    ["new"] = function(_, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_7, (copy 5): v_u_4, (copy 6): v_u_3, (copy 7): v_u_1 ]]
        local v13 = {
            ["Name"] = p_u_9,
            ["RegisterMessageLogDisplay"] = function(p10, p11, p12) --[[ Name: RegisterMessageLogDisplay ]] --[[ Line: 77 ]]
                p10:register_message_log_display(p11, p12)
            end,
            ["UnregisterMessageLogDisplay"] = function(_, _) end
        }
        v13.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 16 ]]
            --[[ Upvalues: (copy 1): p_u_9 ]]
            return p_u_9;
        end;
        v13.get_channelid = function(_) --[[ Name: get_channelid ]] --[[ Line: 17 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8;
        end;
        local v_u_14 = Color3.new(1, 1, 1)
        v13.set_color = function(p15, p16) --[[ Name: set_color ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            v_u_14 = p16
            return p15;
        end;
        v13.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        local v_u_17 = true
        v13.get_players_can_message = function(_) --[[ Name: get_players_can_message ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        v13.set_players_can_message = function(p18, p19) --[[ Name: set_players_can_message ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = p19
            return p18;
        end;
        local v_u_20 = false
        v13.is_default_channel = function(_) --[[ Name: is_default_channel ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        v13.set_default_channel = function(p21, p22) --[[ Name: set_default_channel ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            v_u_20 = p22
            return p21;
        end;
        local v_u_23 = false
        local v_u_24 = ""
        v13.set_broadcast_channel = function(_, p25, p26) --[[ Name: set_broadcast_channel ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
            v_u_23 = p25
            v_u_24 = p26
        end;
        v13.is_broadcast_channel = function(_) --[[ Name: is_broadcast_channel ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v13.get_broadcast_topic = function(_) --[[ Name: get_broadcast_topic ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            return v_u_24;
        end;
        local v_u_27 = v_u_6:new()
        v13.add_member = function(_, p28) --[[ Name: add_member ]] --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): v_u_27 ]]
            v_u_27:add(p28, true)
        end;
        v13.remove_member = function(_, p29) --[[ Name: remove_member ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): v_u_27 ]]
            v_u_27:remove(p29)
        end;
        v13.get_members = function(_) --[[ Name: get_members ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_27 ]]
            return v_u_27;
        end;
        local v_u_30 = v_u_2:new()
        v13.get_messages = function(_) --[[ Name: get_messages ]] --[[ Line: 54 ]]
            --[[ Upvalues: (copy 1): v_u_30 ]]
            return v_u_30;
        end;
        local v_u_31 = v_u_5:get_channel_message_history_count()
        local v_u_32 = nil
        v13.set_roblox_text_channel = function(p33, p34) --[[ Name: set_roblox_text_channel ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32 = p34
            return p33;
        end;
        v13.get_roblox_text_channel = function(_) --[[ Name: get_roblox_text_channel ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            return v_u_32;
        end;
        v13.run_if_has_roblox_text_channel = function(_, p35) --[[ Name: run_if_has_roblox_text_channel ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_3 ]]
            if v_u_32 then
                p35(v_u_32)
            elseif v_u_7.UseRobloxTextChannel == true and v_u_4:is_dev_build() then
                v_u_3:warnf("SPChatChannel:run_if_has_roblox_text_channel no roblox text channel")
            end;
        end;
        local v_u_36 = v_u_2:new()
        v13.register_message_log_display = function(_, p37, p38) --[[ Name: register_message_log_display ]] --[[ Line: 78 ]]
            --[[ Upvalues: (copy 1): v_u_36, (ref 2): v_u_3, (copy 3): v_u_30 ]]
            for v39 = 1, v_u_36:count() do
                if v_u_36:get(v39) == p37 then
                    v_u_3:warnf("SPChatChannel:RegisterMessageLogDisplay message log display already registered")
                    return;
                end;
            end;
            v_u_36:push_back(p37)
            if p38 == true then
                for v40 = 1, v_u_30:count() do
                    p37:add_message(v_u_30:get(v40))
                end;
            end;
        end;
        v13.unregister_message_log_display = function(_, p_u_41) --[[ Name: unregister_message_log_display ]] --[[ Line: 96 ]]
            --[[ Upvalues: (copy 1): v_u_36 ]]
            v_u_36:remove_if(function(p42) --[[ Line: 97 ]]
                --[[ Upvalues: (copy 1): p_u_41 ]]
                return p42 == p_u_41;
            end)
        end;
        v13.add_message_to_channel = function(_, p43) --[[ Name: add_message_to_channel ]] --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): v_u_30, (copy 2): v_u_31, (copy 3): v_u_36 ]]
            if v_u_31 <= v_u_30:count() then
                v_u_30:pop_front()
            end;
            v_u_30:push_back(p43)
            for v44 = 1, v_u_36:count() do
                v_u_36:get(v44):add_message(p43)
            end;
        end;
        v13.update_message_filtered = function(_, p45) --[[ Name: update_message_filtered ]] --[[ Line: 113 ]]
            --[[ Upvalues: (copy 1): v_u_30, (ref 2): v_u_3, (copy 3): v_u_36 ]]
            local v46 = false
            for v47 = 1, v_u_30:count() do
                local v48 = v_u_30:get(v47)
                if v48:get_message_id() == p45:get_message_id() and v48:get_channelid() == p45:get_channelid() then
                    v48:set_message(p45:get_message())
                    v46 = true
                    break;
                end;
            end;
            if v46 == false then
                v_u_3:warnf("SPChatChannel:update_message_filtered id(%s) message was not found", (tostring(p45:get_message_id())))
            end;
            for v49 = 1, v_u_36:count() do
                v_u_36:get(v49):update_message_filtered(p45)
            end;
        end;
        v13.to_table = function(p50) --[[ Name: to_table ]] --[[ Line: 132 ]]
            --[[ Upvalues: (copy 1): p_u_8, (copy 2): p_u_9, (ref 3): v_u_14, (ref 4): v_u_17, (copy 5): v_u_30, (ref 6): v_u_1 ]]
            local v51 = {
                ["ChannelID"] = p_u_8,
                ["Name"] = p_u_9,
                ["Color"] = v_u_14,
                ["PlayersCanMessage"] = v_u_17,
                ["Messages"] = {},
                ["RobloxChatChannel"] = p50:get_roblox_text_channel()
            }
            for v52 = 1, v_u_30:count() do
                v51.Messages[#v51.Messages + 1] = v_u_1:message_to_table(v_u_30:get(v52))
            end;
            return v51;
        end;
        v13.debug_string = function(_) --[[ Name: debug_string ]] --[[ Line: 147 ]]
            --[[ Upvalues: (copy 1): p_u_9, (copy 2): p_u_8, (copy 3): v_u_30 ]]
            return string.format("{Name(%s) ChannelID(%d) Messages[%d]}", p_u_9, p_u_8, v_u_30:count());
        end;
        local v_u_53 = v_u_2:new()
        v13.add_on_removed_fn = function(_, p54) --[[ Name: add_on_removed_fn ]] --[[ Line: 152 ]]
            --[[ Upvalues: (copy 1): v_u_53 ]]
            v_u_53:push_back(p54)
        end;
        v13.on_removed = function(_) --[[ Name: on_removed ]] --[[ Line: 156 ]]
            --[[ Upvalues: (copy 1): v_u_53 ]]
            for _, v55 in v_u_53:key_itr() do
                v55()
            end;
            v_u_53:clear()
        end;
        return v13;
    end
}
v_u_56.from_table = function(_, p57) --[[ Name: from_table ]] --[[ Line: 166 ]]
    --[[ Upvalues: (copy 1): v_u_56, (copy 2): v_u_1 ]]
    local v58 = v_u_56:new(p57.ChannelID, p57.Name)
    v58:set_color(p57.Color)
    v58:set_players_can_message(p57.PlayersCanMessage)
    v58:set_roblox_text_channel(p57.RobloxChatChannel)
    local v59 = v58:get_messages()
    for v60 = 1, #p57.Messages do
        v59:push_back(v_u_1:message_from_table(p57.Messages[v60]))
    end;
    return v58;
end;
return v_u_56;
