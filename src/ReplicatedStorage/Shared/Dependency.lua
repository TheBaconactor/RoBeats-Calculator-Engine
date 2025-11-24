-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPList)
local v2 = {}
local v_u_3 = v1:new()
local v_u_4 = v1:new()
local v_u_5 = v1:new()
local v_u_6 = false
local function f_load_requires_shared() --[[ Name: load_requires_shared ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_3, (ref 2): v_u_6 ]]
    while v_u_3:count() > 0 do
        v_u_3:pop_back()()
    end;
    v_u_6 = true
end;
local v_u_7 = false
v2.load_requires_client = function(_) --[[ Name: load_requires_client ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_7, (copy 3): f_load_requires_shared ]]
    while v_u_5:count() > 0 do
        v_u_5:pop_back()()
    end;
    v_u_7 = true
    f_load_requires_shared()
end;
local v_u_8 = false
v2.load_requires_server = function(_) --[[ Name: load_requires_server ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_8, (copy 3): f_load_requires_shared ]]
    while v_u_4:count() > 0 do
        v_u_4:pop_back()()
    end;
    v_u_8 = true
    f_load_requires_shared()
end;
v2.require_server = function(_, p_u_9) --[[ Name: require_server ]] --[[ Line: 41 ]]
    --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_4 ]]
    if v_u_8 then
        return p_u_9();
    end;
    v_u_4:push_back(function() --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): p_u_9 ]]
        p_u_9()
    end)
end;
v2.require_client = function(_, p_u_10) --[[ Name: require_client ]] --[[ Line: 48 ]]
    --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_5 ]]
    if v_u_7 then
        return p_u_10();
    end;
    v_u_5:push_back(function() --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): p_u_10 ]]
        p_u_10()
    end)
end;
v2.require_shared = function(_, p_u_11) --[[ Name: require_shared ]] --[[ Line: 55 ]]
    --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_3 ]]
    if v_u_6 then
        return p_u_11();
    end;
    v_u_3:push_back(function() --[[ Line: 57 ]]
        --[[ Upvalues: (copy 1): p_u_11 ]]
        p_u_11()
    end)
end;
return v2;
