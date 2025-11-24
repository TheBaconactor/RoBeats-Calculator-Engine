-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.Constants)
local v_u_3 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
return {
    ["new"] = function(_, p_u_4) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3 ]]
        local v5 = {}
        v5.get_rbxid = function(_) --[[ Name: get_rbxid ]] --[[ Line: 11 ]]
            --[[ Upvalues: (copy 1): p_u_4 ]]
            return p_u_4;
        end;
        local v_u_6 = v_u_1:new()
        v5.add_channelid_chat_message = function(_, p7, p8) --[[ Name: add_channelid_chat_message ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_6 ]]
            v_u_2:is_int(p8:get_time())
            v_u_6:push_back_to(p7, p8)
        end;
        v5.is_channelid_on_chat_cooldown = function(_, p9) --[[ Name: is_channelid_on_chat_cooldown ]] --[[ Line: 20 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_3 ]]
            return v_u_6:count_of(p9) >= v_u_3:get_chat_cooldown_chat_amount();
        end;
        v5.get_time_to_channelid_message_queue_pop_sec = function(_, p10) --[[ Name: get_time_to_channelid_message_queue_pop_sec ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_3 ]]
            return v_u_6:count_of(p10) == 0 and 0 or v_u_3:get_chat_cooldown_time_sec() - (os.time() - v_u_6:list_of(p10):get(1):get_time());
        end;
        v5.update = function(_, _) --[[ Name: update ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_3 ]]
            local v11 = os.time()
            for _, v12 in v_u_6:key_itr() do
                if v12:count() > 0 and v11 - v12:get(1):get_time() >= v_u_3:get_chat_cooldown_time_sec() then
                    v12:pop_front()
                end;
            end;
        end;
        return v5;
    end
};
