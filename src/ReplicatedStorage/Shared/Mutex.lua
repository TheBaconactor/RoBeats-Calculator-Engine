-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v6 = {
            ["add_to_mutex_list"] = function(p4, p5) --[[ Name: add_to_mutex_list ]] --[[ Line: 67 ]]
                p5:push_back(p4)
                return p4;
            end
        }
        local v_u_7 = v_u_1:new()
        v6.test = function(_, p8) --[[ Name: test ]] --[[ Line: 12 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7:contains(p8);
        end;
        v6.retain = function(_, p9) --[[ Name: retain ]] --[[ Line: 16 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            if v_u_7:contains(p9) then
                v_u_7:add(p9, v_u_7:get(p9) + 1)
            else
                v_u_7:add(p9, 1)
            end;
        end;
        v6.release = function(_, p10) --[[ Name: release ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            if v_u_7:contains(p10) then
                local v11 = v_u_7:get(p10)
                if v11 == 1 then
                    v_u_7:remove(p10)
                    return;
                end;
                v_u_7:add(p10, v11 - 1)
            end;
        end;
        v6.count = function(_, p12) --[[ Name: count ]] --[[ Line: 35 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return not v_u_7:contains(p12) and 0 or v_u_7:get(p12);
        end;
        local v_u_13 = v_u_1:new()
        v6.update = function(_, p14) --[[ Name: update ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_13, (ref 3): v_u_3, (ref 4): v_u_2 ]]
            for v15, _ in v_u_7:key_itr() do
                if v_u_13:contains(v15) ~= true then
                    v_u_13:add(v15, 0)
                end;
            end;
            for _, v16 in v_u_13:key_list():key_itr() do
                if v_u_7:contains(v16) == true then
                    local v17 = v_u_13:get(v16)
                    if v17 < 10 then
                        v_u_13:add(v16, v17 + v_u_3:TimescaleToDeltaTime(p14))
                    else
                        v_u_13:remove(v16)
                        v_u_7:remove(v16)
                        v_u_2:warnf("Mutex:update timeout for lock(%s)", (tostring(v16)))
                    end;
                else
                    v_u_13:remove(v16)
                end;
            end;
        end;
        return v6;
    end,
    ["critical_section"] = function(_, p_u_18, p_u_19, p_u_20, p_u_21) --[[ Name: critical_section ]] --[[ Line: 75 ]]
        local function _() --[[ Name: perform ]] --[[ Line: 76 ]]
            --[[ Upvalues: (copy 1): p_u_19, (copy 2): p_u_21, (copy 3): p_u_20 ]]
            p_u_19()
            p_u_21(p_u_19, p_u_20)
            p_u_20()
        end;
        if p_u_18() then
            local v_u_22 = 0.1
            spawn(function() --[[ Line: 84 ]]
                --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_22, (copy 3): p_u_19, (copy 4): p_u_21, (copy 5): p_u_20 ]]
                while p_u_18() do
                    wait(v_u_22)
                    v_u_22 = v_u_22 + 0.1
                end;
                p_u_19()
                p_u_21(p_u_19, p_u_20)
                p_u_20()
            end)
        else
            p_u_19()
            p_u_21(p_u_19, p_u_20)
            p_u_20()
        end;
    end,
    ["update_mutex_list"] = function(_, p23, p24) --[[ Name: update_mutex_list ]] --[[ Line: 96 ]]
        for _, v25 in p23:key_itr() do
            v25:update(p24)
        end;
    end
};
