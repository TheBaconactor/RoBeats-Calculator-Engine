-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = {
    ["EventType"] = {
        ["VIPSale"] = 0,
        ["CoinSale"] = 1,
        ["StarSale"] = 2,
        ["PackSale"] = 3,
        ["RBChallenge"] = 4,
        ["RBSwordHunt"] = 5,
        ["SongLaunch"] = 6,
        ["HolidayEvent"] = 7,
        ["ArtistEvent"] = 8,
        ["HalloweenCountdown"] = 9,
        ["UpgradeSale"] = 10,
        ["CraftSale"] = 11,
        ["MiniSale"] = 12
    },
    ["EventList"] = {},
    ["ActiveEvent"] = {}
}
v_u_3.EventList.new = function(_) --[[ Name: new ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3 ]]
    local v11 = {
        ["is_any_event_in_list_active"] = function(p4, p5) --[[ Name: is_any_event_in_list_active ]] --[[ Line: 56 ]]
            for _, v6 in p5:key_itr() do
                local v7, v8, v9, v10 = p4:is_event_type_active(v6)
                if v7 == true then
                    return v7, v8, v9, v10;
                end;
            end;
            return false;
        end
    }
    local v_u_12 = v_u_1:new()
    v11.get_event_list = function(_) --[[ Name: get_event_list ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12;
    end;
    v11.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        local v13 = {}
        for v14 = 1, v_u_12:count() do
            v13[#v13 + 1] = v_u_12:get(v14):to_table()
        end;
        return v13;
    end;
    v11.is_event_type_active = function(_, p15) --[[ Name: is_event_type_active ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3, (copy 3): v_u_12 ]]
        v_u_2:is_enum_member(p15, v_u_3.EventType)
        local v16 = false
        local v17 = 0
        local v18 = ""
        local v19 = 0
        for v20 = 1, v_u_12:count() do
            local v21 = v_u_12:get(v20)
            if v21:get_param1() == p15 then
                v17 = v21:get_param2()
                v19 = v21:get_param3()
                v18 = v21:get_msg()
                v16 = true
            end;
        end;
        return v16, v17, v18, v19;
    end;
    return v11;
end;
v_u_3.EventList.default_list = function(_) --[[ Name: default_list ]] --[[ Line: 69 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return v_u_3.EventList:new();
end;
v_u_3.EventList.from_table = function(_, p22) --[[ Name: from_table ]] --[[ Line: 73 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v23 = v_u_3.EventList:new()
    for v24 = 1, #p22 do
        local v25 = p22[v24]
        v23:get_event_list():push_back(v_u_3.ActiveEvent:new(v25.EventId, v25.Param1, v25.Param2, v25.Param3, v25.Msg))
    end;
    return v23;
end;
v_u_3.ActiveEvent.new = function(_, p_u_26, p_u_27, p_u_28, p_u_29, p_u_30) --[[ Name: new ]] --[[ Line: 85 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    v_u_2:is_int_greater_than(p_u_26, 0)
    v_u_2:is_int(p_u_27)
    v_u_2:is_int(p_u_28)
    v_u_2:is_string(p_u_30)
    local v31 = {}
    v31.get_event_id = function(_) --[[ Name: get_event_id ]] --[[ Line: 92 ]]
        --[[ Upvalues: (copy 1): p_u_26 ]]
        return p_u_26;
    end;
    v31.get_param1 = function(_) --[[ Name: get_param1 ]] --[[ Line: 93 ]]
        --[[ Upvalues: (copy 1): p_u_27 ]]
        return p_u_27;
    end;
    v31.get_param2 = function(_) --[[ Name: get_param2 ]] --[[ Line: 94 ]]
        --[[ Upvalues: (copy 1): p_u_28 ]]
        return p_u_28;
    end;
    v31.get_param3 = function(_) --[[ Name: get_param3 ]] --[[ Line: 95 ]]
        --[[ Upvalues: (copy 1): p_u_29 ]]
        return p_u_29;
    end;
    v31.get_msg = function(_) --[[ Name: get_msg ]] --[[ Line: 96 ]]
        --[[ Upvalues: (copy 1): p_u_30 ]]
        return p_u_30;
    end;
    v31.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 98 ]]
        --[[ Upvalues: (copy 1): p_u_26, (copy 2): p_u_27, (copy 3): p_u_28, (copy 4): p_u_29, (copy 5): p_u_30 ]]
        return {
            ["EventId"] = p_u_26,
            ["Param1"] = p_u_27,
            ["Param2"] = p_u_28,
            ["Param3"] = p_u_29,
            ["Msg"] = p_u_30
        };
    end;
    return v31;
end;
return v_u_3;
