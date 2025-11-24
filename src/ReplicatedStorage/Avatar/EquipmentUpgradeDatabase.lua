-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Avatar.EquipmentUpgradeBase)
local v_u_5 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradesSet1)
local v_u_7 = {}
v_u_7.new = function(_) --[[ Name: new ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_2, (copy 4): v_u_5, (copy 5): v_u_3, (copy 6): v_u_7, (copy 7): v_u_4 ]]
    local v_u_10 = {
        ["upgrade_count_can_upgrade"] = function(_, p8) --[[ Name: upgrade_count_can_upgrade ]] --[[ Line: 58 ]]
            return p8 < 15;
        end,
        ["get_max_safe_upgrade_count"] = function(_) --[[ Name: get_max_safe_upgrade_count ]] --[[ Line: 62 ]]
            return 5;
        end,
        ["get_upgrade_boost_material_id"] = function(_) --[[ Name: get_upgrade_boost_material_id ]] --[[ Line: 68 ]]
            return 32;
        end,
        ["get_upgrade_boost_untradeable_material_id"] = function(_) --[[ Name: get_upgrade_boost_untradeable_material_id ]] --[[ Line: 69 ]]
            return 294;
        end,
        ["get_upgrade_protect_material_id"] = function(_) --[[ Name: get_upgrade_protect_material_id ]] --[[ Line: 70 ]]
            return 33;
        end,
        ["get_upgrade_protect_untradeable_material_id"] = function(_) --[[ Name: get_upgrade_protect_untradeable_material_id ]] --[[ Line: 71 ]]
            return 295;
        end,
        ["get_upgrade_cleaner_material_id"] = function(_) --[[ Name: get_upgrade_cleaner_material_id ]] --[[ Line: 72 ]]
            return 148;
        end,
        ["get_upgrade_boost_max_count"] = function(_) --[[ Name: get_upgrade_boost_max_count ]] --[[ Line: 73 ]]
            return 5;
        end,
        ["get_boost_upgrade_success_lt_d100_roll_for_upgrade_count"] = function(_, p9) --[[ Name: get_boost_upgrade_success_lt_d100_roll_for_upgrade_count ]] --[[ Line: 75 ]]
            return p9 == 5 and 75 or (p9 == 6 and 45 or (p9 == 7 and 25 or (p9 == 8 and 15 or (p9 == 9 and 10 or (p9 == 10 and 5 or (p9 == 11 and 4 or (p9 == 12 and 3 or (p9 == 13 and 2.5 or (p9 == 14 and 2 or 1)))))))));
        end
    }
    local v_u_11 = v_u_1:new()
    local function _() --[[ Name: cons ]] --[[ Line: 19 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_10 ]]
        v_u_6:add_to_equipment_upgrade_database(v_u_10)
    end;
    v_u_10.add_equipment_upgrade = function(_, p12, p13) --[[ Name: add_equipment_upgrade ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_11, (ref 2): v_u_2, (ref 3): v_u_5, (ref 4): v_u_3 ]]
        if v_u_11:contains(p12) then
            v_u_2:errf("EquipmentUpgradeDatabase:add_equipment_upgrade duplicate id(%d)", p12)
        end;
        for v14, v15 in pairs(p13:get_gear_statmodifierobj()) do
            if v_u_5:is_valid_type(v14) ~= true then
                v_u_2:errf("EquipmentUpgradeDatabase:add_equipment_upgrade get_gear_statmodifierobj k invalid")
            end;
            if typeof(v15) ~= "number" then
                v_u_2:errf("EquipmentUpgradeDatabase:add_equipment_upgrade get_gear_statmodifierobj v invalid")
            end;
        end;
        for v16, v17 in pairs(p13:get_craft_materials()) do
            if v_u_3:singleton():get_material(v16) == nil then
                v_u_2:errf("EquipmentUpgradeDatabase:get_craft_materials get_gear_statmodifierobj k invalid")
            end;
            if typeof(v17) ~= "number" then
                v_u_2:errf("EquipmentUpgradeDatabase:get_craft_materials get_gear_statmodifierobj v invalid")
            end;
        end;
        v_u_11:add(p12, p13)
    end;
    v_u_10.get_equipment_upgrade_for_id = function(_, p18) --[[ Name: get_equipment_upgrade_for_id ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        return v_u_11:get(p18);
    end;
    v_u_10.equipment_upgrade_id_list = function(_) --[[ Name: equipment_upgrade_id_list ]] --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        return v_u_11:key_list();
    end;
    v_u_10.get_requirements_dict_for_id = function(p19, p20) --[[ Name: get_requirements_dict_for_id ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v21 = v_u_1:new()
        local v22 = p19:get_equipment_upgrade_for_id(p20)
        if v22 ~= nil then
            v21:clear()
            for v23, v24 in pairs(v22:get_craft_materials()) do
                v21:add(v23, v24)
            end;
            return v21;
        end;
    end;
    v_u_10.upgrade_count_can_safe_upgrade = function(_, p25) --[[ Name: upgrade_count_can_safe_upgrade ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return p25 < v_u_7:singleton():get_max_safe_upgrade_count();
    end;
    v_u_10.get_pity_boost_upgrade_success_lt_d100_roll_for_upgrade_count = function(_, p26) --[[ Name: get_pity_boost_upgrade_success_lt_d100_roll_for_upgrade_count ]] --[[ Line: 101 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return v_u_7:singleton():get_boost_upgrade_success_lt_d100_roll_for_upgrade_count(p26) * 0.25;
    end;
    v_u_10.get_boost_upgrade_success_lt_d100_roll_for_upgrade_count_and_boost_count = function(_, p27, p28, p29) --[[ Name: get_boost_upgrade_success_lt_d100_roll_for_upgrade_count_and_boost_count ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4 ]]
        local v30 = p29 == nil and 0 or p29
        local v31 = v_u_7:singleton():get_boost_upgrade_success_lt_d100_roll_for_upgrade_count(p27)
        local v32 = v31
        for _ = 1, p28 do
            v31 = v_u_4:clamp(v31 + v32, 0, 100)
        end;
        local v33 = v30 * v_u_7:singleton():get_pity_boost_upgrade_success_lt_d100_roll_for_upgrade_count(p27)
        return v_u_4:clamp(v31 + v33, 0, 100), v33;
    end;
    v_u_10.get_upgrade_info = function(_) --[[ Name: get_upgrade_info ]] --[[ Line: 120 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        local v34 = {}
        for v35, v36 in v_u_11:key_itr() do
            v34[#v34 + 1] = {
                ["upgrade_id"] = v35,
                ["name"] = v36:get_name()
            }
        end;
        return v34;
    end;
    v_u_6:add_to_equipment_upgrade_database(v_u_10)
    return v_u_10;
end;
local v_u_37 = v_u_7:new()
v_u_7.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 136 ]]
    --[[ Upvalues: (copy 1): v_u_37 ]]
    return v_u_37;
end;
return v_u_7;
