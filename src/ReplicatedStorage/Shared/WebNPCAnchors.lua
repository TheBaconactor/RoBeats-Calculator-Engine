-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v3 = {}
local v_u_4 = v1:new(require(game.ReplicatedStorage.CodeGen.WebNPCCFrames))
v3.get_cframe_for_anchor_name = function(_, p5) --[[ Name: get_cframe_for_anchor_name ]] --[[ Line: 8 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2 ]]
    if v_u_4:contains(p5) then
        return v_u_4:get(p5);
    end;
    v_u_2:warnf("WebNPCAnchors anchor(%s) not found", (tostring(p5)))
    return CFrame.new();
end;
local v_u_6 = nil
v3.get_webnpc_anchor_table_list = function(_) --[[ Name: get_webnpc_anchor_table_list ]] --[[ Line: 19 ]]
    --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_4 ]]
    if v_u_6 == nil then
        v_u_6 = {}
        for v7, _ in v_u_4:key_itr() do
            v_u_6[#v_u_6 + 1] = v7
        end;
    end;
    return v_u_6;
end;
local v_u_8 = v1:new()
v3.swap_in_random_anchor = function(_, p9, p10) --[[ Name: swap_in_random_anchor ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (ref 3): v_u_6 ]]
    local v11 = v_u_4:key_list()
    v11:set_local_random(p10)
    v11:remove_if(function(p12) --[[ Line: 33 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        return v_u_8:contains(p12);
    end)
    if v11:count() == 0 then
        v11 = v_u_4:key_list()
    end;
    local v13 = v11:random()
    v_u_4:add(v13, p9)
    v_u_8:add_set(v13)
    v_u_6 = nil
    return v13;
end;
return v3;
