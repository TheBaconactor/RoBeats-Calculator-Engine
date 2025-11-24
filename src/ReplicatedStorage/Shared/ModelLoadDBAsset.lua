-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Time elapsed: 15 milliseconds

local v1 = require(game.ReplicatedStorage.Shared.SPList)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
local v3 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = v3:new()
local v_u_6 = v2:new()
local v_u_7 = v2:new()
local v_u_8 = v2:new()
local v_u_9 = v2:new()
local v10 = 1
local v_u_11 = {
    ["Category"] = {}
}
local v12 = {}
for v13, v14 in pairs({
    ["Accessory"] = {},
    ["PetNPC"] = {},
    ["GameStage"] = {},
    ["NPC"] = {},
    ["LobbyDecoration"] = {}
}) do
    local v15 = v2:new()
    local v16 = {}
    for _, v17 in v1:new(v14):key_itr() do
        local v18 = v10 + 1
        v16[v17] = v10
        v_u_5:push_back_to(v13, v10)
        v_u_6:add(v10, v17)
        v4:is_true(v15:contains(v17) == false)
        v15:add(v17, v10)
        v_u_9:add(v10, v16)
        v10 = v18
    end;
    v_u_7:add(v13, v15)
    v_u_11[v13] = v16
    v12[v13] = v13
    v_u_8:add(v16, v13)
end;
v_u_11.get_categories_to_ids = function(_) --[[ Name: get_categories_to_ids ]] --[[ Line: 388 ]]
    --[[ Upvalues: (copy 1): v_u_5 ]]
    return v_u_5;
end;
v_u_11.get_id_to_name = function(_) --[[ Name: get_id_to_name ]] --[[ Line: 391 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6;
end;
v_u_11.get_category_name_to_id = function(_, p19) --[[ Name: get_category_name_to_id ]] --[[ Line: 394 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    return v_u_7:get(p19);
end;
v_u_11.get_category_table_to_name = function(_) --[[ Name: get_category_table_to_name ]] --[[ Line: 397 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    return v_u_8;
end;
v_u_11.get_id_category_table = function(_, p20) --[[ Name: get_id_category_table ]] --[[ Line: 399 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    return v_u_9:get(p20);
end;
v_u_11.get_category_table_and_name_to_id = function(_, p21, p22) --[[ Name: get_category_table_and_name_to_id ]] --[[ Line: 402 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    local v23 = v_u_11:get_category_table_to_name():get(p21)
    if v23 == nil then
        return nil;
    else
        return v_u_11:get_category_name_to_id(v23):get(p22);
    end;
end;
return v_u_11;
