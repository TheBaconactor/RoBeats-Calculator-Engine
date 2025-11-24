-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_7 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_9 = {
    ["SlotDanceInfo"] = {},
    ["get_default_dance_id"] = function(_) --[[ Name: get_default_dance_id ]] --[[ Line: 78 ]]
        return 10;
    end,
    ["Type"] = "GameDanceInfo",
    ["key_for_slot"] = function(_, p8) --[[ Name: key_for_slot ]] --[[ Line: 132 ]]
        return string.format("Slot%d", p8);
    end
}
v_u_9.SlotDanceInfo.new = function(_) --[[ Name: new ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_5 ]]
    local v10 = {}
    local v_u_11 = v_u_2:new()
    v10.add_type_danceid = function(_, p12, p13) --[[ Name: add_type_danceid ]] --[[ Line: 17 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): v_u_5, (copy 4): v_u_11 ]]
        v_u_3:is_enum_member(p12, v_u_4)
        v_u_3:is_true(v_u_5:singleton():contains_dance_for_id(p13))
        v_u_3:is_false(v_u_11:list_of(p12):contains(p13))
        v_u_11:push_back_to(p12, p13)
    end;
    v10.get_danceids_for_type = function(_, p14) --[[ Name: get_danceids_for_type ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        return v_u_11:list_of(p14);
    end;
    v10.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_11, (ref 2): v_u_4 ]]
        return {
            ["OnMiss"] = v_u_11:list_of(v_u_4.OnMiss)._table,
            ["Standard"] = v_u_11:list_of(v_u_4.Standard)._table,
            ["Combo"] = v_u_11:list_of(v_u_4.Combo)._table
        };
    end;
    return v10;
end;
v_u_9.SlotDanceInfo.from_table = function(_, p15) --[[ Name: from_table ]] --[[ Line: 40 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_4 ]]
    local v16 = v_u_9.SlotDanceInfo:new()
    local l_OnMiss_0 = p15.OnMiss
    for v17 = 1, #l_OnMiss_0 do
        v16:add_type_danceid(v_u_4.OnMiss, l_OnMiss_0[v17])
    end;
    local l_Standard_0 = p15.Standard
    for v18 = 1, #l_Standard_0 do
        v16:add_type_danceid(v_u_4.Standard, l_Standard_0[v18])
    end;
    local l_Combo_0 = p15.Combo
    for v19 = 1, #l_Combo_0 do
        v16:add_type_danceid(v_u_4.Combo, l_Combo_0[v19])
    end;
    return v16;
end;
v_u_9.get_default_dance_info = function(_) --[[ Name: get_default_dance_info ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_6, (copy 3): v_u_7, (copy 4): v_u_5 ]]
    local v20 = v_u_9:new()
    for v21 = v_u_6.SLOT_MIN, v_u_6.SLOT_MAX do
        local v22 = v_u_9.SlotDanceInfo:new()
        for v23 = v_u_7.DEFAULT_EQUIPPED_MIN_ID, v_u_7.DEFAULT_EQUIPPED_MAX_ID do
            v22:add_type_danceid(v_u_5:singleton():get_dance_type_for_id(v23), v23)
        end;
        v20:add_slot_slotdanceinfo(v21, v22)
    end;
    return v20;
end;
local v_u_24 = v_u_9.SlotDanceInfo:new()
v_u_9.new = function(_) --[[ Name: new ]] --[[ Line: 86 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_1, (copy 3): v_u_24, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_5 ]]
    local v25 = {
        ["Type"] = v_u_9.Type
    }
    local v_u_26 = v_u_1:new()
    v25.add_slot_slotdanceinfo = function(_, p27, p28) --[[ Name: add_slot_slotdanceinfo ]] --[[ Line: 92 ]]
        --[[ Upvalues: (copy 1): v_u_26 ]]
        v_u_26:add(p27, p28)
    end;
    v25.get_danceids_for_slot_and_type = function(_, p29, p30) --[[ Name: get_danceids_for_slot_and_type ]] --[[ Line: 96 ]]
        --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_24 ]]
        if v_u_26:contains(p29) then
            return v_u_26:get(p29):get_danceids_for_type(p30);
        else
            return v_u_24:get_danceids_for_type(p30);
        end;
    end;
    v25.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_26, (ref 3): v_u_9, (ref 4): v_u_24 ]]
        local v31 = {}
        for v32 = v_u_6.SLOT_MIN, v_u_6.SLOT_MAX do
            if v_u_26:contains(v32) then
                v31[v_u_9:key_for_slot(v32)] = v_u_26:get(v32):to_table()
            else
                v31[v_u_9:key_for_slot(v32)] = v_u_24:to_table()
            end;
        end;
        return v31;
    end;
    v25.add_playerblob_to_slot = function(p33, p34, p35) --[[ Name: add_playerblob_to_slot ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_7, (ref 3): v_u_5 ]]
        local v36 = v_u_9.SlotDanceInfo:new()
        if p34 ~= nil then
            for v37, v38 in v_u_7:get_owned_danceid_to_equipped_dict(p34):key_itr() do
                if v38 then
                    v36:add_type_danceid(v_u_5:singleton():get_dance_type_for_id(v37), v37)
                end;
            end;
        end;
        p33:add_slot_slotdanceinfo(p35, v36)
    end;
    return v25;
end;
v_u_9.from_table = function(_, p39) --[[ Name: from_table ]] --[[ Line: 134 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_6 ]]
    local v40 = v_u_9:new()
    for v41 = v_u_6.SLOT_MIN, v_u_6.SLOT_MAX do
        v40:add_slot_slotdanceinfo(v41, v_u_9.SlotDanceInfo:from_table(p39[v_u_9:key_for_slot(v41)]))
    end;
    return v40;
end;
return v_u_9;
