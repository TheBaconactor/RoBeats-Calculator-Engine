-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.VArg)
return {
    ["puts"] = function(_, p_u_2, ...) --[[ Name: puts ]] --[[ Line: 4 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v_u_3 = p_u_2
        local v_u_4 = { v_u_1:arg_deconvert(...) }
        local v5, v6 = pcall(function() --[[ Line: 7 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_2, (copy 3): v_u_4 ]]
            v_u_3 = string.format(p_u_2, unpack(v_u_4))
        end)
        print((string.format("[Server] %s", v_u_3)))
        if v5 ~= true then
            warn("DebugOut:puts type mismatch(%s)", (tostring(v6)))
        end;
    end,
    ["warnf"] = function(_, p_u_7, ...) --[[ Name: warnf ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v_u_8 = p_u_7
        local v_u_9 = { v_u_1:arg_deconvert(...) }
        local v10, v11 = pcall(function() --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_7, (copy 3): v_u_9 ]]
            v_u_8 = string.format(p_u_7, unpack(v_u_9))
        end)
        warn((string.format("[Server] %s", v_u_8)))
        if v10 ~= true then
            warn("DebugOut:errf type mismatch(%s)", (tostring(v11)))
        end;
    end,
    ["errf"] = function(_, p_u_12, ...) --[[ Name: errf ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v_u_13 = p_u_12
        local v_u_14 = { v_u_1:arg_deconvert(...) }
        local v15, v16 = pcall(function() --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_12, (copy 3): v_u_14 ]]
            v_u_13 = string.format(p_u_12, unpack(v_u_14))
        end)
        local v17 = string.format("[Server] %s", v_u_13)
        if v15 ~= true then
            warn("DebugOut:errf type mismatch(%s)", (tostring(v16)))
        end;
        error(v17)
    end
};
