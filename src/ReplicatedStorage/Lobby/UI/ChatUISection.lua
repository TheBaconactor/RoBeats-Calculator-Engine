-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:49 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
local v_u_3 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["new"] = function(_, p_u_5, p_u_6, p_u_7, p_u_8, p_u_9, p10) --[[ Name: new ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_1 ]]
        local v11 = {}
        local v_u_12 = p10 == nil and 20 or p10
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        v11.cons = function(_) --[[ Name: cons ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_9, (ref 3): v_u_14, (ref 4): v_u_2, (copy 5): p_u_5, (copy 6): p_u_7, (copy 7): p_u_6, (ref 8): v_u_3 ]]
            if v_u_4:do_disable_chat() then
                p_u_9.Parent = nil
            else
                v_u_14 = v_u_2:new(p_u_5, p_u_9.ScrollingFrame.TextLabel, p_u_9.ScrollingFrame, p_u_7, p_u_6):set_empty_message(string.format("Click here or press \'%s\' to chat", p_u_5._input:get_key_display_str(v_u_3.KEY_MENU_MATCHMAKING_CHAT_FOCUS)))
            end;
        end;
        v11.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13, (copy 3): p_u_5, (ref 4): v_u_16, (ref 5): v_u_15 ]]
            if v_u_14 then
                v_u_14:cleanup()
            end;
            if v_u_13 ~= nil then
                local v17 = p_u_5._chat:get_game_instance_channel()
                if v17 ~= nil then
                    v17:UnregisterMessageLogDisplay(v_u_13)
                end;
                p_u_5._chat:cleanup_message_log_display(v_u_13)
                v_u_13 = nil
                v_u_16 = nil
            end;
            v_u_15 = nil
        end;
        v11.behaviour_update = function(_, p18) --[[ Name: behaviour_update ]] --[[ Line: 55 ]]
            --[[ Upvalues: (copy 1): p_u_5, (ref 2): v_u_13, (ref 3): v_u_12, (copy 4): p_u_8, (ref 5): v_u_4, (ref 6): v_u_16, (copy 7): p_u_7, (ref 8): v_u_1, (ref 9): v_u_15, (ref 10): v_u_14, (ref 11): v_u_3 ]]
            local v19 = p_u_5._chat:get_game_instance_channel()
            if v_u_13 == nil then
                if v19 == nil then
                    return;
                end;
                v_u_13 = p_u_5._chat:make_message_log_display(v_u_12)
                v_u_13:SetParentManual(p_u_8)
                local v20, v21 = v_u_4:try(function() --[[ Line: 62 ]]
                    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_13, (ref 3): p_u_7 ]]
                    v_u_16 = v_u_13:get_spchat_message_display()
                    v_u_16:set_spuiobj_parent(p_u_7)
                end)
                if v20 ~= true then
                    v_u_1:warnf("ChatUISection get_spchat_message_display fail (%s)[%s]", v21.Error, v21.StackTrace)
                end;
                v19:RegisterMessageLogDisplay(v_u_13, true)
                p_u_5._chat:get_system_channel():RegisterMessageLogDisplay(v_u_13)
                v_u_15 = v19:get_channelid()
            end;
            if v_u_13 and (v19 ~= nil and v_u_15 ~= v19:get_channelid()) then
                if v_u_15 ~= nil then
                    local v22 = p_u_5._chat:get_channel_by_id(v_u_15)
                    if v22 ~= nil then
                        v22:UnregisterMessageLogDisplay(v_u_13)
                    end;
                end;
                v_u_15 = v19:get_channelid()
                v19:RegisterMessageLogDisplay(v_u_13, true)
            end;
            if v_u_14 then
                if p_u_5._input:control_just_pressed(v_u_3.KEY_MENU_MATCHMAKING_CHAT_FOCUS) then
                    v_u_14:do_focus()
                end;
                if v_u_16 ~= nil then
                    v_u_16:update(p18)
                end;
                v_u_14:update(p18)
                local v23, v24 = v_u_14:get_raise_text_sent()
                if v23 == true then
                    p_u_5._chat:post_message_to_gameinstance(v24)
                end;
            end;
        end;
        v11:cons()
        return v11;
    end
};
