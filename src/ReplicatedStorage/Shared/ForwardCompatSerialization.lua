-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 5 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = {}
        local v_u_3 = v_u_1:new()
        v2.write_forward_compat_properties_to_table = function(_, p4) --[[ Name: write_forward_compat_properties_to_table ]] --[[ Line: 10 ]]
            --[[ Upvalues: (copy 1): v_u_3 ]]
            for v5, v6 in v_u_3:key_itr() do
                p4[v5] = v6
            end;
            return p4;
        end;
        v2.store_forward_compat_properties = function(_, p7, p8) --[[ Name: store_forward_compat_properties ]] --[[ Line: 17 ]]
            --[[ Upvalues: (copy 1): v_u_3 ]]
            for v9, v10 in pairs(p8) do
                if p7[v9] == nil then
                    v_u_3:add(v9, v10)
                end;
            end;
        end;
        return v2;
    end
};
