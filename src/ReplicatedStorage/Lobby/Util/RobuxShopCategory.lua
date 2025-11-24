-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:59 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.PlayerInfo.SaleInfo)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v4 = {
    ["CoinsAndStars"] = 1,
    ["Upgrade"] = 2,
    ["Craft"] = 3,
    ["Minis"] = 4,
    ["Packs"] = 5
}
local v_u_5 = v_u_3:new():add_table({
    [v4.CoinsAndStars] = "Coins & Stars",
    [v4.Upgrade] = "Upgrades",
    [v4.Craft] = "Crafting",
    [v4.Minis] = "Minis",
    [v4.Packs] = "Packs"
})
v4.category_to_name = function(_, p6) --[[ Name: category_to_name ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_5 ]]
    return v_u_5:get(p6);
end;
local v_u_7 = v_u_3:new():add_table({
    [v4.CoinsAndStars] = "rbxassetid://10529208603",
    [v4.Upgrade] = "rbxassetid://10529208772",
    [v4.Craft] = "rbxassetid://10529209016",
    [v4.Minis] = "rbxassetid://10531119310",
    [v4.Packs] = "rbxassetid://10529209322"
})
v4.category_to_icon = function(_, p8) --[[ Name: category_to_icon ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    return v_u_7:get(p8);
end;
local v9 = v_u_3:new()
local v10 = {
    [l_CoinsAndStars_0] = v11:push_back_table_list(v12),
    [l_Upgrade_0] = v13:push_back_table_list(v14),
    [l_Craft_0] = v15:push_back_table_list(v16),
    [l_Minis_0] = v17:push_back_table_list(v18),
    [l_Packs_0] = v19:push_back_table_list(v20)
}
local l_CoinsAndStars_0 = v4.CoinsAndStars
local v11 = v_u_2:new()
local v12 = {
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Coin1_V3),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Coin2_V3),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Coin3_V3),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Coin4_V3),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Star1_V3),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Star2_V3),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Star3_V3),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Star4_V3)
}
local l_Upgrade_0 = v4.Upgrade
local v13 = v_u_2:new()
local v14 = {
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeBoost_5),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeBoost_20),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeBoost_50),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeBoost_100),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeProtect_5),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeProtect_20),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeProtect_50),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_UpgradeProtect_100)
}
local l_Craft_0 = v4.Craft
local v15 = v_u_2:new()
local v16 = {
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_GemBox_10),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_GemBox_30),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_GemBox_100),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_GemBox_225),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_TokenBox_1),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_TokenBox_5),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_TokenBox_10),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_TokenBox_20)
}
local l_Minis_0 = v4.Minis
local v17 = v_u_2:new()
local v18 = {
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini2StarBox_1),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini2StarBox_5),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini2StarBox_15),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini2StarBox_35),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini1StarBox_5),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini1StarBox_15),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini1StarBox_40),
    v_u_1:get_info_data_for_productid(v_u_1.ProductID_Mini1StarBox_80)
}
local l_Packs_0 = v4.Packs
local v19 = v_u_2:new()
local v20 = { v_u_1:get_info_data_for_productid(v_u_1.ProductID_StarterPack_V3), v_u_1:get_info_data_for_productid(v_u_1.ProductID_CoinPack_V3), v_u_1:get_info_data_for_productid(v_u_1.ProductID_StarPack_V3) }
local v_u_21 = v9:add_table(v10)
v4.generate_category_to_product_info_data_dict_for_day_event_list = function(_, p22) --[[ Name: generate_category_to_product_info_data_dict_for_day_event_list ]] --[[ Line: 90 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_21, (copy 3): v_u_2, (copy 4): v_u_1 ]]
    local v23 = v_u_3:new()
    for v24, v25 in v_u_21:key_itr() do
        local v26 = v_u_2:new()
        v23:add(v24, v26)
        for _, v27 in v25:key_itr() do
            local v28 = false
            for _, v29 in v_u_1:get_id_to_copy_target_info_data_mdict():list_of(v27:get_product_id()):key_itr() do
                local v30, v31 = v29:requires_day_event()
                local v32, v33 = v29:requires_day_event_param2()
                if v30 then
                    local v34, v35 = p22:is_event_type_active(v31)
                    if v34 and (v32 == true and v35 == v33 or v32 == false) then
                        v26:push_back(v29)
                        v28 = true
                    end;
                end;
            end;
            if v28 == false then
                v26:push_back(v27)
            end;
        end;
    end;
    return v23;
end;
v4.is_category_to_product_info_data_dict_category_matching_default = function(_, p36, p37) --[[ Name: is_category_to_product_info_data_dict_category_matching_default ]] --[[ Line: 124 ]]
    --[[ Upvalues: (copy 1): v_u_21 ]]
    local v38 = p36:get(p37)
    local v39 = v_u_21:get(p37)
    if v38 == nil or v39 == nil then
        return false;
    end;
    if v38:count() ~= v39:count() then
        return false;
    end;
    for v40 = 1, v39:count() do
        if v38:get(v40) ~= v39:get(v40) then
            return false;
        end;
    end;
    return true;
end;
return v4;
