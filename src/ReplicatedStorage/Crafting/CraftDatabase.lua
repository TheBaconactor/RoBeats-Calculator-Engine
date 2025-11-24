-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Crafting.MaterialsSet1)
local v_u_4 = require(game.ReplicatedStorage.Crafting.SongCraftingRecipes)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_9 = require(game.ReplicatedStorage.Crafting.GearCraftingRecipes)
local v_u_10 = require(game.ReplicatedStorage.Crafting.MaterialCraftingRecipes)
local v_u_11 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_13 = {
    ["invalid_material_id"] = function(_) --[[ Name: invalid_material_id ]] --[[ Line: 208 ]]
        return -1;
    end
}
v_u_13.new = function(_) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_9, (copy 4): v_u_10, (copy 5): v_u_1, (copy 6): v_u_2, (copy 7): v_u_5, (copy 8): v_u_11, (copy 9): v_u_12, (copy 10): v_u_6, (copy 11): v_u_7, (copy 12): v_u_8, (copy 13): v_u_13 ]]
    local v_u_38 = {
        ["get_material_name"] = function(p14, p15) --[[ Name: get_material_name ]] --[[ Line: 72 ]]
            return p14:get_material(p15):get_name();
        end,
        ["get_material_icon"] = function(p16, p17) --[[ Name: get_material_icon ]] --[[ Line: 73 ]]
            return p16:get_material(p17):get_icon();
        end,
        ["get_material_description"] = function(p18, p19) --[[ Name: get_material_description ]] --[[ Line: 74 ]]
            return p18:get_material(p19):get_description();
        end,
        ["get_material_tier"] = function(p20, p21) --[[ Name: get_material_tier ]] --[[ Line: 75 ]]
            return p20:get_material(p21):get_tier();
        end,
        ["get_material_type"] = function(p22, p23) --[[ Name: get_material_type ]] --[[ Line: 76 ]]
            return p22:get_material(p23):get_type();
        end,
        ["is_material_tradeable"] = function(p24, p25) --[[ Name: is_material_tradeable ]] --[[ Line: 77 ]]
            return p24:get_material(p25):is_tradeable();
        end,
        ["get_song_recipe_songkey"] = function(p26, p27) --[[ Name: get_song_recipe_songkey ]] --[[ Line: 104 ]]
            return p26:get_song_recipe(p27):get_song();
        end,
        ["get_gear_recipe_gear_id"] = function(p28, p29) --[[ Name: get_gear_recipe_gear_id ]] --[[ Line: 132 ]]
            return p28:get_gear_recipe(p29):get_gear_id();
        end,
        ["get_material_recipe_material_id"] = function(p30, p31) --[[ Name: get_material_recipe_material_id ]] --[[ Line: 164 ]]
            return p30:get_material_recipe(p31):get_material_id();
        end,
        ["get_material_recipe_result_count"] = function(p32, p33) --[[ Name: get_material_recipe_result_count ]] --[[ Line: 165 ]]
            return p32:get_material_recipe(p33):get_count();
        end,
        ["get_material_recipe_icon"] = function(p34, p35) --[[ Name: get_material_recipe_icon ]] --[[ Line: 166 ]]
            return p34:get_material_icon(p34:get_material_recipe_material_id(p35));
        end,
        ["get_material_recipe_name"] = function(p36, p37) --[[ Name: get_material_recipe_name ]] --[[ Line: 167 ]]
            return string.format("%s x%d", p36:get_material_name(p36:get_material_recipe_material_id(p37)), (p36:get_material_recipe_result_count(p37)));
        end
    }
    local function f_cons() --[[ Name: cons ]] --[[ Line: 22 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_38, (ref 3): v_u_4, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_1, (ref 7): v_u_2, (ref 8): v_u_5 ]]
        v_u_3:add_to_craftdatabase(v_u_38)
        v_u_38:validate_crafting_materials()
        v_u_4:add_to_craftdatabase(v_u_38)
        v_u_9:add_to_craftdatabase(v_u_38)
        v_u_10:add_to_craftdatabase(v_u_38)
        local v39 = v_u_1:new()
        for v40, _ in v_u_38:song_recipe_key_itr() do
            v39:add(v_u_38:get_song_recipe_songkey(v40), true)
        end;
        local v41 = v_u_2:singleton():all_keys()
        for v42 = 1, v41:count() do
            local v43 = v41:get(v42)
            if v_u_2:singleton():key_get_audiomod(v43) == v_u_2.MOD_NORMAL and (v39:get(v43) ~= true and v_u_2:singleton():get_songkey_should_grant(v43)) then
                v_u_5:warnf("SongKey(%d)(%s) has no crafting recipe", v43, v_u_2:singleton():get_title_for_key(v43))
            end;
        end;
    end;
    local v_u_44 = v_u_1:new()
    local v_u_45 = 1
    v_u_38.add_to_material_dict = function(_, p46, p47) --[[ Name: add_to_material_dict ]] --[[ Line: 51 ]]
        --[[ Upvalues: (copy 1): v_u_44, (ref 2): v_u_5, (ref 3): v_u_45 ]]
        if v_u_44:contains(p46) then
            return v_u_5:errf("CraftDatabase:add_to_material_dict already contains(%d)", p46);
        end;
        if p46 ~= v_u_45 then
            v_u_5:errf("CraftDatabase:add_to_material_dict unexpected id(%d)", p46)
        end;
        v_u_45 = v_u_45 + 1
        v_u_44:add(p46, p47)
    end;
    v_u_38.validate_crafting_materials = function(p48) --[[ Name: validate_crafting_materials ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_11, (ref 3): v_u_12 ]]
        local v49 = v_u_1:new()
        for _, v50 in v_u_11:singleton():get_pet_id_list():key_itr() do
            local v51 = v_u_11:singleton():get_data_for_petid(v50)
            v_u_12:is_true(p48:contains_material(v51:get_material_id()))
            v_u_12:is_false(v49:contains(v51:get_material_id()))
            v49:add_set(v51:get_material_id())
        end;
    end;
    v_u_38.material_key_itr = function(_) --[[ Name: material_key_itr ]] --[[ Line: 69 ]]
        --[[ Upvalues: (copy 1): v_u_44 ]]
        return v_u_44:key_itr();
    end;
    v_u_38.get_material = function(_, p52) --[[ Name: get_material ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_44 ]]
        return v_u_44:get(p52);
    end;
    v_u_38.contains_material = function(_, p53) --[[ Name: contains_material ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): v_u_44 ]]
        return v_u_44:contains(p53);
    end;
    v_u_38.tier_get_color = function(_, p54) --[[ Name: tier_get_color ]] --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7 ]]
        if p54 == v_u_6.Tier.T1 then
            return v_u_7:color3(189, 196, 195);
        elseif p54 == v_u_6.Tier.T2 then
            return v_u_7:color3(234, 255, 98);
        elseif p54 == v_u_6.Tier.T3 then
            return v_u_7:color3(24, 234, 252);
        else
            return v_u_7:color3(238, 130, 238);
        end;
    end;
    local v_u_55 = v_u_1:new()
    local v_u_56 = v_u_1:new()
    v_u_38.add_to_song_recipe_dict = function(_, p57, p58) --[[ Name: add_to_song_recipe_dict ]] --[[ Line: 96 ]]
        --[[ Upvalues: (copy 1): v_u_55, (copy 2): v_u_56 ]]
        if v_u_55:contains(p57) then
            error(string.format("CraftDatabase:add_to_song_recipe_dict contains(%d)", p57))
        end;
        v_u_55:add(p57, p58)
        v_u_56:add(p58:get_song(), p57)
    end;
    v_u_38.get_song_recipe = function(_, p59) --[[ Name: get_song_recipe ]] --[[ Line: 102 ]]
        --[[ Upvalues: (copy 1): v_u_55 ]]
        return v_u_55:get(p59);
    end;
    v_u_38.song_recipe_key_itr = function(_) --[[ Name: song_recipe_key_itr ]] --[[ Line: 103 ]]
        --[[ Upvalues: (copy 1): v_u_55 ]]
        return v_u_55:key_itr();
    end;
    v_u_38.get_song_recipe_icon = function(p60, p61) --[[ Name: get_song_recipe_icon ]] --[[ Line: 107 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        return v_u_2:singleton():get_coverimage_assetid_for_key(p60:get_song_recipe(p61):get_song());
    end;
    v_u_38.get_song_recipe_requirements_dict = function(p62, p63) --[[ Name: get_song_recipe_requirements_dict ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v64 = v_u_1:new()
        p62:get_song_recipe(p63):get_requirements(v64)
        return v64;
    end;
    v_u_38.get_songkey_recipe_id = function(_, p65) --[[ Name: get_songkey_recipe_id ]] --[[ Line: 116 ]]
        --[[ Upvalues: (copy 1): v_u_56 ]]
        return v_u_56:get(p65);
    end;
    local v_u_66 = v_u_1:new()
    local v_u_67 = v_u_1:new()
    v_u_38.add_to_gear_recipe_dict = function(_, p68, p69) --[[ Name: add_to_gear_recipe_dict ]] --[[ Line: 124 ]]
        --[[ Upvalues: (copy 1): v_u_66, (copy 2): v_u_67 ]]
        if v_u_66:contains(p68) then
            error(string.format("CraftDatabase:_id_to_gear_recipe contains(%d)", p68))
        end;
        v_u_66:add(p68, p69)
        v_u_67:add(p69:get_gear_id(), p68)
    end;
    v_u_38.get_gear_recipe = function(_, p70) --[[ Name: get_gear_recipe ]] --[[ Line: 130 ]]
        --[[ Upvalues: (copy 1): v_u_66 ]]
        return v_u_66:get(p70);
    end;
    v_u_38.gear_recipe_key_itr = function(_) --[[ Name: gear_recipe_key_itr ]] --[[ Line: 131 ]]
        --[[ Upvalues: (copy 1): v_u_66 ]]
        return v_u_66:key_itr();
    end;
    v_u_38.get_gear_recipe_icon = function(p71, p72) --[[ Name: get_gear_recipe_icon ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        return v_u_8:singleton():get_equipment_for_id((p71:get_gear_recipe_gear_id(p72))):get_icon();
    end;
    v_u_38.get_gear_recipe_name = function(p73, p74) --[[ Name: get_gear_recipe_name ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        return v_u_8:singleton():get_equipment_for_id(p73:get_gear_recipe_gear_id(p74)):get_name();
    end;
    v_u_38.get_gear_recipe_requirements_dict = function(p75, p76) --[[ Name: get_gear_recipe_requirements_dict ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v77 = v_u_1:new()
        p75:get_gear_recipe(p76):get_requirements(v77)
        return v77;
    end;
    v_u_38.contains_recipe_id_for_gear_id = function(_, p78) --[[ Name: contains_recipe_id_for_gear_id ]] --[[ Line: 149 ]]
        --[[ Upvalues: (copy 1): v_u_67 ]]
        return v_u_67:contains(p78), v_u_67:get(p78);
    end;
    local v_u_79 = v_u_1:new()
    v_u_38.add_to_material_recipe_dict = function(_, p80, p81) --[[ Name: add_to_material_recipe_dict ]] --[[ Line: 157 ]]
        --[[ Upvalues: (copy 1): v_u_79 ]]
        if v_u_79:contains(p80) then
            error("CraftDatabase:add_to_material_recipe_dict contains", p80)
        end;
        v_u_79:add(p80, p81)
    end;
    v_u_38.get_material_recipe = function(_, p82) --[[ Name: get_material_recipe ]] --[[ Line: 162 ]]
        --[[ Upvalues: (copy 1): v_u_79 ]]
        return v_u_79:get(p82);
    end;
    v_u_38.material_recipe_key_itr = function(_) --[[ Name: material_recipe_key_itr ]] --[[ Line: 163 ]]
        --[[ Upvalues: (copy 1): v_u_79 ]]
        return v_u_79:key_itr();
    end;
    v_u_38.get_material_recipe_requirements_dict = function(p83, p84, p85) --[[ Name: get_material_recipe_requirements_dict ]] --[[ Line: 172 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v86 = p85 == nil and 1 or p85
        local v87 = v_u_1:new()
        p83:get_material_recipe(p84):get_requirements(v87)
        if v86 > 1 then
            for v88, v89 in v87:key_itr() do
                v87:add(v88, v89 * v86)
            end;
        end;
        return v87;
    end;
    v_u_38.get_craftdatabase_info = function(_) --[[ Name: get_craftdatabase_info ]] --[[ Line: 186 ]]
        --[[ Upvalues: (copy 1): v_u_44, (ref 2): v_u_13 ]]
        local v90 = {}
        for v91, _ in v_u_44:key_itr() do
            v90[#v90 + 1] = {
                ["material_id"] = v91,
                ["name"] = v_u_13:singleton():get_material_name(v91),
                ["tier"] = v_u_13:singleton():get_material_tier(v91),
                ["material_type"] = v_u_13:singleton():get_material_type(v91)
            }
        end;
        return v90;
    end;
    f_cons()
    return v_u_38;
end;
local v_u_92 = v_u_13:new()
v_u_13.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 204 ]]
    --[[ Upvalues: (copy 1): v_u_92 ]]
    return v_u_92;
end;
return v_u_13;
