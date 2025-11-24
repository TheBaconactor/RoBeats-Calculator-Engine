-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_44 = {
    ["get_owned_crafting_materials"] = function(_, p11) --[[ Name: get_owned_crafting_materials ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5, (copy 3): v_u_3 ]]
        local v12 = v_u_2:new()
        for _, v13 in pairs(p11.CraftingMaterials) do
            local l_ID_0 = v13.ID
            local l_Count_0 = v13.Count
            if v_u_5:singleton():get_material(l_ID_0) then
                if l_Count_0 > 0 then
                    v12:add(l_ID_0, l_Count_0)
                end;
            else
                v_u_3:warnf("PlayerBlobCrafting:get_owned_crafting_materials invalid material_id(%d)", l_ID_0)
            end;
        end;
        return v12;
    end,
    ["add_crafting_materials_of_id"] = function(_, p14, p15, p16) --[[ Name: add_crafting_materials_of_id ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_5, (copy 3): v_u_3 ]]
        v_u_9:is_true(v_u_5:singleton():contains_material(p15))
        v_u_9:is_int(p16)
        for _, v17 in pairs(p14.CraftingMaterials) do
            local l_ID_1 = v17.ID
            local l_Count_1 = v17.Count
            if l_ID_1 == p15 then
                local v18 = l_Count_1 + p16
                if v18 < 0 then
                    v_u_3:errf("PlayerBlobCrafting:add_crafting_materials_of_id(%s,%s) neu_count(%s) is less than 0", tostring(p15), tostring(p16), (tostring(v18)))
                    v18 = 0
                end;
                v17.Count = v18
                return v18;
            end;
        end;
        p14.CraftingMaterials[#p14.CraftingMaterials + 1] = {
            ["ID"] = p15,
            ["Count"] = p16
        }
        return p16;
    end,
    ["get_count_of_material"] = function(_, p19, p20) --[[ Name: get_count_of_material ]] --[[ Line: 58 ]]
        for _, v21 in pairs(p19.CraftingMaterials) do
            local l_ID_2 = v21.ID
            local l_Count_2 = v21.Count
            if l_ID_2 == p20 then
                return l_Count_2;
            end;
        end;
        return 0;
    end,
    ["can_craft_recipe"] = function(_, p22, p23, p24) --[[ Name: can_craft_recipe ]] --[[ Line: 99 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_6, (copy 4): v_u_10 ]]
        local v25 = v_u_5:singleton():get_song_recipe_songkey(p23)
        local v26, v27 = v_u_7:singleton():key_has_combineinfo(v25)
        if v26 then
            v27 = v27.OutputKey
        end;
        local v28 = v_u_6:get_song_key_owned_count(p22, v25)
        local v29 = not v26 and 0 or v_u_6:get_song_key_owned_count(p22, v27)
        if p24 == nil then
            p24 = v_u_10:get_collection_info_from_playerblob(p22)
        end;
        local v30 = v28 > 0 or (v29 > 0 or v_u_7:singleton():get_easymode_crafting_normal_key_set():contains(v25))
        if v30 then
            v26 = v30
        elseif v_u_10:get_playerblob_songkey_in_collection(p22, v25, p24) == true then
            v26 = true
        elseif v26 then
            v26 = v_u_10:get_playerblob_songkey_in_collection(p22, v27, p24) == true
        end;
        return v26;
    end,
    ["get_playerblob_craftable_song_recipe_ids_list"] = function(_, p31, p32) --[[ Name: get_playerblob_craftable_song_recipe_ids_list ]] --[[ Line: 124 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_6, (copy 4): v_u_10, (copy 5): v_u_5, (copy 6): v_u_7 ]]
        local v33 = v_u_1:new()
        v_u_4:profilebegin("PlayerBlob:song_inventory_key_to_owned_count_dict")
        local v34 = v_u_6:song_inventory_key_to_owned_count_dict(p31)
        v_u_4:profileend()
        v_u_4:profilebegin("CollectionInfo:get_collection_info_from_playerblob")
        if p32 == nil then
            p32 = v_u_10:get_collection_info_from_playerblob(p31)
        end;
        v_u_4:profileend()
        local v35 = v_u_5:singleton()
        local v36 = v_u_7:singleton()
        local v37 = v36:get_easymode_crafting_normal_key_set()
        v_u_4:profilebegin("craft_database_singleton:song_recipe_key_itr()")
        for v38, _ in v35:song_recipe_key_itr() do
            local v39 = v35:get_song_recipe_songkey(v38)
            local v40, v41 = v36:key_has_combineinfo(v39)
            local l_OutputKey_0 = v41.OutputKey
            local v42 = v37:contains(v39) and true or false
            if v42 ~= true then
                v42 = v40 and v34:contains(l_OutputKey_0) and true or (v34:contains(v39) and true or v42)
            end;
            local v43 = v42 ~= true and v_u_10:get_playerblob_songkey_in_collection(p31, v39, p32) == true and true or v42
            if v43 ~= true and (v40 and v_u_10:get_playerblob_songkey_in_collection(p31, l_OutputKey_0, p32) == true) and true or v43 then
                v33:push_back(v38)
            end;
        end;
        v_u_4:profileend()
        return v33;
    end,
    ["add_debug_materials_to_playerblob"] = function(_, _) end
}
v_u_44.can_craft_requirements_dict = function(_, p45, p46) --[[ Name: can_craft_requirements_dict ]] --[[ Line: 70 ]]
    --[[ Upvalues: (copy 1): v_u_44 ]]
    for v47, v48 in p46:key_itr() do
        if v_u_44:get_count_of_material(p45, v47) < v48 then
            return false;
        end;
    end;
    return true;
end;
v_u_44.can_craft_count_of_requirements_dict = function(_, p49, p50) --[[ Name: can_craft_count_of_requirements_dict ]] --[[ Line: 79 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_44 ]]
    local v51 = v_u_1:new()
    for v52, v53 in p50:key_itr() do
        v51:push_back((math.floor(v_u_44:get_count_of_material(p49, v52) / v53)))
    end;
    if v51:count() == 0 then
        return 0;
    end;
    local v54 = v51:get(1)
    for v55 = 1, v51:count() do
        v54 = math.min(v54, v51:get(v55))
    end;
    return v54;
end;
v_u_44.can_craft_songkey = function(_, p56, p57, p58) --[[ Name: can_craft_songkey ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_44 ]]
    local v59 = v_u_5:singleton():get_songkey_recipe_id(p57)
    if v59 == nil then
        return false;
    else
        return v_u_44:can_craft_recipe(p56, v59, p58);
    end;
end;
local function f_validate_playerblob_fevericon_dayid(p60, p61, p62) --[[ Name: validate_playerblob_fevericon_dayid ]] --[[ Line: 184 ]]
    --[[ Upvalues: (copy 1): v_u_44, (copy 2): v_u_5, (copy 3): v_u_10, (copy 4): v_u_8 ]]
    local l_FeverIcon_0 = p60.FeverIcon
    if l_FeverIcon_0 == 0 or l_FeverIcon_0 == 1 then
        return;
    end;
    local v63 = v_u_44:get_owned_crafting_materials(p60)
    local v64 = false
    for v65, v66 in v63:key_itr() do
        local v67 = v_u_5:singleton():get_material(v65)
        if v67 and (v66 > 0 and (v67:get_fever_icon_id() == l_FeverIcon_0 and (v67:is_fever_icon() and v63:contains(v65)))) then
            v64 = true
            break;
        end;
    end;
    for v68, _ in v_u_10:playerblob_get_collection_type_database_id_set(p60, v_u_10.Type.Icons, p62):key_itr() do
        if v68 == l_FeverIcon_0 then
            v64 = true
            break;
        end;
    end;
    if v_u_8:playerblob_has_vip_for_current_day(p60, p61) then
        for v69, _ in v_u_8:get_vip_fevericon_ids_set():key_itr() do
            if l_FeverIcon_0 == v69 then
                v64 = true
                break;
            end;
        end;
    end;
    if v64 ~= true then
        p60.FeverIcon = 0
    end;
end;
v_u_44.validate_playerblob_fevericon = function(_, p70, p71) --[[ Name: validate_playerblob_fevericon ]] --[[ Line: 222 ]]
    --[[ Upvalues: (copy 1): f_validate_playerblob_fevericon_dayid ]]
    f_validate_playerblob_fevericon_dayid(p70, p71._api:get_day_id(), p71._collection_manager:get_collection_info_for_player_id_playerblob(p70.UserId, p70))
end;
v_u_44.playerblob_song_key_to_craftable_song = function(_, p72, p73) --[[ Name: playerblob_song_key_to_craftable_song ]] --[[ Line: 230 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_5, (copy 3): v_u_44 ]]
    local v74 = v_u_7:invalid_songkey()
    if v_u_5:singleton():get_songkey_recipe_id(p73) == nil then
        if v_u_7:singleton():get_easy_mode_to_songkey_dict():contains(p73) then
            p73 = v_u_7:singleton():get_easy_mode_to_songkey_dict():get(p73)
        elseif v_u_7:singleton():key_is_fusionresult_of(p73) == nil then
            p73 = v74
        else
            p73 = v_u_7:singleton():key_is_fusionresult_of(p73)
            if v_u_5:singleton():get_songkey_recipe_id(p73) == nil then
                p73 = v74
            end;
        end;
    end;
    if p73 == v_u_7:invalid_songkey() or not v_u_44:can_craft_songkey(p72, p73) then
        return v_u_7:invalid_songkey();
    else
        return p73;
    end;
end;
return v_u_44;
