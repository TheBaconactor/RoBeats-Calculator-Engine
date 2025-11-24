-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_19 = {
    ["new"] = function(_, p_u_4, p_u_5, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_1 ]]
        v_u_2:is_int_greater_than(p_u_4, 0)
        v_u_2:is_true(v_u_3:singleton():get_material(p_u_5) ~= nil)
        v_u_2:is_int_greater_than(p_u_6, 0)
        v_u_2:is_int(p_u_7)
        v_u_2:is_int_greater_than(p_u_6, 0)
        v_u_2:is_bool(p_u_9)
        v_u_2:is_string(p_u_10)
        local v11 = {}
        v11.get_index = function(_) --[[ Name: get_index ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_4 ]]
            return p_u_4;
        end;
        v11.get_materialid = function(_) --[[ Name: get_materialid ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_5 ]]
            return p_u_5;
        end;
        v11.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): p_u_6 ]]
            return p_u_6;
        end;
        v11.get_start_date = function(_) --[[ Name: get_start_date ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            return p_u_7;
        end;
        v11.get_price = function(_) --[[ Name: get_price ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8;
        end;
        v11.get_purchased = function(_) --[[ Name: get_purchased ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): p_u_9 ]]
            return p_u_9;
        end;
        v11.get_purchased_by = function(_) --[[ Name: get_purchased_by ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): p_u_10 ]]
            return p_u_10;
        end;
        v11.set_purchased = function(_, p12) --[[ Name: set_purchased ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_9 ]]
            v_u_2:is_bool(p12)
            p_u_9 = p12
        end;
        v11.set_purchased_by = function(_, p13) --[[ Name: set_purchased_by ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_10 ]]
            v_u_2:is_string(p13)
            p_u_10 = p13
        end;
        local v_u_14 = ""
        local v_u_15 = 103972519
        v11.get_seller_name = function(_) --[[ Name: get_seller_name ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        v11.get_seller_id = function(_) --[[ Name: get_seller_id ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        v11.set_seller_name = function(_, p16) --[[ Name: set_seller_name ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_14 ]]
            v_u_2:is_string(v_u_14)
            v_u_14 = p16
        end;
        v11.set_seller_id = function(_, p17) --[[ Name: set_seller_id ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_15 ]]
            v_u_2:is_int(p17)
            v_u_15 = p17
        end;
        v11.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 59 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): p_u_5, (copy 3): p_u_6, (copy 4): p_u_7, (copy 5): p_u_8, (ref 6): p_u_9, (ref 7): p_u_10, (ref 8): v_u_14, (ref 9): v_u_15 ]]
            return {
                ["Index"] = p_u_4,
                ["MaterialID"] = p_u_5,
                ["Count"] = p_u_6,
                ["StartDate"] = p_u_7,
                ["Price"] = p_u_8,
                ["Purchased"] = p_u_9,
                ["PurchasedBy"] = p_u_10,
                ["SellerName"] = v_u_14,
                ["SellerID"] = v_u_15
            };
        end;
        v11.to_str = function(p18) --[[ Name: to_str ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            return v_u_1:table_to_string(p18:to_table());
        end;
        return v11;
    end
}
v_u_19.from_table = function(_, p20) --[[ Name: from_table ]] --[[ Line: 81 ]]
    --[[ Upvalues: (copy 1): v_u_19 ]]
    local v21 = v_u_19:new(p20.Index, p20.MaterialID, p20.Count, p20.StartDate, p20.Price, p20.Purchased, p20.PurchasedBy)
    if p20.SellerName ~= nil then
        v21:set_seller_name(p20.SellerName)
    end;
    if p20.SellerID ~= nil then
        v21:set_seller_id(p20.SellerID)
    end;
    return v21;
end;
return v_u_19;
