-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
return {
    ["new"] = function(_, p_u_2) --[[ Name: new ]] --[[ Line: 5 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v3 = {}
        local v_u_4 = 0
        local v_u_5 = 0
        v3.cons = function(p6) --[[ Name: cons ]] --[[ Line: 10 ]]
            --[[ Upvalues: (copy 1): p_u_2 ]]
            p6:set_flash_speed(p_u_2)
        end;
        v3.update = function(_, p7) --[[ Name: update ]] --[[ Line: 14 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4 ]]
            v_u_5 = v_u_5 + v_u_4 * p7
        end;
        v3.set_flash_speed = function(_, p8) --[[ Name: set_flash_speed ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1 ]]
            v_u_4 = v_u_1:SecondsToTick(p8)
        end;
        v3.flash_now = function(_) --[[ Name: flash_now ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            v_u_5 = 1
        end;
        v3.reset = function(_) --[[ Name: reset ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            v_u_5 = 0
        end;
        v3.do_flash = function(_) --[[ Name: do_flash ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            local v9 = v_u_5 >= 1
            if v9 then
                v_u_5 = 0
            end;
            return v9;
        end;
        v3:cons()
        return v3;
    end
};
