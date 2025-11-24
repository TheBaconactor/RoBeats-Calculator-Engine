-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
return {
    ["new"] = function(_, p2, p3) --[[ Name: new ]] --[[ Line: 4 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v14 = {
            ["Type"] = "SPRange",
            ["_min"] = p2,
            ["_max"] = p3,
            ["set_min_max"] = function(p4, p5, p6) --[[ Name: set_min_max ]] --[[ Line: 21 ]]
                p4:set_min(p5)
                p4:set_max(p6)
            end,
            ["min"] = function(p7) --[[ Name: min ]] --[[ Line: 25 ]]
                return p7._min;
            end,
            ["max"] = function(p8) --[[ Name: max ]] --[[ Line: 26 ]]
                return p8._max;
            end,
            ["contains"] = function(p9, p10) --[[ Name: contains ]] --[[ Line: 27 ]]
                return p9:contains_eq(p10);
            end,
            ["contains_eq"] = function(p11, p12) --[[ Name: contains_eq ]] --[[ Line: 30 ]]
                local v13
                if p11:min() <= p12 then
                    v13 = p12 <= p11:max()
                else
                    v13 = false
                end;
                return v13;
            end
        }
        v_u_1:is_number(v14._min)
        v_u_1:is_number(v14._max)
        v14.set_min = function(p15, p16) --[[ Name: set_min ]] --[[ Line: 13 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:is_number(p16)
            p15._min = p16
        end;
        v14.set_max = function(p17, p18) --[[ Name: set_max ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:is_number(p18)
            p17._max = p18
        end;
        return v14;
    end
};
