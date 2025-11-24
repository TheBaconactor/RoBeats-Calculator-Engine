-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.MarketplaceSale)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Shared.GuildData)
local v_u_7 = require(game.ReplicatedStorage.Shared.GuildBonusUtil)
local v_u_43 = {
    ["get_player_max_sale_count"] = function(_) --[[ Name: get_player_max_sale_count ]] --[[ Line: 16 ]]
        return 8;
    end,
    ["get_sale_create_cost_for_playerblob_and_day_and_week"] = function(_, p8, p9, p10) --[[ Name: get_sale_create_cost_for_playerblob_and_day_and_week ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_4, (copy 3): v_u_6 ]]
        if v_u_7:playerblob_is_bonus_id_active_for_weekid(p8, v_u_7.BonusType.FreeMarketplaceSales, p10) then
            return 0, v_u_4.CurrencyType.Stars;
        else
            local v11 = v_u_6:playerblob_has_vip_for_current_day(p8, p9)
            local v12 = #p8.MarketSales
            if v11 then
                if v12 < 4 then
                    return 0, v_u_4.CurrencyType.Stars;
                else
                    return 1, v_u_4.CurrencyType.Stars;
                end;
            elseif v12 < 4 then
                return 1, v_u_4.CurrencyType.Stars;
            else
                return 2, v_u_4.CurrencyType.Stars;
            end;
        end;
    end,
    ["playerblob_add_sale"] = function(_, p13, p14) --[[ Name: playerblob_add_sale ]] --[[ Line: 55 ]]
        p13.MarketSales[#p13.MarketSales + 1] = p14:to_table()
    end,
    ["playerblob_has_any_sales"] = function(_, p15) --[[ Name: playerblob_has_any_sales ]] --[[ Line: 59 ]]
        return #p15.MarketSales > 0;
    end,
    ["get_sales_list_from_playerblob"] = function(_, p16, p17, p18) --[[ Name: get_sales_list_from_playerblob ]] --[[ Line: 61 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5, (copy 3): v_u_3 ]]
        if #p16.MarketSales == 0 then
            return v_u_2:new();
        end;
        local v19 = v_u_2:new()
        for v20 = 1, #p16.MarketSales do
            local v21 = v_u_5:from_table(p16.MarketSales[v20])
            if v_u_3:singleton():contains_material(v21:get_materialid()) then
                v21:set_seller_name(p17)
                v21:set_seller_id(p18)
                v19:push_back(v21)
            end;
        end;
        return v19;
    end,
    ["playerblob_remove_sale_index"] = function(_, p22, p23) --[[ Name: playerblob_remove_sale_index ]] --[[ Line: 86 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        for v24 = #p22.MarketSales, 1, -1 do
            if v_u_5:from_table(p22.MarketSales[v24]):get_index() == p23 then
                table.remove(p22.MarketSales, v24)
            end;
        end;
    end,
    ["sales_list_to_table"] = function(_, p25) --[[ Name: sales_list_to_table ]] --[[ Line: 95 ]]
        local v26 = {}
        for v27 = 1, p25:count() do
            v26[#v26 + 1] = p25:get(v27):to_table()
        end;
        return v26;
    end,
    ["sales_table_to_list"] = function(_, p28) --[[ Name: sales_table_to_list ]] --[[ Line: 103 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5 ]]
        local v29 = v_u_2:new()
        for v30 = 1, #p28 do
            v29:push_back(v_u_5:from_table(p28[v30]))
        end;
        return v29;
    end,
    ["playerblob_has_any_purchased_sales"] = function(_, p31) --[[ Name: playerblob_has_any_purchased_sales ]] --[[ Line: 111 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        local v32 = false
        for v33 = 1, #p31.MarketSales do
            if v_u_5:from_table(p31.MarketSales[v33]):get_purchased() == true then
                v32 = true
            end;
        end;
        return v32;
    end,
    ["playerblob_claim_purchased_sales"] = function(_, p34) --[[ Name: playerblob_claim_purchased_sales ]] --[[ Line: 122 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5, (copy 3): v_u_4 ]]
        local v35 = v_u_2:new()
        for v36 = #p34.MarketSales, 1, -1 do
            local v37 = v_u_5:from_table(p34.MarketSales[v36])
            if v37:get_purchased() == true then
                v_u_4:set_coin_currency(p34, v_u_4:get_coin_currency(p34) + v37:get_price())
                v35:push_back(v37)
                table.remove(p34.MarketSales, v36)
            end;
        end;
        return v35;
    end,
    ["playerblob_mark_sale_index_as_purchased_by"] = function(_, p38, p39, p40) --[[ Name: playerblob_mark_sale_index_as_purchased_by ]] --[[ Line: 135 ]]
        local v41 = false
        for v42 = 1, #p38.MarketSales do
            local l_MarketSales_0 = p38.MarketSales[v42]
            if l_MarketSales_0.Index == p39 and l_MarketSales_0.Purchased == false then
                l_MarketSales_0.Purchased = true
                l_MarketSales_0.PurchasedBy = p40
                return true;
            end;
        end;
        return v41;
    end
}
v_u_43.playerblob_get_next_available_sale_id = function(_, p44) --[[ Name: playerblob_get_next_available_sale_id ]] --[[ Line: 39 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_43 ]]
    local v45 = v_u_1:new()
    local v46 = v_u_43:get_sales_list_from_playerblob(p44, "", -1)
    local v47 = -1
    for v48 = 1, v46:count() do
        v45:add(v46:get(v48):get_index(), true)
    end;
    for v49 = 1, v_u_43:get_player_max_sale_count() do
        if v45:contains(v49) ~= true then
            return v49;
        end;
    end;
    return v47;
end;
v_u_43.playerblob_get_sale_index = function(_, p50, p51) --[[ Name: playerblob_get_sale_index ]] --[[ Line: 75 ]]
    --[[ Upvalues: (copy 1): v_u_43 ]]
    local v52 = v_u_43:get_sales_list_from_playerblob(p50, "", p50.UserId)
    for v53 = 1, v52:count() do
        local v54 = v52:get(v53)
        if v54:get_index() == p51 then
            return v54;
        end;
    end;
    return nil;
end;
return v_u_43;
