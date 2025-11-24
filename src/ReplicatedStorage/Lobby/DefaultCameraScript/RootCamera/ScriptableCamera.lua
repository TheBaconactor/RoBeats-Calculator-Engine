-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local v_u_1 = require(script.Parent)
return function() --[[ Name: CreateScriptableCamera ]] --[[ Line: 3 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v2 = v_u_1()
    tick()
    v2.Update = function(_) end;
    return v2;
end;
