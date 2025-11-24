-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_13 = {
    ["Type"] = {
        ["None"] = 0,
        ["ArtistEventButton"] = 1
    },
    ["list_to_table"] = function(_, p3) --[[ Name: list_to_table ]] --[[ Line: 43 ]]
        local v4 = {}
        for v5 = 1, p3:count() do
            v4[#v4 + 1] = p3:get(v5):to_table()
        end;
        return v4;
    end,
    ["create_display_wrapper"] = function(_, p_u_6, p_u_7) --[[ Name: create_display_wrapper ]] --[[ Line: 51 ]]
        local v8 = {}
        p_u_6.Visible = false
        local v_u_9 = false
        local v_u_10 = nil
        v8.update_state = function(_, p11, p12) --[[ Name: update_state ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (copy 3): p_u_6, (copy 4): p_u_7 ]]
            if p11 ~= v_u_9 or p12 ~= v_u_10 then
                if p11 then
                    p_u_6.Visible = true
                    p_u_7.Text = tostring(p12)
                else
                    p_u_6.Visible = false
                end;
                v_u_9 = p11
                v_u_10 = p12
            end;
        end;
        return v8;
    end
}
v_u_13.new = function(_, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_13 ]]
    v_u_1:is_enum_member(p_u_14, v_u_13.Type)
    v_u_1:is_int(p_u_15)
    local v16 = {}
    v16.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 16 ]]
        --[[ Upvalues: (ref 1): p_u_14 ]]
        return p_u_14;
    end;
    v16.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 17 ]]
        --[[ Upvalues: (ref 1): p_u_15 ]]
        return p_u_15;
    end;
    v16.load_from_table = function(p17, p18) --[[ Name: load_from_table ]] --[[ Line: 19 ]]
        --[[ Upvalues: (ref 1): p_u_14, (ref 2): p_u_15 ]]
        p_u_14 = p18.Type
        p_u_15 = p18.Count
        return p17;
    end;
    v16.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 25 ]]
        --[[ Upvalues: (ref 1): p_u_14, (ref 2): p_u_15 ]]
        return {
            ["Type"] = p_u_14,
            ["Count"] = p_u_15
        };
    end;
    return v16;
end;
v_u_13.table_to_list = function(_, p19) --[[ Name: table_to_list ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_13 ]]
    local v20 = v_u_2:new()
    for v21 = 1, #p19 do
        v20:push_back(v_u_13:new(v_u_13.Type.None, 0):load_from_table(p19[v21]))
    end;
    return v20;
end;
return v_u_13;
