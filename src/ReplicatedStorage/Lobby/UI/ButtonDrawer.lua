-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = {
    ["State"] = {
        ["Minimized"] = 0,
        ["Expanded"] = 1
    }
}
v_u_3.new = function(_) --[[ Name: new ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3 ]]
    local v4 = {}
    local v_u_5 = v_u_2:new()
    local v_u_6 = v_u_2:new()
    local v_u_7 = v_u_1:new()
    local v_u_8 = v_u_2:new()
    local v_u_9 = v_u_2:new()
    v4.add_to_expanded_elements = function(_, p10, p11) --[[ Name: add_to_expanded_elements ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        v_u_6:push_back_to(p10, p11)
    end;
    v4.add_to_minimized_elements = function(_, p12, p13) --[[ Name: add_to_minimized_elements ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        v_u_5:push_back_to(p12, p13)
    end;
    v4.add_to_expanded_uielements = function(_, p14, p15) --[[ Name: add_to_expanded_uielements ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_9 ]]
        v_u_9:push_back_to(p14, p15)
    end;
    v4.add_to_minimized_uielements = function(_, p16, p17) --[[ Name: add_to_minimized_uielements ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_8 ]]
        v_u_8:push_back_to(p16, p17)
    end;
    v4.get_expand_state = function(_, p18) --[[ Name: get_expand_state ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        return v_u_7:get(p18);
    end;
    v4.set_expand_state = function(_, p19, p20) --[[ Name: set_expand_state ]] --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        v_u_7:add(p19, p20)
    end;
    v4.refresh_expand_state_buttons = function(_) --[[ Name: refresh_expand_state_buttons ]] --[[ Line: 47 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_5, (copy 3): v_u_6, (ref 4): v_u_3, (copy 5): v_u_8, (copy 6): v_u_9 ]]
        for v21, v22 in v_u_7:key_itr() do
            local v23 = v_u_5:list_of(v21)
            local v24 = v_u_6:list_of(v21)
            for v25 = 1, v23:count() do
                v23:get(v25):set_visible(v22 == v_u_3.State.Minimized, true)
            end;
            for v26 = 1, v24:count() do
                v24:get(v26):set_visible(v22 == v_u_3.State.Expanded, true)
            end;
            local v27 = v_u_8:list_of(v21)
            local v28 = v_u_9:list_of(v21)
            for v29 = 1, v27:count() do
                v27:get(v29).Visible = v22 == v_u_3.State.Minimized
            end;
            for v30 = 1, v28:count() do
                v28:get(v30).Visible = v22 == v_u_3.State.Expanded
            end;
        end;
    end;
    return v4;
end;
return v_u_3;
