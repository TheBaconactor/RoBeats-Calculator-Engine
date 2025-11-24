-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 7 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = {
            ["cons"] = function(_) end
        }
        local v_u_3 = v_u_1:new()
        v2.repool = function(_, p4, p5) --[[ Name: repool ]] --[[ Line: 15 ]]
            --[[ Upvalues: (copy 1): v_u_3 ]]
            v_u_3:push_back_to(p4, p5)
        end;
        v2.depool = function(_, p6) --[[ Name: depool ]] --[[ Line: 19 ]]
            --[[ Upvalues: (copy 1): v_u_3 ]]
            if v_u_3:count_of(p6) == 0 then
                return nil;
            else
                return v_u_3:pop_back_from(p6);
            end;
        end;
        v2:cons()
        return v2;
    end
};
