-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["get_base_fn"] = function(_, p2, p3) --[[ Name: get_base_fn ]] --[[ Line: 5 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v4 = p2[p3]
        if v4 == nil then
            v_u_1:errf("Override:get_base_fn(%s) base does not exist", (tostring(p3)))
        end;
        if typeof(v4) ~= "function" then
            v_u_1:errf("Override:get_base_fn(%s) base is not function", (tostring(p3)))
        end;
        return v4;
    end
};
