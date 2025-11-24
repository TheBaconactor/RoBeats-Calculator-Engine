-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:52 PM
-- Cached decompilation

require(game.ReplicatedStorage.SPChat.Shared.SPChatMessageType)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_3 = require(game.ReplicatedStorage.SPChat.Local.SPChatMessageDisplay)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
return {
    ["new"] = function(_, p_u_4, p_u_5) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v6 = {}
        v_u_1:new()
        local v_u_7 = nil
        v6.get_spchat_message_display = function(_) --[[ Name: get_spchat_message_display ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        v6.cons = function(p8) --[[ Name: cons ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_3, (copy 3): p_u_4, (copy 4): p_u_5 ]]
            v_u_7 = v_u_3:new(p_u_4, p_u_5)
            p8.GuiObject = v_u_7:get_base_frame()
            p8.Scroller = v_u_7:get_scrolling_frame()
        end;
        v6.relayout = function(_) --[[ Name: relayout ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7 ]]
            v_u_2:profilebegin("SPChatMessageLogDisplayAdapter:relayout")
            v_u_7:relayout_starting_at_element_index(1)
            v_u_2:profileend()
        end;
        v6.SetParentManual = function(_, p9) --[[ Name: SetParentManual ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:set_base_frame_parent(p9)
        end;
        v6.add_message = function(_, p10) --[[ Name: add_message ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7 ]]
            v_u_2:profilebegin("SPChatMessageLogDisplayAdapter:AddMessage")
            local v11 = v_u_7:add_message(p10)
            v11:set_id(p10:get_message_id())
            v11:set_name_button_color(p10:get_name_color())
            v11:set_channel_button_color(p10:get_channel_color())
            v_u_2:profileend()
        end;
        v6.update_message_filtered = function(_, p12) --[[ Name: update_message_filtered ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7 ]]
            v_u_2:profilebegin("SPChatMessageLogDisplayAdapter:UpdateMessageFiltered")
            local v13 = v_u_7:get_message_display_elements()
            local v14 = false
            local v15 = 1
            for v16 = 1, v13:count() do
                local v17 = v13:get(v16)
                if v17:get_id() == p12:get_message_id() then
                    v17:set_message_text(p12:get_message())
                    v14 = v17:update_text()
                    v15 = v16
                    break;
                end;
            end;
            if v14 == true then
                v_u_7:relayout_starting_at_element_index(v15)
            end;
            v_u_2:profileend()
        end;
        v6.remove_messages_from_channel = function(_, p_u_18) --[[ Name: remove_messages_from_channel ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:get_message_display_elements():remove_if(function(p19) --[[ Line: 68 ]]
                --[[ Upvalues: (copy 1): p_u_18 ]]
                local v20 = p19:get_message_data():get_channelid() == p_u_18:get_channelid()
                if v20 then
                    p19:destroy()
                end;
                return v20;
            end)
            v_u_7:recalculate_all_message_positions()
        end;
        v6.sort_all_messages_by_time = function(_) --[[ Name: sort_all_messages_by_time ]] --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:get_message_display_elements():sort(function(p21, p22) --[[ Line: 79 ]]
                return p22:get_message_data():get_time() - p21:get_message_data():get_time();
            end)
            v_u_7:recalculate_all_message_positions()
        end;
        v6.update = function(_, p23) --[[ Name: update ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:update(p23)
        end;
        v6.Destroy = function(_) --[[ Name: Destroy ]] --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:destroy()
        end;
        v6.clear = function(_) --[[ Name: clear ]] --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:clear()
        end;
        v6:cons()
        return v6;
    end
};
