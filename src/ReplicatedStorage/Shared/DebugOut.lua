-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v1 = {}
local v_u_2 = nil
local v_u_3 = nil
local v_u_4 = nil
v1.set_as_client = function(_) --[[ Name: set_as_client ]] --[[ Line: 7 ]]
    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_4 ]]
    if v_u_2 == nil then
        v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
    end;
    v_u_4 = v_u_2
end;
v1.set_as_server = function(_) --[[ Name: set_as_server ]] --[[ Line: 13 ]]
    --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4 ]]
    if v_u_3 == nil then
        v_u_3 = require(game.ReplicatedStorage.Server.DebugOut)
    end;
    v_u_4 = v_u_3
end;
v1.puts = function(_, p5, ...) --[[ Name: puts ]] --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    if v_u_4 then
        v_u_4:puts(p5, ...)
    end;
end;
v1.errf = function(_, p6, ...) --[[ Name: errf ]] --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    if v_u_4 then
        v_u_4:errf(p6, ...)
    end;
end;
v1.warnf = function(_, p7, ...) --[[ Name: warnf ]] --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    if v_u_4 then
        v_u_4:warnf(p7, ...)
    end;
end;
return v1;
