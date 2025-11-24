-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_8 = require(game.ReplicatedStorage.Pets.PetUtils)
local v12 = {
    ["SortType"] = {
        ["Name"] = 1,
        ["GearPower"] = 2,
        ["Slot"] = 3,
        ["Upgrades"] = 4,
        ["Color"] = 5
    },
    ["owned_data_get_gearpower"] = function(_, p9, p10) --[[ Name: owned_data_get_gearpower ]] --[[ Line: 63 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (copy 3): v_u_1 ]]
        local v11
        if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p10) then
            v11 = v_u_8:playerblob_get_pet_ownedid_gearpower(p9, v_u_8:ownedpet_get_ownedid(p10))
        else
            v11 = v_u_1:playerblob_get_ownedid_gearpower(p9, p10.OwnedID)
        end;
        return v11;
    end
}
local v_u_13 = {
    ["Name"] = 1,
    ["GearPower"] = 2,
    ["Slot"] = 3,
    ["Upgrades"] = 4,
    ["Color"] = 5
}
local l_GearPower_0 = v_u_13.GearPower
v12.get_sort_type = function(_) --[[ Name: get_sort_type ]] --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): l_GearPower_0 ]]
    return l_GearPower_0;
end;
v12.set_sort_type = function(_, p14) --[[ Name: set_sort_type ]] --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): l_GearPower_0 ]]
    l_GearPower_0 = p14
end;
local function f_owned_data_get_name(p15, p16) --[[ Name: owned_data_get_name ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (copy 3): v_u_7, (copy 4): v_u_1, (copy 5): v_u_2 ]]
    if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p16) then
        return v_u_7:singleton():get_data_for_petid((v_u_8:ownedpet_get_petid(p16))):get_name();
    end;
    local v17 = v_u_2:singleton():get_equipment_for_id((v_u_1:playerblob_ownedid_to_equipmentid(p15, p16.OwnedID)))
    return not v17 and "?" or v17:get_name();
end;
v12.owned_data_get_name = function(_, p18, p19) --[[ Name: owned_data_get_name ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): f_owned_data_get_name ]]
    return f_owned_data_get_name(p18, p19);
end;
local function _(p20, p21) --[[ Name: owned_data_get_gearpower ]] --[[ Line: 50 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (copy 3): v_u_1 ]]
    if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p21) then
        return v_u_8:playerblob_get_pet_ownedid_gearpower(p20, v_u_8:ownedpet_get_ownedid(p21));
    else
        return v_u_1:playerblob_get_ownedid_gearpower(p20, p21.OwnedID);
    end;
end;
local function f_owned_data_get_slot(p22, p23) --[[ Name: owned_data_get_slot ]] --[[ Line: 67 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (copy 3): v_u_5, (copy 4): v_u_1, (copy 5): v_u_2 ]]
    if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p23) then
        return v_u_5:get_slot_before_value();
    else
        local v24 = v_u_2:singleton():get_equipment_for_id((v_u_1:playerblob_ownedid_to_equipmentid(p22, p23.OwnedID)))
        if v24 then
            return v24:get_avatar_slot();
        else
            return v_u_5:get_slot_before_value();
        end;
    end;
end;
v12.owned_data_get_slot = function(_, p25, p26) --[[ Name: owned_data_get_slot ]] --[[ Line: 80 ]]
    --[[ Upvalues: (copy 1): f_owned_data_get_slot ]]
    return f_owned_data_get_slot(p25, p26);
end;
local function f_owned_data_get_upgrade_count(p27, p28) --[[ Name: owned_data_get_upgrade_count ]] --[[ Line: 84 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (copy 3): v_u_1 ]]
    return v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p28) and 0 or v_u_1:get_ownedid_upgrade_count(p27, p28.OwnedID);
end;
v12.owned_data_get_upgrade_count = function(_, p29, p30) --[[ Name: owned_data_get_upgrade_count ]] --[[ Line: 91 ]]
    --[[ Upvalues: (copy 1): f_owned_data_get_upgrade_count ]]
    return f_owned_data_get_upgrade_count(p29, p30);
end;
local function f_owned_data_get_color(p31, p32) --[[ Name: owned_data_get_color ]] --[[ Line: 95 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (copy 3): v_u_3, (copy 4): v_u_1 ]]
    if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p32) then
        local v33 = v_u_3:statsdict_base()
        v_u_8:playerblob_apply_pet_ownedid_statsdict(p31, v_u_8:ownedpet_get_ownedid(p32), v33)
        return v_u_3:statsdict_get_ranked_colors(v33):get(1);
    else
        local v34 = v_u_3:statsdict_base()
        v_u_1:playerblob_apply_ownedid_statsdict(p31, p32.OwnedID, v34)
        return v_u_3:statsdict_get_ranked_colors(v34):get(1);
    end;
end;
v12.owned_data_get_color = function(_, p35, p36) --[[ Name: owned_data_get_color ]] --[[ Line: 109 ]]
    --[[ Upvalues: (copy 1): f_owned_data_get_color ]]
    return f_owned_data_get_color(p35, p36);
end;
local function _(_, p37) --[[ Name: owned_data_get_ownedid ]] --[[ Line: 113 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8 ]]
    if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p37) then
        return v_u_8:ownedpet_get_ownedid(p37);
    else
        return p37.OwnedID;
    end;
end;
v12.get_sort_fn_for_playerblob = function(_, p_u_38) --[[ Name: get_sort_fn_for_playerblob ]] --[[ Line: 121 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_4, (copy 3): v_u_8, (copy 4): v_u_1, (ref 5): l_GearPower_0, (copy 6): v_u_13, (copy 7): f_owned_data_get_name, (copy 8): f_owned_data_get_slot, (copy 9): f_owned_data_get_color ]]
    local v_u_39 = v_u_6:new()
    local function _(p40) --[[ Name: cached_gearpower_get ]] --[[ Line: 123 ]]
        --[[ Upvalues: (copy 1): v_u_39, (copy 2): p_u_38, (ref 3): v_u_4, (ref 4): v_u_8, (ref 5): v_u_1 ]]
        local v41 = v_u_39:get(p40)
        if v41 == nil then
            local v42 = p_u_38
            if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p40) then
                v41 = v_u_8:playerblob_get_pet_ownedid_gearpower(v42, v_u_8:ownedpet_get_ownedid(p40))
            else
                v41 = v_u_1:playerblob_get_ownedid_gearpower(v42, p40.OwnedID)
            end;
            v_u_39:add(p40, v41)
        end;
        return v41;
    end;
    local v_u_43 = v_u_6:new()
    local function f_sort_type_val_get(p44) --[[ Name: sort_type_val_get ]] --[[ Line: 133 ]]
        --[[ Upvalues: (copy 1): v_u_43, (ref 2): l_GearPower_0, (ref 3): v_u_13, (ref 4): f_owned_data_get_name, (copy 5): p_u_38, (copy 6): v_u_39, (ref 7): v_u_4, (ref 8): v_u_8, (ref 9): v_u_1, (ref 10): f_owned_data_get_slot, (ref 11): f_owned_data_get_color ]]
        local v45 = v_u_43:get(p44)
        if v45 == nil then
            if l_GearPower_0 == v_u_13.Name then
                v45 = f_owned_data_get_name(p_u_38, p44)
            elseif l_GearPower_0 == v_u_13.GearPower then
                v45 = v_u_39:get(p44)
                if v45 == nil then
                    local v46 = p_u_38
                    if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p44) then
                        v45 = v_u_8:playerblob_get_pet_ownedid_gearpower(v46, v_u_8:ownedpet_get_ownedid(p44))
                    else
                        v45 = v_u_1:playerblob_get_ownedid_gearpower(v46, p44.OwnedID)
                    end;
                    v_u_39:add(p44, v45)
                end;
            elseif l_GearPower_0 == v_u_13.Slot then
                v45 = f_owned_data_get_slot(p_u_38, p44)
            elseif l_GearPower_0 == v_u_13.Upgrades then
                v45 = v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p44) and 0 or v_u_1:get_ownedid_upgrade_count(p_u_38, p44.OwnedID)
            elseif l_GearPower_0 == v_u_13.Color then
                v45 = f_owned_data_get_color(p_u_38, p44)
            elseif v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p44) then
                v45 = v_u_8:ownedpet_get_ownedid(p44)
            else
                v45 = p44.OwnedID
            end;
            v_u_43:add(p44, v45)
        end;
        return v45;
    end;
    local function _(p47, p48, p49) --[[ Name: cmp ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): f_sort_type_val_get, (copy 2): v_u_39, (copy 3): p_u_38, (ref 4): v_u_4, (ref 5): v_u_8, (ref 6): v_u_1 ]]
        local v50 = f_sort_type_val_get(p47)
        local v51 = f_sort_type_val_get(p48)
        if v50 == v51 then
            local v52 = v_u_39:get(p47)
            if v52 == nil then
                local v53 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p47) then
                    v52 = v_u_8:playerblob_get_pet_ownedid_gearpower(v53, v_u_8:ownedpet_get_ownedid(p47))
                else
                    v52 = v_u_1:playerblob_get_ownedid_gearpower(v53, p47.OwnedID)
                end;
                v_u_39:add(p47, v52)
            end;
            local v54 = v_u_39:get(p48)
            if v54 == nil then
                local v55 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p48) then
                    v54 = v_u_8:playerblob_get_pet_ownedid_gearpower(v55, v_u_8:ownedpet_get_ownedid(p48))
                else
                    v54 = v_u_1:playerblob_get_ownedid_gearpower(v55, p48.OwnedID)
                end;
                v_u_39:add(p48, v54)
            end;
            return v54 < v52;
        elseif p49 then
            return v50 < v51;
        else
            return v51 < v50;
        end;
    end;
    return function(p56, p57) --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): l_GearPower_0, (ref 2): v_u_13, (copy 3): f_sort_type_val_get, (copy 4): v_u_39, (copy 5): p_u_38, (ref 6): v_u_4, (ref 7): v_u_8, (ref 8): v_u_1 ]]
        if l_GearPower_0 == v_u_13.Name then
            local v58 = f_sort_type_val_get(p56)
            local v59 = f_sort_type_val_get(p57)
            if v58 ~= v59 then
                return v58 < v59;
            end;
            local v60 = v_u_39:get(p56)
            if v60 == nil then
                local v61 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p56) then
                    v60 = v_u_8:playerblob_get_pet_ownedid_gearpower(v61, v_u_8:ownedpet_get_ownedid(p56))
                else
                    v60 = v_u_1:playerblob_get_ownedid_gearpower(v61, p56.OwnedID)
                end;
                v_u_39:add(p56, v60)
            end;
            local v62 = v_u_39:get(p57)
            if v62 == nil then
                local v63 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p57) then
                    v62 = v_u_8:playerblob_get_pet_ownedid_gearpower(v63, v_u_8:ownedpet_get_ownedid(p57))
                else
                    v62 = v_u_1:playerblob_get_ownedid_gearpower(v63, p57.OwnedID)
                end;
                v_u_39:add(p57, v62)
            end;
            return v62 < v60;
        end;
        if l_GearPower_0 == v_u_13.GearPower then
            local v64 = f_sort_type_val_get(p56)
            local v65 = f_sort_type_val_get(p57)
            if v64 ~= v65 then
                return v65 < v64;
            end;
            local v66 = v_u_39:get(p56)
            if v66 == nil then
                local v67 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p56) then
                    v66 = v_u_8:playerblob_get_pet_ownedid_gearpower(v67, v_u_8:ownedpet_get_ownedid(p56))
                else
                    v66 = v_u_1:playerblob_get_ownedid_gearpower(v67, p56.OwnedID)
                end;
                v_u_39:add(p56, v66)
            end;
            local v68 = v_u_39:get(p57)
            if v68 == nil then
                local v69 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p57) then
                    v68 = v_u_8:playerblob_get_pet_ownedid_gearpower(v69, v_u_8:ownedpet_get_ownedid(p57))
                else
                    v68 = v_u_1:playerblob_get_ownedid_gearpower(v69, p57.OwnedID)
                end;
                v_u_39:add(p57, v68)
            end;
            return v68 < v66;
        end;
        if l_GearPower_0 == v_u_13.Slot then
            local v70 = f_sort_type_val_get(p56)
            local v71 = f_sort_type_val_get(p57)
            if v70 ~= v71 then
                return v70 < v71;
            end;
            local v72 = v_u_39:get(p56)
            if v72 == nil then
                local v73 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p56) then
                    v72 = v_u_8:playerblob_get_pet_ownedid_gearpower(v73, v_u_8:ownedpet_get_ownedid(p56))
                else
                    v72 = v_u_1:playerblob_get_ownedid_gearpower(v73, p56.OwnedID)
                end;
                v_u_39:add(p56, v72)
            end;
            local v74 = v_u_39:get(p57)
            if v74 == nil then
                local v75 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p57) then
                    v74 = v_u_8:playerblob_get_pet_ownedid_gearpower(v75, v_u_8:ownedpet_get_ownedid(p57))
                else
                    v74 = v_u_1:playerblob_get_ownedid_gearpower(v75, p57.OwnedID)
                end;
                v_u_39:add(p57, v74)
            end;
            return v74 < v72;
        end;
        if l_GearPower_0 == v_u_13.Upgrades then
            local v76 = f_sort_type_val_get(p56)
            local v77 = f_sort_type_val_get(p57)
            if v76 ~= v77 then
                return v77 < v76;
            end;
            local v78 = v_u_39:get(p56)
            if v78 == nil then
                local v79 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p56) then
                    v78 = v_u_8:playerblob_get_pet_ownedid_gearpower(v79, v_u_8:ownedpet_get_ownedid(p56))
                else
                    v78 = v_u_1:playerblob_get_ownedid_gearpower(v79, p56.OwnedID)
                end;
                v_u_39:add(p56, v78)
            end;
            local v80 = v_u_39:get(p57)
            if v80 == nil then
                local v81 = p_u_38
                if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p57) then
                    v80 = v_u_8:playerblob_get_pet_ownedid_gearpower(v81, v_u_8:ownedpet_get_ownedid(p57))
                else
                    v80 = v_u_1:playerblob_get_ownedid_gearpower(v81, p57.OwnedID)
                end;
                v_u_39:add(p57, v80)
            end;
            return v80 < v78;
        end;
        if l_GearPower_0 ~= v_u_13.Color then
            return p56 < p57;
        end;
        local v82 = f_sort_type_val_get(p56)
        local v83 = f_sort_type_val_get(p57)
        if v82 ~= v83 then
            return v82 < v83;
        end;
        local v84 = v_u_39:get(p56)
        if v84 == nil then
            local v85 = p_u_38
            if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p56) then
                v84 = v_u_8:playerblob_get_pet_ownedid_gearpower(v85, v_u_8:ownedpet_get_ownedid(p56))
            else
                v84 = v_u_1:playerblob_get_ownedid_gearpower(v85, p56.OwnedID)
            end;
            v_u_39:add(p56, v84)
        end;
        local v86 = v_u_39:get(p57)
        if v86 == nil then
            local v87 = p_u_38
            if v_u_4.DebugMinisActive == true and v_u_8:is_ownedpet(p57) then
                v86 = v_u_8:playerblob_get_pet_ownedid_gearpower(v87, v_u_8:ownedpet_get_ownedid(p57))
            else
                v86 = v_u_1:playerblob_get_ownedid_gearpower(v87, p57.OwnedID)
            end;
            v_u_39:add(p57, v86)
        end;
        return v86 < v84;
    end;
end;
return v12;
