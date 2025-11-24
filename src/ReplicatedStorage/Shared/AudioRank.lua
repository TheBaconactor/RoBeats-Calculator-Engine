-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:02 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
local v3 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
local v4 = require(game.ReplicatedStorage.Shared.BuildConfig)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
v5:require_shared(function() --[[ Line: 9 ]]
    --[[ Upvalues: (ref 1): v_u_6 ]]
    v_u_6 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
end)
local v_u_7 = {
    ["RankF"] = 0,
    ["RankD"] = 5,
    ["RankDPlus"] = 6,
    ["RankC"] = 1,
    ["RankCPlus"] = 7,
    ["RankB"] = 2,
    ["RankBPlus"] = 8,
    ["RankA"] = 3,
    ["RankAPlus"] = 4,
    ["RankS"] = 9
}
local v8 = v2:new({
    v_u_7.RankF,
    v_u_7.RankD,
    v_u_7.RankDPlus,
    v_u_7.RankC,
    v_u_7.RankCPlus,
    v_u_7.RankB,
    v_u_7.RankBPlus,
    v_u_7.RankA,
    v_u_7.RankAPlus,
    v_u_7.RankS
})
local v_u_9 = v2:new()
local v_u_10 = v_u_6
local v_u_11 = {
    ["Value"] = {
        ["RankF"] = 0,
        ["RankD"] = 5,
        ["RankDPlus"] = 6,
        ["RankC"] = 1,
        ["RankCPlus"] = 7,
        ["RankB"] = 2,
        ["RankBPlus"] = 8,
        ["RankA"] = 3,
        ["RankAPlus"] = 4,
        ["RankS"] = 9
    }
}
for v12 = v8:count(), 1, -1 do
    v_u_9:push_back(v8:get(v12))
end;
local v_u_13 = v1:new({
    [v_u_7.RankF] = 0,
    [v_u_7.RankD] = 0.3,
    [v_u_7.RankDPlus] = 0.425,
    [v_u_7.RankC] = 0.575,
    [v_u_7.RankCPlus] = 0.65,
    [v_u_7.RankB] = 0.75,
    [v_u_7.RankBPlus] = 0.815,
    [v_u_7.RankA] = 0.875,
    [v_u_7.RankAPlus] = 0.955,
    [v_u_7.RankS] = 0.975
})
if v4:is_dev_build() then
    local v14 = -1
    for _, v15 in v8:key_itr() do
        local v16 = v_u_13:get(v15)
        v3:is_true(v16 < 1)
        v3:is_true(v14 < v16)
        v14 = v16
    end;
end;
v_u_11.rank_value_to_accuracy = function(_, p17) --[[ Name: rank_value_to_accuracy ]] --[[ Line: 70 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return not v_u_13:contains(p17) and 0 or v_u_13:get(p17);
end;
v_u_11.accuracy_to_rank_value = function(_, p18) --[[ Name: accuracy_to_rank_value ]] --[[ Line: 78 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_9, (copy 3): v_u_11 ]]
    local l_RankF_0 = v_u_7.RankF
    for v19 = 1, v_u_9:count() do
        local v20 = v_u_9:get(v19)
        if v_u_11:rank_value_to_accuracy(v20) <= p18 then
            return v20;
        end;
    end;
    return l_RankF_0;
end;
local v_u_21 = v1:new()
for v22, v23 in v8:key_itr() do
    v_u_21:add(v23, v22 - 1)
end;
v_u_11.rank_value_to_index = function(_, p24) --[[ Name: rank_value_to_index ]] --[[ Line: 96 ]]
    --[[ Upvalues: (copy 1): v_u_21 ]]
    return not v_u_21:contains(p24) and 1 or v_u_21:get(p24);
end;
local v_u_25 = v1:new()
for v26, v27 in v_u_21:key_itr() do
    v_u_25:add(v27, v26)
end;
v_u_11.contains_index = function(_, p28) --[[ Name: contains_index ]] --[[ Line: 107 ]]
    --[[ Upvalues: (copy 1): v_u_25 ]]
    return v_u_25:contains(p28);
end;
v_u_11.index_to_rank_value = function(_, p29) --[[ Name: index_to_rank_value ]] --[[ Line: 109 ]]
    --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_7 ]]
    if v_u_25:contains(p29) then
        return v_u_25:get(p29);
    else
        return v_u_7.RankF;
    end;
end;
local v_u_30 = v1:new({
    [v_u_7.RankF] = "F",
    [v_u_7.RankD] = "D",
    [v_u_7.RankDPlus] = "D+",
    [v_u_7.RankC] = "C",
    [v_u_7.RankCPlus] = "C+",
    [v_u_7.RankB] = "B",
    [v_u_7.RankBPlus] = "B+",
    [v_u_7.RankA] = "A",
    [v_u_7.RankAPlus] = "A+",
    [v_u_7.RankS] = "S"
})
v_u_11.get_rank_value_name = function(_, p31) --[[ Name: get_rank_value_name ]] --[[ Line: 129 ]]
    --[[ Upvalues: (copy 1): v_u_30 ]]
    return not v_u_30:contains(p31) and "?" or v_u_30:get(p31);
end;
local v_u_32 = v1:new({
    [v_u_7.RankF] = "rbxassetid://11275727092",
    [v_u_7.RankD] = "rbxassetid://11275727440",
    [v_u_7.RankDPlus] = "rbxassetid://11275727217",
    [v_u_7.RankC] = "rbxassetid://11275727710",
    [v_u_7.RankCPlus] = "rbxassetid://11275727586",
    [v_u_7.RankB] = "rbxassetid://11275727925",
    [v_u_7.RankBPlus] = "rbxassetid://11275727812",
    [v_u_7.RankA] = "rbxassetid://11275728175",
    [v_u_7.RankAPlus] = "rbxassetid://11275728035",
    [v_u_7.RankS] = "rbxassetid://11343449473"
})
v_u_11.get_rank_value_icon = function(_, p33) --[[ Name: get_rank_value_icon ]] --[[ Line: 149 ]]
    --[[ Upvalues: (copy 1): v_u_32, (ref 2): v_u_10 ]]
    if v_u_32:contains(p33) then
        return v_u_32:get(p33);
    else
        return v_u_10:get_question_assetid();
    end;
end;
return v_u_11;
