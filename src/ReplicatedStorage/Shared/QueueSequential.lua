-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["new"] = function(_, p_u_4) --[[ Name: new ]] --[[ Line: 7 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v5 = {}
        local v_u_6 = v_u_1:new()
        local v_u_7 = false
        local function v_u_11() --[[ Line: 13 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_6, (ref 3): v_u_3, (copy 4): p_u_4, (ref 5): v_u_11, (ref 6): v_u_2 ]]
            if v_u_7 == false and v_u_6:count() > 0 then
                local v_u_8 = v_u_6:pop_back()
                v_u_7 = true
                local v9, v10 = v_u_3:try(function() --[[ Line: 18 ]]
                    --[[ Upvalues: (ref 1): p_u_4, (copy 2): v_u_8, (ref 3): v_u_7, (ref 4): v_u_11 ]]
                    p_u_4(v_u_8[1], function(...) --[[ Line: 19 ]]
                        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_11 ]]
                        v_u_7 = false
                        if typeof(v_u_8[2]) == "function" then
                            v_u_8[2](...)
                        end;
                        v_u_11()
                    end)
                end)
                if v9 ~= true then
                    v_u_11()
                    v_u_2:warnf("QueueSequential ERR(%s)[%s]", v10.Error, v10.StackTrace)
                end;
            end;
        end;
        v5.queue_sequential = function(_, p12, p13) --[[ Name: queue_sequential ]] --[[ Line: 34 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_11 ]]
            v_u_6:push_front({ p12, p13 })
            v_u_11()
        end;
        v5.force_active = function(_, p14) --[[ Name: force_active ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7 = p14
        end;
        v5.dequeue_and_apply = function(_) --[[ Name: dequeue_and_apply ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11()
        end;
        return v5;
    end
};
