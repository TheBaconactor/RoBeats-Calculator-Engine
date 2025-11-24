-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 5 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v3 = {
            ["get_stdev"] = function(p2) --[[ Name: get_stdev ]] --[[ Line: 34 ]]
                return math.sqrt((p2:get_var()));
            end
        }
        local v_u_4 = 0
        local v_u_5 = 0
        local v_u_6 = 0
        local v_u_7 = 0
        v3.push_val = function(_, p8, p9) --[[ Name: push_val ]] --[[ Line: 12 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4, (ref 3): v_u_6, (ref 4): v_u_7 ]]
            local v10 = p9 == nil and 1 or p9
            local v11 = p8 - v_u_5
            local v12 = v_u_4 + v10
            local v13 = v11 * v10 / v12
            v_u_5 = v_u_5 + v13
            v_u_6 = v_u_6 + v11 * v13 * v_u_4
            v_u_4 = v12
            v_u_7 = v_u_7 + 1
        end;
        v3.get_ct = function(_) --[[ Name: get_ct ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        v3.get_avg = function(_) --[[ Name: get_avg ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            return v_u_5;
        end;
        v3.get_var = function(_) --[[ Name: get_var ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_1 ]]
            local v14 = v_u_6 * v_u_7 / (v_u_4 * (v_u_7 - 1))
            return v_u_1:is_finite(v14) ~= true and 0 or v14;
        end;
        return v3;
    end
};
