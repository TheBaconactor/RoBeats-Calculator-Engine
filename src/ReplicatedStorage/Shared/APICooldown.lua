-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v5 = {}
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList):new()
v5.update_active_api_cooldowns = function(_) --[[ Name: update_active_api_cooldowns ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    for v7 = 1, v_u_6:count() do
        v_u_6:get(v7):update()
    end;
end;
v5.new = function(_) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_3 ]]
    local v_u_8 = {}
    local function _() --[[ Name: cons ]] --[[ Line: 30 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_8 ]]
        v_u_6:push_back(v_u_8)
    end;
    local v_u_9 = v_u_1:new()
    local v_u_10 = 3
    v_u_8.set_cooldown = function(p11, p12) --[[ Name: set_cooldown ]] --[[ Line: 37 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        v_u_10 = p12
        return p11;
    end;
    local v_u_13 = 1
    v_u_8.set_max_queued_requests = function(p14, p15) --[[ Name: set_max_queued_requests ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        v_u_13 = p15
        return p14;
    end;
    local v_u_16 = true
    v_u_8.set_do_replace_last_queued_request = function(p17, p18) --[[ Name: set_do_replace_last_queued_request ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        v_u_16 = p18
        return p17;
    end;
    v_u_8.try_run_key_request = function(_, p19, p20) --[[ Name: try_run_key_request ]] --[[ Line: 54 ]]
        --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_10 ]]
        if v_u_9:is_on_cooldown(p19) == true then
            return false;
        end;
        v_u_9:add_cooldown_to_id(p19, v_u_10)
        p20()
        return true;
    end;
    local v_u_21 = v_u_4:new()
    v_u_8.queue_key_request = function(_, p22, p23) --[[ Name: queue_key_request ]] --[[ Line: 65 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_21, (ref 3): v_u_13, (ref 4): v_u_16, (ref 5): v_u_10 ]]
        if v_u_9:is_on_cooldown(p22) == true then
            if v_u_13 <= v_u_21:count_of(p22) then
                if v_u_16 ~= true then
                    return false;
                end;
                v_u_21:pop_front_from(p22)
            end;
            v_u_21:push_back_to(p22, p23)
            return false;
        else
            v_u_9:add_cooldown_to_id(p22, v_u_10)
            p23()
            return true;
        end;
    end;
    local function f_update(p24) --[[ Name: update ]] --[[ Line: 83 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_21, (ref 3): v_u_2, (ref 4): v_u_10 ]]
        v_u_9:update(p24)
        if v_u_21:count() > 0 then
            for v25, v26 in v_u_21:key_itr() do
                if v_u_9:is_on_cooldown(v25) ~= true and v26:count() ~= 0 then
                    local v_u_27 = v26:pop_front()
                    if v_u_27 ~= nil then
                        v_u_2:ptry(function() --[[ Line: 95 ]]
                            --[[ Upvalues: (copy 1): v_u_27 ]]
                            v_u_27()
                        end)
                        v_u_9:add_cooldown_to_id(v25, v_u_10)
                    end;
                end;
            end;
            v_u_21:get_dict():remove_if(function(p28) --[[ Line: 101 ]]
                return p28:count() == 0;
            end)
        end;
    end;
    local v_u_29 = tick()
    v_u_8.update = function(_) --[[ Name: update ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_29, (copy 3): f_update, (ref 4): v_u_3 ]]
        v_u_2:ptry(function() --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): f_update, (ref 3): v_u_3 ]]
            local v30 = tick()
            f_update(v_u_3:DeltaTimeToTimescale(v30 - v_u_29))
            v_u_29 = v30
        end)
    end;
    v_u_6:push_back(v_u_8)
    return v_u_8;
end;
return v5;
