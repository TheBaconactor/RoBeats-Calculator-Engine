-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v4 = {}
        local v_u_5 = v_u_1:new()
        v4.enqueue_function = function(_, p6, p7) --[[ Name: enqueue_function ]] --[[ Line: 10 ]]
            --[[ Upvalues: (copy 1): v_u_5 ]]
            v_u_5:push_back({
                ["Fn"] = p6,
                ["Delay"] = p7 == nil and 0 or p7
            })
        end;
        v4.delay_sec_fn_call = function(p8, p9, p10) --[[ Name: delay_sec_fn_call ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            p8:enqueue_function(p10, v_u_3:DeltaTimeToTimescale(p9))
        end;
        local v_u_11 = nil
        v4.set_error_function = function(_, p12) --[[ Name: set_error_function ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p12
        end;
        v4.update = function(_, p13) --[[ Name: update ]] --[[ Line: 29 ]]
            --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_2, (ref 3): v_u_11 ]]
            for v14 = v_u_5:count(), 1, -1 do
                local v_u_15 = v_u_5:get(v14)
                v_u_15.Delay = v_u_15.Delay - p13
                if v_u_15.Delay <= 0 then
                    local v16, v17 = v_u_2:try(function() --[[ Line: 34 ]]
                        --[[ Upvalues: (copy 1): v_u_15 ]]
                        v_u_15.Fn()
                    end)
                    if not v16 and v_u_11 then
                        v_u_11(v17)
                    end;
                    v_u_5:remove_at(v14)
                end;
            end;
        end;
        return v4;
    end
};
