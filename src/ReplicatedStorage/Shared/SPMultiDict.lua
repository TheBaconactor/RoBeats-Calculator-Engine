-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v_u_9 = {
            ["_dict"] = v_u_1:new(),
            ["get_dict"] = function(p3) --[[ Name: get_dict ]] --[[ Line: 11 ]]
                return p3._dict;
            end,
            ["remove"] = function(p4, p5) --[[ Name: remove ]] --[[ Line: 51 ]]
                return p4._dict:remove(p5);
            end,
            ["key_itr"] = function(p6) --[[ Name: key_itr ]] --[[ Line: 54 ]]
                return p6._dict:key_itr();
            end,
            ["count"] = function(p7) --[[ Name: count ]] --[[ Line: 57 ]]
                return p7._dict:count();
            end,
            ["clear"] = function(p8) --[[ Name: clear ]] --[[ Line: 61 ]]
                p8._dict:clear()
                return p8;
            end
        }
        local function _(p10) --[[ Name: verify_list_exists ]] --[[ Line: 13 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_2 ]]
            if not v_u_9._dict:contains(p10) then
                v_u_9._dict:add(p10, v_u_2:new())
            end;
        end;
        v_u_9.count_of = function(p11, p12) --[[ Name: count_of ]] --[[ Line: 19 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_2 ]]
            if not v_u_9._dict:contains(p12) then
                v_u_9._dict:add(p12, v_u_2:new())
            end;
            return p11._dict:get(p12):count();
        end;
        v_u_9.push_back_to = function(p13, p14, p15) --[[ Name: push_back_to ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_2 ]]
            if not v_u_9._dict:contains(p14) then
                v_u_9._dict:add(p14, v_u_2:new())
            end;
            p13._dict:get(p14):push_back(p15)
        end;
        v_u_9.push_front_to = function(p16, p17, p18) --[[ Name: push_front_to ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_2 ]]
            if not v_u_9._dict:contains(p17) then
                v_u_9._dict:add(p17, v_u_2:new())
            end;
            p16._dict:get(p17):push_front(p18)
        end;
        v_u_9.pop_back_from = function(p19, p20) --[[ Name: pop_back_from ]] --[[ Line: 31 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_2 ]]
            if not v_u_9._dict:contains(p20) then
                v_u_9._dict:add(p20, v_u_2:new())
            end;
            local v21 = p19._dict:get(p20):pop_back()
            if p19._dict:get(p20):count() == 0 then
                p19._dict:add(p20, nil)
            end;
            return v21;
        end;
        v_u_9.pop_front_from = function(p22, p23) --[[ Name: pop_front_from ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_2 ]]
            if not v_u_9._dict:contains(p23) then
                v_u_9._dict:add(p23, v_u_2:new())
            end;
            local v24 = p22._dict:get(p23):pop_front()
            if p22._dict:get(p23):count() == 0 then
                p22._dict:add(p23, nil)
            end;
            return v24;
        end;
        v_u_9.list_of = function(p25, p26) --[[ Name: list_of ]] --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_2 ]]
            if not v_u_9._dict:contains(p26) then
                v_u_9._dict:add(p26, v_u_2:new())
            end;
            return p25._dict:get(p26);
        end;
        return v_u_9;
    end
};
