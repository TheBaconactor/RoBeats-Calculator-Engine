-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.VArg)
local v_u_3 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_4 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_45 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_7, (copy 4): v_u_2 ]]
        local v8 = {}
        local v_u_9 = v_u_1:new()
        local v_u_10 = 0
        local v_u_11 = false
        v8.to_string = function(_) --[[ Name: to_string ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_9, (ref 3): v_u_4 ]]
            local v12 = string.format("%d coins,", v_u_10)
            for v13, v14 in v_u_9:key_itr() do
                v12 = v12 .. string.format("%s x%d,", v_u_4:singleton():get_material_name(v13), v14)
            end;
            return v12;
        end;
        v8.clear = function(_) --[[ Name: clear ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11 ]]
            v_u_9:clear()
            v_u_10 = 0
            v_u_11 = false
        end;
        v8.update_from_table = function(_, p15) --[[ Name: update_from_table ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_9, (ref 5): v_u_1, (ref 6): v_u_2, (ref 7): v_u_4 ]]
            v_u_7:is_int_greater_than(p15.Coins, -1)
            v_u_7:is_bool(p15.Accepted)
            local v16 = v_u_10 ~= p15.Coins
            v_u_10 = p15.Coins
            v_u_11 = p15.Accepted
            local v17 = v_u_9
            local v18 = v_u_1:new()
            for v19, v20 in pairs((v_u_2:sparse_array_deconvert(p15.Materials))) do
                v_u_7:is_true(v_u_4:singleton():get_material(v19) ~= nil)
                v_u_7:is_int_greater_than(v20, -1)
                v18:add(v19, v20)
                if v20 ~= v17:get(v19) then
                    v16 = true
                end;
            end;
            local v21 = v17:count() ~= v18:count() and true or v16
            v_u_9 = v18
            return v21;
        end;
        v8.update_accepted_from_table = function(_, p22) --[[ Name: update_accepted_from_table ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p22.Accepted
        end;
        v8.export_to_table = function(_, _) --[[ Name: export_to_table ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_2 ]]
            local v23 = {}
            for v24, v25 in v_u_9:key_itr() do
                v23[v24] = v25
            end;
            return {
                ["Coins"] = v_u_10,
                ["Accepted"] = v_u_11,
                ["Materials"] = v_u_2:sparse_array_convert(v23)
            };
        end;
        v8.add_material = function(_, p26) --[[ Name: add_material ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            if v_u_9:contains(p26) then
                v_u_9:add(p26, v_u_9:get(p26) + 1)
            else
                v_u_9:add(p26, 1)
            end;
        end;
        v8.remove_material = function(_, p27) --[[ Name: remove_material ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            if v_u_9:contains(p27) then
                local v28 = v_u_9:get(p27)
                if v28 == 1 then
                    v_u_9:remove(p27)
                    return;
                end;
                v_u_9:add(p27, v28 - 1)
            end;
        end;
        v8.get_count_of_material_id = function(_, p29) --[[ Name: get_count_of_material_id ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return not v_u_9:contains(p29) and 0 or v_u_9:get(p29);
        end;
        v8.get_materials_dict = function(_) --[[ Name: get_materials_dict ]] --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v8.set_coins = function(_, p30) --[[ Name: set_coins ]] --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            v_u_10 = p30
        end;
        v8.get_coins = function(_) --[[ Name: get_coins ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end;
        v8.set_accepted = function(_, p31) --[[ Name: set_accepted ]] --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p31
        end;
        v8.get_accepted = function(_) --[[ Name: get_accepted ]] --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        v8.can_add_material = function(p32, p33) --[[ Name: can_add_material ]] --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return p32:get_count_of_material_id(p33) > 0 and true or v_u_9:count() < 6;
        end;
        return v8;
    end,
    ["get_material_id_playerblob_remaining_count"] = function(_, p34, p35, p36) --[[ Name: get_material_id_playerblob_remaining_count ]] --[[ Line: 123 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        return v_u_3:get_count_of_material(p36, p35) - p34:get_count_of_material_id(p35);
    end,
    ["add_to_playerblob"] = function(_, p37, p38) --[[ Name: add_to_playerblob ]] --[[ Line: 152 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5, (copy 3): v_u_3 ]]
        if p37:get_coins() < 0 then
            v_u_6:errf("ActiveTradeOffer:add_to_playerblob coin_currency negative")
        end;
        v_u_5:set_coin_currency(p38, v_u_5:get_coin_currency(p38) + p37:get_coins())
        for v39, v40 in p37:get_materials_dict():key_itr() do
            if v40 < 0 then
                v_u_6:errf("ActiveTradeOffer:trade_materials material_count negative")
            end;
            v_u_3:add_crafting_materials_of_id(p38, v39, v40)
        end;
    end,
    ["remove_from_playerblob"] = function(_, p41, p42) --[[ Name: remove_from_playerblob ]] --[[ Line: 167 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5, (copy 3): v_u_3 ]]
        if p41:get_coins() < 0 then
            v_u_6:errf("ActiveTradeOffer:remove_from_playerblob coin_currency negative ")
        end;
        v_u_5:set_coin_currency(p42, v_u_5:get_coin_currency(p42) - p41:get_coins())
        for v43, v44 in p41:get_materials_dict():key_itr() do
            if v44 < 0 then
                v_u_6:errf("ActiveTradeOffer:remove_from_playerblob material_count negative")
            end;
            v_u_3:add_crafting_materials_of_id(p42, v43, -v44)
        end;
    end
}
v_u_45.validate_to_playerblob = function(_, p46, p47) --[[ Name: validate_to_playerblob ]] --[[ Line: 129 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_5, (copy 3): v_u_4, (copy 4): v_u_45 ]]
    v_u_7:is_int(p46:get_coins())
    if v_u_5:get_coin_currency(p47) < p46:get_coins() then
        return false;
    end;
    if p46:get_coins() < 0 then
        return false;
    end;
    for v48, v49 in p46:get_materials_dict():key_itr() do
        v_u_7:is_int(v49)
        v_u_7:is_true(v_u_4:singleton():get_material(v48) ~= nil)
        v_u_7:is_true(v_u_4:singleton():is_material_tradeable(v48))
        if v_u_45:get_material_id_playerblob_remaining_count(p46, v48, p47) < 0 then
            return false;
        end;
        if v49 < 0 then
            return false;
        end;
    end;
    return true;
end;
return v_u_45;
