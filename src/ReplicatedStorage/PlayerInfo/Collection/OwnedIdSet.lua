-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.Bit)
local v_u_20 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_1 ]]
        local v4 = {}
        local v_u_5 = 0
        local v_u_6 = v_u_2:new()
        v4.set_id_owned = function(_, p7, p8) --[[ Name: set_id_owned ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_6, (ref 3): v_u_5 ]]
            v_u_3:is_int(p7)
            v_u_3:is_bool(p8)
            v_u_6:add(tostring(p7), p8)
            if p8 then
                v_u_5 = math.max(p7, v_u_5)
            end;
        end;
        v4.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            local v9 = 0
            for _, v10 in v_u_6:key_itr() do
                if v10 == true then
                    v9 = v9 + 1
                end;
            end;
            return v9;
        end;
        v4.is_id_owned = function(_, p11) --[[ Name: is_id_owned ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            return v_u_6:get((tostring(p11))) == true;
        end;
        v4.get_owned_id_list = function(_) --[[ Name: get_owned_id_list ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_6 ]]
            local v12 = v_u_1:new()
            for v13, v14 in v_u_6:key_itr() do
                if v14 then
                    v12:push_back((tonumber(v13)))
                end;
            end;
            return v12;
        end;
        v4.to_table = function(p15) --[[ Name: to_table ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_5 ]]
            local v16 = v_u_1:new()
            local v17 = 1
            while v17 <= v_u_5 do
                local v18 = 0
                for v19 = 0, 31 do
                    if p15:is_id_owned(v17 + v19) then
                        v18 = bit32.bor(v18, (bit32.lshift(1, v19)))
                    end;
                end;
                v16:push_back(v18)
                v17 = v17 + 32
            end;
            return v16:get_table();
        end;
        return v4;
    end
}
v_u_20.from_table = function(_, p21) --[[ Name: from_table ]] --[[ Line: 72 ]]
    --[[ Upvalues: (copy 1): v_u_20 ]]
    local v22 = v_u_20:new()
    if typeof(p21) ~= "table" then
        return v22;
    end;
    for v23 = 1, #p21 do
        local v24 = (v23 - 1) * 32 + 1
        local v25 = p21[v23]
        if typeof(v25) ~= "number" then
            return v22;
        end;
        for v26 = 0, 31 do
            v22:set_id_owned(v24 + v26, bit32.band(v25, (bit32.lshift(1, v26))) > 0)
        end;
    end;
    return v22;
end;
return v_u_20;
