-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_3 ]]
        local v_u_7 = {
            ["add_cooldown"] = function(p5, p6) --[[ Name: add_cooldown ]] --[[ Line: 26 ]]
                p5:add_cooldown_to_id(1, p6)
            end
        }
        local v_u_8 = v_u_1:new()
        local v_u_9 = v_u_2:new()
        v_u_7.is_on_cooldown = function(_, p10) --[[ Name: is_on_cooldown ]] --[[ Line: 15 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            return v_u_8:contains(p10 == nil and 1 or p10);
        end;
        v_u_7.get_cooldown_time = function(_, p11) --[[ Name: get_cooldown_time ]] --[[ Line: 20 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            local v12 = p11 == nil and 1 or p11
            return v_u_8:contains(v12) ~= true and 0 or v_u_8:get(v12);
        end;
        v_u_7.add_cooldown_to_id = function(_, p13, p14) --[[ Name: add_cooldown_to_id ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            v_u_8:add(p13, p14)
        end;
        v_u_7.remove_cooldown_from_id = function(_, p15) --[[ Name: remove_cooldown_from_id ]] --[[ Line: 34 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            v_u_8:remove(p15)
        end;
        v_u_7.add_min_cooldown_to_id = function(_, p16, p17) --[[ Name: add_min_cooldown_to_id ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            v_u_8:add(p16, (math.max(v_u_8:get(p16), p17)))
        end;
        local function _(p18, p19, p20) --[[ Name: on_cooldown_fnslist_apply ]] --[[ Line: 42 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_9 ]]
            if v_u_7:is_on_cooldown(p18) ~= true then
                return p19();
            end;
            p20(v_u_9:list_of(p18))
        end;
        v_u_7.on_cooldown_queue = function(_, p21, p_u_22) --[[ Name: on_cooldown_queue ]] --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_9 ]]
            local function v24(p23) --[[ Line: 48 ]]
                --[[ Upvalues: (copy 1): p_u_22 ]]
                p23:push_back(p_u_22)
            end;
            if v_u_7:is_on_cooldown(p21) == true then
                v24(v_u_9:list_of(p21))
            else
                p_u_22()
            end;
        end;
        v_u_7.on_cooldown_last = function(_, p25, p_u_26) --[[ Name: on_cooldown_last ]] --[[ Line: 53 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_9 ]]
            local function v28(p27) --[[ Line: 54 ]]
                --[[ Upvalues: (copy 1): p_u_26 ]]
                p27:clear()
                p27:push_back(p_u_26)
            end;
            if v_u_7:is_on_cooldown(p25) == true then
                v28(v_u_9:list_of(p25))
            else
                p_u_26()
            end;
        end;
        local v_u_29 = v_u_4:new()
        v_u_7.get_frame_removed_ids = function(_) --[[ Name: get_frame_removed_ids ]] --[[ Line: 61 ]]
            --[[ Upvalues: (copy 1): v_u_29 ]]
            return v_u_29;
        end;
        v_u_7.update = function(_, p30) --[[ Name: update ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_8, (copy 3): v_u_29, (ref 4): v_u_1, (copy 5): v_u_9 ]]
            local v31 = v_u_3:TimescaleToDeltaTime(p30)
            for v32, v33 in v_u_8:key_itr() do
                v_u_8:add(v32, v33 - v31)
            end;
            v_u_29:clear()
            v_u_1:remove_if(v_u_8, function(p34, p35) --[[ Line: 72 ]]
                --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_29 ]]
                local v36 = p34 <= 0
                if v36 then
                    if v_u_9._dict:contains(p35) then
                        for _, v37 in v_u_9:list_of(p35):key_itr() do
                            v37()
                        end;
                        v_u_9:remove(p35)
                    end;
                    v_u_29:push_back(p35)
                end;
                return v36;
            end)
        end;
        return v_u_7;
    end
};
